"""
Finance & Receipt Service Layer
Handles payment processing, installment tracking, fee structures, refunds, and receipt generation.
"""
from __future__ import annotations

import uuid
import logging
from decimal import Decimal
from typing import Any
from django.db import transaction
from django.db.models import Q, QuerySet, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import Role, User
from finance.models import FeeStructure, FeeDiscount, Installment, Payment, Receipt, Refund
from aws_services.ses_sns_service import notification_service

ZERO = Decimal('0.00')

#: Fee-status vocabulary exposed by `student_fee_summary`.
FEE_STATUS_PAID = 'PAID'
FEE_STATUS_PENDING = 'PENDING'
FEE_STATUS_PARTIALLY_PAID = 'PARTIALLY_PAID'
FEE_STATUS_OVERDUE = 'OVERDUE'

logger = logging.getLogger('institute_crm.finance')


class FinanceService:
    @staticmethod
    def filter_installments(
        actor: User,
        *,
        student_id: str | None = None,
        status: str | None = None,
    ) -> QuerySet[Installment]:
        qs = Installment.objects.filter(is_deleted=False).select_related(
            'student', 'student__branch', 'fee_structure', 'fee_structure__course'
        )

        if student_id:
            qs = qs.filter(student_id=student_id)
        if status:
            qs = qs.filter(status=status)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code == Role.STUDENT:
                qs = qs.filter(student=actor)
            elif role_code == Role.PARENT:
                qs = qs.filter(student__student_profile__parent_links__parent__user=actor)
            elif role_code in [Role.BRANCH_ADMIN, Role.ACCOUNTANT] and actor.branch:
                qs = qs.filter(student__branch=actor.branch)

        return qs.order_by('due_date')

    @staticmethod
    def filter_payments(
        actor: User,
        *,
        student_id: str | None = None,
    ) -> QuerySet[Payment]:
        qs = Payment.objects.filter(is_deleted=False).select_related(
            'student', 'installment', 'receipt', 'recorded_by'
        )

        if student_id:
            qs = qs.filter(student_id=student_id)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code == Role.STUDENT:
                qs = qs.filter(student=actor)
            elif role_code == Role.PARENT:
                qs = qs.filter(student__student_profile__parent_links__parent__user=actor)
            elif role_code in [Role.BRANCH_ADMIN, Role.ACCOUNTANT] and actor.branch:
                qs = qs.filter(student__branch=actor.branch)

        return qs.order_by('-payment_date')

    @staticmethod
    def student_fee_summary(student_user: User) -> dict[str, Any]:
        """Computed fee summary for one student. Read-only; nothing is persisted.

        Student-specific fee *terms* come from ``StudentProfile`` (agreed fee and
        applicable discount/concession/scholarship, in INR):

            net_fee = max(agreed_fee - discount_amount - concession_amount
                          - scholarship_amount, 0)

        Transaction truth comes from the existing finance records - installment
        schedule, payments and refunds - so totals always match what the finance
        app itself would report and cannot drift:

            total_paid = sum(Payment.amount) - sum(approved Refund.amount)

        ``outstanding_balance`` is measured against the actual billed amount:
        the scheduled installment total when a schedule exists in finance,
        otherwise ``net_fee``; it is ``max(billed - total_paid, 0)``. Because
        this summary is computed live on every read from those rows, it is always
        consistent with the underlying finance records; no cached total is
        stored on the student profile, so nothing can go stale. ``next_due_date``
        is the earliest ``due_date`` among not-yet-paid installments (``None``
        when there is no open installment). ``fee_status`` is one of
        ``PAID`` / ``PENDING`` / ``PARTIALLY_PAID`` / ``OVERDUE``.
        """
        profile = getattr(student_user, 'student_profile', None)

        def term(name: str) -> Decimal:
            value = getattr(profile, name, None) if profile is not None else None
            try:
                return Decimal(str(value)) if value is not None else ZERO
            except (ArithmeticError, ValueError):
                return ZERO

        agreed_fee = term('agreed_fee')
        discount_amount = term('discount_amount')
        concession_amount = term('concession_amount')
        scholarship_amount = term('scholarship_amount')
        net_fee = max(
            agreed_fee - discount_amount - concession_amount - scholarship_amount, ZERO
        )

        installments = list(
            Installment.objects.filter(student=student_user, is_deleted=False)
        )
        payments_total = (
            Payment.objects.filter(student=student_user, is_deleted=False).aggregate(
                total=Sum('amount')
            )['total']
            or ZERO
        )
        refunds_total = (
            Refund.objects.filter(
                student=student_user, is_deleted=False, status='APPROVED'
            ).aggregate(total=Sum('amount'))['total']
            or ZERO
        )
        total_paid = Decimal(str(payments_total)) - Decimal(str(refunds_total))

        scheduled_total = sum((i.amount or ZERO for i in installments), ZERO)
        billed_total = scheduled_total if scheduled_total > ZERO else net_fee
        outstanding_balance = max(billed_total - total_paid, ZERO)

        today = timezone.now().date()
        open_installments = [i for i in installments if i.status != 'PAID']
        next_due_date = min((i.due_date for i in open_installments), default=None)
        overdue = any(
            i.due_date < today for i in open_installments
        )

        if outstanding_balance <= ZERO:
            fee_status = FEE_STATUS_PAID
        elif overdue:
            fee_status = FEE_STATUS_OVERDUE
        elif total_paid > ZERO:
            fee_status = FEE_STATUS_PARTIALLY_PAID
        else:
            fee_status = FEE_STATUS_PENDING

        def money(value: Decimal) -> str:
            return str(value.quantize(Decimal('0.01')))

        return {
            'currency': 'INR',
            'agreed_fee': money(agreed_fee),
            'discount_amount': money(discount_amount),
            'concession_amount': money(concession_amount),
            'scholarship_amount': money(scholarship_amount),
            'net_fee': money(net_fee),
            'total_paid': money(total_paid),
            'outstanding_balance': money(outstanding_balance),
            'next_due_date': next_due_date.isoformat() if next_due_date else None,
            'fee_status': fee_status,
        }

    @staticmethod
    @transaction.atomic
    def record_payment(
        student_user: User,
        amount: float,
        payment_mode: str,
        reference_number: str | None = None,
        installment_id: str | None = None,
        recorded_by: User | None = None
    ) -> tuple[Payment, Receipt]:
        installment = None
        if installment_id:
            installment = Installment.objects.select_for_update().get(id=installment_id)

        payment = Payment.objects.create(
            student=student_user,
            installment=installment,
            amount=amount,
            payment_mode=payment_mode,
            reference_number=reference_number or f"REF-{uuid.uuid4().hex[:8].upper()}",
            recorded_by=recorded_by
        )

        if installment:
            installment.status = 'PAID'
            installment.save()

        # Generate Receipt
        receipt_num = f"REC-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        receipt = Receipt.objects.create(
            receipt_number=receipt_num,
            payment=payment,
            pdf_url=f"https://institute-crm-storage-bucket.s3.amazonaws.com/receipts/{receipt_num}.pdf"
        )

        # Notify via Email/SMS
        msg = f"Payment of INR {amount} received via {payment_mode}. Receipt No: {receipt_num}."
        notification_service.send_email(
            recipient_email=student_user.email,
            subject=f"Fee Payment Receipt #{receipt_num}",
            body_html=f"<h3>Payment Receipt</h3><p>{msg}</p>"
        )

        logger.info(f"Payment recorded: {payment.id} for student {student_user.id}")
        return payment, receipt

    @staticmethod
    @transaction.atomic
    def process_refund(
        actor: User,
        student_user: User,
        amount: float,
        reason: str,
    ) -> Refund:
        refund = Refund.objects.create(
            student=student_user,
            amount=amount,
            reason=reason,
            status='PENDING'
        )
        logger.info(f"Refund request created: {refund.id} by user {actor.id}")
        return refund
