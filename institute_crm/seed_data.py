import os
import django
import sys
from datetime import date, timedelta, time
from django.utils import timezone
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'institute_crm.settings')

django.setup()

from accounts.models import Role, Branch, User
from users_profiles.models import StudentProfile, TeacherProfile, ParentProfile, StudentParent
from crm_leads.models import Lead, FollowUp, CounsellingNote, Visitor
from academics.models import Course, Subject, Batch, CourseEnrolment, Timetable, Lecture, Attendance, StudyMaterial
from assignments_exams.models import Assignment, Submission, Exam, Result
from finance.models import FeeStructure, FeeDiscount, Installment, Payment, Receipt
from communications.models import Announcement, Notification

def seed():
    print("[INFO] Seeding Coaching Institute CRM database...")

    # 1. Roles
    roles_data = [
        (Role.SUPER_ADMIN, 'Super Admin', 'Full system access across all branches'),
        (Role.BRANCH_ADMIN, 'Branch Admin', 'Manages branch operational activities'),
        (Role.ADMISSION_COUNSELOR, 'Admission Counselor', 'Handles leads, enquiries, counselling and admissions'),
        (Role.TEACHER, 'Teacher', 'Manages timetable, lectures, attendance, assignments and marks'),
        (Role.STUDENT, 'Student', 'Views timetable, submits assignments, checks fee receipts and marks'),
        (Role.PARENT, 'Parent', 'Monitors child attendance, test results, fee dues and remarks'),
        (Role.ACCOUNTANT, 'Accountant', 'Manages fee collection, discounts, installments and financial reports'),
        (Role.RECEPTIONIST, 'Receptionist', 'Registers walk-in visitors, enquiries and schedules sessions'),
    ]

    roles = {}
    for code, name, desc in roles_data:
        r, _ = Role.objects.get_or_create(code=code, defaults={'name': name, 'description': desc})
        roles[code] = r
    print(" [OK] 8 Roles seeded.")

    # 2. Branches
    branches_data = [
        ('BR-PUN-01', 'Main Campus - Downtown', 'Pune', '12 Connaught Place, Pune', '+91-20-12345678', 'pune@coachinginstitute.com'),
        ('BR-MUM-01', 'West End Branch - Bandra', 'Mumbai', '45 Linking Road, Bandra West, Mumbai', '+91-22-98765432', 'mumbai@coachinginstitute.com'),
        ('BR-BLR-01', 'North City Campus - Koramangala', 'Bengaluru', '88 80 Feet Road, Koramangala, Bengaluru', '+91-80-44556677', 'blore@coachinginstitute.com'),
    ]
    branches = []
    for code, name, city, addr, phone, email in branches_data:
        b, _ = Branch.objects.get_or_create(code=code, defaults={'name': name, 'city': city, 'address': addr, 'phone': phone, 'email': email})
        branches.append(b)
    print(" [OK] 3 Branches seeded.")

    b_pune = branches[0]

    # 3. Users for each role
    # Super Admin
    super_admin, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@coachinginstitute.com',
            'first_name': 'Super',
            'last_name': 'Administrator',
            'role': roles[Role.SUPER_ADMIN],
            'branch': b_pune,
            'is_superuser': True,
            'is_staff': True
        }
    )
    super_admin.set_password('Admin@123')
    super_admin.save()

    # Branch Admin
    branch_admin, _ = User.objects.get_or_create(
        username='branchadmin',
        defaults={'email': 'badmin@coachinginstitute.com', 'first_name': 'Rajesh', 'last_name': 'Sharma', 'role': roles[Role.BRANCH_ADMIN], 'branch': b_pune}
    )
    branch_admin.set_password('Admin@123')
    branch_admin.save()

    # Counselor
    counselor, _ = User.objects.get_or_create(
        username='counselor',
        defaults={'email': 'counselor@coachinginstitute.com', 'first_name': 'Priya', 'last_name': 'Verma', 'role': roles[Role.ADMISSION_COUNSELOR], 'branch': b_pune}
    )
    counselor.set_password('Admin@123')
    counselor.save()

    # Teacher
    teacher, _ = User.objects.get_or_create(
        username='teacher',
        defaults={'email': 'teacher@coachinginstitute.com', 'first_name': 'Dr. Alok', 'last_name': 'Gupta', 'role': roles[Role.TEACHER], 'branch': b_pune}
    )
    teacher.set_password('Admin@123')
    teacher.save()
    TeacherProfile.objects.get_or_create(user=teacher, defaults={'employee_id': 'EMP-101', 'qualification': 'Ph.D Computer Science (IIT Delhi)', 'specialization': 'Web Development & Cloud Computing'})

    # Accountant
    accountant, _ = User.objects.get_or_create(
        username='accountant',
        defaults={'email': 'accountant@coachinginstitute.com', 'first_name': 'Ramesh', 'last_name': 'Kumar', 'role': roles[Role.ACCOUNTANT], 'branch': b_pune}
    )
    accountant.set_password('Admin@123')
    accountant.save()

    # Receptionist
    receptionist, _ = User.objects.get_or_create(
        username='receptionist',
        defaults={'email': 'reception@coachinginstitute.com', 'first_name': 'Sneha', 'last_name': 'Patel', 'role': roles[Role.RECEPTIONIST], 'branch': b_pune}
    )
    receptionist.set_password('Admin@123')
    receptionist.save()

    # Student
    student_user, _ = User.objects.get_or_create(
        username='student',
        defaults={'email': 'student@coachinginstitute.com', 'first_name': 'Rohan', 'last_name': 'Mehta', 'role': roles[Role.STUDENT], 'branch': b_pune}
    )
    student_user.set_password('Admin@123')
    student_user.save()

    # Parent
    parent_user, _ = User.objects.get_or_create(
        username='parent',
        defaults={'email': 'parent@coachinginstitute.com', 'first_name': 'Suresh', 'last_name': 'Mehta', 'role': roles[Role.PARENT], 'branch': b_pune}
    )
    parent_user.set_password('Admin@123')
    parent_user.save()
    parent_prof, _ = ParentProfile.objects.get_or_create(user=parent_user, defaults={'occupation': 'Software Engineer', 'relationship_type': 'FATHER'})

    print(" [OK] All 8 User Roles initialized with login credentials (Password: Admin@123).")

    # 4. Course & Batch (Computer Science Courses)
    course, _ = Course.objects.get_or_create(
        code='CS-WEB-2026',
        defaults={'title': 'Fullstack Web Development Masterclass', 'description': 'Comprehensive React, Node.js, Next.js, REST API Engineering', 'duration_months': 6, 'total_fee': 120000.00}
    )
    Course.objects.get_or_create(
        code='CS-CLOUD-2026',
        defaults={'title': 'Cloud Computing & AWS Architecture', 'description': 'AWS Cloud, Docker, Kubernetes, and DevOps Architecture', 'duration_months': 6, 'total_fee': 110000.00}
    )
    Course.objects.get_or_create(
        code='CS-DBMS-2026',
        defaults={'title': 'Database Management Systems & Data Engineering', 'description': 'SQL, PostgreSQL, NoSQL MongoDB, Indexing & Query Tuning', 'duration_months': 4, 'total_fee': 95000.00}
    )
    Course.objects.get_or_create(
        code='CS-DS-2026',
        defaults={'title': 'Data Science & Machine Learning', 'description': 'Python Data Science, Pandas, Scikit-Learn, Deep Learning Models', 'duration_months': 6, 'total_fee': 130000.00}
    )

    subject_phy, _ = Subject.objects.get_or_create(course=course, code='CS-WEB-101', defaults={'title': 'Frontend & Backend Web Engineering', 'description': 'React, Node.js, Express, State Management'})
    subject_chem, _ = Subject.objects.get_or_create(course=course, code='CS-DBMS-101', defaults={'title': 'Database Engineering & SQL', 'description': 'PostgreSQL Schema Design, Indexing & Queries'})

    batch, _ = Batch.objects.get_or_create(
        code='BATCH-PUN-A1',
        defaults={'course': course, 'branch': b_pune, 'name': 'Morning Web Dev Batch A1', 'start_date': date(2026, 4, 1), 'end_date': date(2027, 3, 31), 'max_capacity': 40}
    )

    # Link Student Profile to Batch
    student_prof, _ = StudentProfile.objects.get_or_create(
        user=student_user,
        defaults={'enrollment_number': 'ENR-PUN-2026-001', 'batch': batch, 'dob': date(2008, 5, 14), 'gender': 'MALE', 'emergency_contact': '+91-9876543210'}
    )
    StudentParent.objects.get_or_create(student=student_prof, parent=parent_prof)
    CourseEnrolment.objects.get_or_create(student=student_user, course=course, defaults={'batch': batch, 'status': 'ACTIVE'})

    # 5. Leads Pipeline
    leads_sample = [
        ('Aarav Sharma', 'aarav@gmail.com', '+91-9811223344', Lead.STAGE_NEW, 'WEBSITE', 'Fullstack Web Development'),
        ('Ananya Singh', 'ananya@gmail.com', '+91-9822334455', Lead.STAGE_CONTACTED, 'WALK_IN', 'Cloud Computing & AWS'),
        ('Vikram Malhotra', 'vikram@gmail.com', '+91-9833445566', Lead.STAGE_DEMO_SCHEDULED, 'REFERRAL', 'Database Management Systems'),
        ('Ishita Kapoor', 'ishita@gmail.com', '+91-9844556677', Lead.STAGE_ADMISSION_PENDING, 'SOCIAL_MEDIA', 'Data Science & Machine Learning'),
    ]
    for name, email, phone, stage, source, target_c in leads_sample:
        ld, _ = Lead.objects.get_or_create(
            email=email,
            defaults={'name': name, 'phone': phone, 'branch': b_pune, 'target_course': target_c, 'source': source, 'stage': stage, 'lead_owner': counselor}
        )
        FollowUp.objects.get_or_create(lead=ld, counselor=counselor, defaults={'scheduled_date': timezone.now() + timedelta(days=2), 'remarks': 'Discuss fee structure and demo class feedback.'})

    # 6. Timetable & Lecture
    tt, _ = Timetable.objects.get_or_create(
        batch=batch, subject=subject_phy, teacher=teacher, day_of_week='MONDAY',
        defaults={'start_time': time(9, 0), 'end_time': time(10, 30), 'room_number': 'Lab 201'}
    )
    lec, _ = Lecture.objects.get_or_create(
        timetable=tt, date=date.today(),
        defaults={'topic': 'React State Management & Async REST APIs', 'status': 'COMPLETED'}
    )
    Attendance.objects.get_or_create(lecture=lec, student=student_user, defaults={'status': 'PRESENT', 'remarks': 'Active participant'})

    # 7. Assignment & Exam
    assign, _ = Assignment.objects.get_or_create(
        subject=subject_phy, batch=batch, title='Fullstack Project #3 - Node & Express API',
        defaults={'description': 'Build CRUD RESTful endpoints with authentication JWT', 'total_marks': 50, 'due_date': timezone.now() + timedelta(days=5), 'created_by': teacher}
    )
    Submission.objects.get_or_create(
        assignment=assign, student=student_user,
        defaults={'file_url': 'https://s3.amazonaws.com/institute-crm-storage-bucket/submissions/rohan_ps3.pdf', 'marks_obtained': 45.0, 'evaluated_by': teacher}
    )

    exam, _ = Exam.objects.get_or_create(
        subject=subject_phy, batch=batch, title='Module Assessment 1 - Web Development',
        defaults={'total_marks': 100, 'passing_marks': 40, 'exam_date': timezone.now() - timedelta(days=7)}
    )
    Result.objects.get_or_create(exam=exam, student=student_user, defaults={'marks_obtained': 88.5, 'grade': 'A+', 'remarks': 'Excellent performance in API design'})

    # 8. Finance - Fee Structure, Installments, Payments
    fee_struct, _ = FeeStructure.objects.get_or_create(course=course, defaults={'total_amount': 120000.00, 'deposit_amount': 30000.00, 'num_installments': 3})
    inst1, _ = Installment.objects.get_or_create(
        student=student_user, fee_structure=fee_struct, installment_number=1,
        defaults={'due_date': date.today() - timedelta(days=30), 'amount': 40000.00, 'status': 'PAID'}
    )

    inst2, _ = Installment.objects.get_or_create(
        student=student_user, fee_structure=fee_struct, installment_number=2,
        defaults={'due_date': date.today() + timedelta(days=30), 'amount': 40000.00, 'status': 'PENDING'}
    )

    pay, _ = Payment.objects.get_or_create(
        reference_number='REF-TXN-998811',
        defaults={'student': student_user, 'installment': inst1, 'amount': 40000.00, 'payment_mode': 'UPI', 'recorded_by': accountant}
    )
    Receipt.objects.get_or_create(payment=pay, defaults={'receipt_number': 'REC-2026-001', 'pdf_url': 'https://s3.amazonaws.com/institute-crm-storage-bucket/receipts/REC-2026-001.pdf'})

    # 9. Communications
    Announcement.objects.get_or_create(
        title='Upcoming All-India Mock Test Series',
        defaults={'branch': b_pune, 'content': 'Full syllabus mock test will be conducted on Sunday at 10 AM.', 'published_by': super_admin}
    )
    Notification.objects.get_or_create(
        recipient=student_user,
        defaults={'title': 'Assignment Marks Uploaded', 'message': 'Dr. Alok Gupta evaluated your Physics PS#3 assignment.', 'channel': 'IN_APP'}
    )

    print(" [SUCCESS] Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
