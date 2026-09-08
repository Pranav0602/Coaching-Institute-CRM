from rest_framework import serializers
from finance.models import FeeStructure, FeeDiscount, Installment, Payment, Receipt, Refund

class FeeStructureSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = FeeStructure
        fields = ['id', 'course', 'course_title', 'total_amount', 'deposit_amount', 'num_installments']


class FeeDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeDiscount
        fields = ['id', 'title', 'discount_percentage', 'fixed_discount']


class InstallmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = Installment
        fields = ['id', 'student', 'student_name', 'fee_structure', 'installment_number', 'due_date', 'amount', 'status']


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['id', 'receipt_number', 'payment', 'issue_date', 'pdf_url']


class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    receipt = ReceiptSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'student', 'student_name', 'installment', 'amount', 'payment_mode', 'reference_number', 'payment_date', 'recorded_by', 'receipt']


class RefundSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = Refund
        fields = ['id', 'student', 'student_name', 'amount', 'reason', 'status', 'processed_by', 'created_at']


class RecordPaymentSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    installment_id = serializers.UUIDField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = serializers.CharField()
    reference_number = serializers.CharField(required=False, allow_blank=True)
