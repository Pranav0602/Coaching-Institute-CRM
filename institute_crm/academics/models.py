from django.db import models
from institute_crm.utils import BaseModel
from accounts.models import User, Branch

class Course(BaseModel):
    FIELD_CHOICES = [
        ('Mechanical CAD/CAM/CAE', 'Mechanical CAD/CAM/CAE'),
        ('Civil CAD', 'Civil CAD'),
        ('Electrical CAD', 'Electrical CAD'),
        ('Design & BIM', 'Design & BIM'),
        ('Data Science & AI/ML', 'Data Science & AI/ML'),
        ('IT & Software Development', 'IT & Software Development'),
        ('Cloud Computing', 'Cloud Computing'),
    ]
    code = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    duration_months = models.PositiveIntegerField(default=6)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    field_of_engineering = models.CharField(max_length=50, choices=FIELD_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.code})"


class Subject(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    code = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('course', 'code')

    def __str__(self):
        return f"{self.title} [{self.course.code}]"


class Batch(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='batches')
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField()
    max_capacity = models.PositiveIntegerField(default=40)
    teachers = models.ManyToManyField(
        User,
        related_name='assigned_batches',
        blank=True,
        help_text="Teachers assigned to this cohort (primary, co-teachers, or substitutes)."
    )

    def __str__(self):
        return f"Batch: {self.name} ({self.code}) - {self.branch.name}"


class CourseEnrolment(BaseModel):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('DROPPED', 'Dropped'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrolments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrolments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrolments')
    enrolled_at = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"Enrolment: {self.student.username} -> {self.course.code}"


class Timetable(BaseModel):
    DAY_CHOICES = [
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'),
    ]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='timetables')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_timetables')
    day_of_week = models.CharField(max_length=15, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=50, default='Room 101')

    def __str__(self):
        return f"{self.batch.name} - {self.subject.title} ({self.day_of_week} {self.start_time}-{self.end_time})"


class Lecture(BaseModel):
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='lectures')
    date = models.DateField(db_index=True)
    topic = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default='SCHEDULED') # SCHEDULED, COMPLETED, CANCELLED
    conducted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_lectures',
        help_text="Teacher who actually conducted the lecture and marked attendance (allows substitutes)."
    )

    def __str__(self):
        return f"Lecture: {self.topic} on {self.date} [{self.timetable.batch.name}]"


class Attendance(BaseModel):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused'),
    ]

    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')
    remarks = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('lecture', 'student')

    def __str__(self):
        return f"Attendance: {self.student.username} - {self.status} ({self.lecture.date})"


class StudyMaterial(BaseModel):
    TYPE_CHOICES = [
        ('PDF', 'PDF Document'),
        ('VIDEO', 'Video Lecture'),
        ('NOTES', 'Class Notes'),
        ('LINK', 'External Link'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='materials')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True, related_name='materials')
    title = models.CharField(max_length=200)
    material_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='PDF')
    file_url = models.URLField(max_length=500, blank=True, null=True)
    external_link = models.URLField(max_length=500, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"StudyMaterial: {self.title} [{self.material_type}]"
