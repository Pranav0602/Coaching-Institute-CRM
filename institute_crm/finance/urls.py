from django.urls import path, include
from rest_framework.routers import DefaultRouter
from finance.views import (
    FeeStructureViewSet, FeeDiscountViewSet, InstallmentViewSet, 
    PaymentViewSet, ReceiptViewSet, RefundViewSet
)

router = DefaultRouter()
router.register(r'structures', FeeStructureViewSet, basename='feestructure')
router.register(r'discounts', FeeDiscountViewSet, basename='feediscount')
router.register(r'installments', InstallmentViewSet, basename='installment')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'receipts', ReceiptViewSet, basename='receipt')
router.register(r'refunds', RefundViewSet, basename='refund')

urlpatterns = [
    path('', include(router.urls)),
]
