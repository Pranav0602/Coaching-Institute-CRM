"""
Finance & Receipt Service Layer
Handles payment processing, installment tracking, fee structures, refunds, and receipt generation.
"""
from __future__ import annotations

import uuid
import logging
from typing import Any
from django.db import transaction
from django.db.models import Q, QuerySet, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import Role, User
from finance.models import FeeStructure, FeeDiscount, Installment, Payment, Receipt, Refund
from aws_services.ses_sns_service import notification_service

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
