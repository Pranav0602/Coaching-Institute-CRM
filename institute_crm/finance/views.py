"""
HTTP controller layer for the finance app.
Views validate requests and delegate execution to FinanceService.
"""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from finance.models import FeeStructure, FeeDiscount, Installment, Payment, Receipt, Refund
from finance.serializers import (
    FeeStructureSerializer, FeeDiscountSerializer, InstallmentSerializer, 
    PaymentSerializer, ReceiptSerializer, RefundSerializer, RecordPaymentSerializer
)
from finance.services.finance_service import FinanceService
from accounts.models import User


class FeeStructureViewSet(viewsets.ModelViewSet):
    queryset = FeeStructure.objects.filter(is_deleted=False).select_related('course')
    serializer_class = FeeStructureSerializer
    permission_classes = [IsAuthenticated]


class FeeDiscountViewSet(viewsets.ModelViewSet):
    queryset = FeeDiscount.objects.filter(is_deleted=False)
    serializer_class = FeeDiscountSerializer
    permission_classes = [IsAuthenticated]


class InstallmentViewSet(viewsets.ModelViewSet):
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinanceService.filter_installments(
            self.request.user,
            student_id=self.request.query_params.get('student_id'),
            status=self.request.query_params.get('status'),
        )


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinanceService.filter_payments(
            self.request.user,
            student_id=self.request.query_params.get('student_id'),
        )

    @action(detail=False, methods=['post'], url_path='record-payment')
    def record_payment(self, request):
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student_user = User.objects.get(id=serializer.validated_data['student_id'])
        payment, receipt = FinanceService.record_payment(
            student_user=student_user,
            amount=serializer.validated_data['amount'],
            payment_mode=serializer.validated_data['payment_mode'],
            reference_number=serializer.validated_data.get('reference_number'),
            installment_id=serializer.validated_data.get('installment_id'),
            recorded_by=request.user
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class ReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Receipt.objects.filter(is_deleted=False).select_related('payment')
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]


class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.filter(is_deleted=False).select_related('student')
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        FinanceService.process_refund(
            actor=self.request.user,
            student_user=serializer.validated_data['student'],
            amount=serializer.validated_data['amount'],
            reason=serializer.validated_data.get('reason', '')
        )
