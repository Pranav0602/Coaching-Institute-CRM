from django.db import models
from institute_crm.utils import BaseModel
from accounts.models import User
from academics.models import Course

class FeeStructure(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='fee_structures')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    num_installments = models.PositiveIntegerField(default=3)

    def __str__(self):
        return f"FeeStructure: {self.course.title} (Total: {self.total_amount})"


class FeeDiscount(BaseModel):
    title = models.CharField(max_length=150)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    fixed_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Discount: {self.title}"


class Installment(BaseModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='installments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE)
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)

    def __str__(self):
        return f"Installment #{self.installment_number} for {self.student.username} ({self.amount}) - {self.status}"


class Payment(BaseModel):
    MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Credit/Debit Card'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    installment = models.ForeignKey(Installment, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='UPI')
    reference_number = models.CharField(max_length=100, unique=True, db_index=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_payments')

    def __str__(self):
        return f"Payment: {self.reference_number} - {self.amount} ({self.student.username})"


class Receipt(BaseModel):
    receipt_number = models.CharField(max_length=100, unique=True, db_index=True)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='receipt')
    issue_date = models.DateField(auto_now_add=True)
    pdf_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"Receipt #{self.receipt_number}"


class Refund(BaseModel):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_refunds')

    def __str__(self):
        return f"Refund request: {self.student.username} - {self.amount} ({self.status})"
