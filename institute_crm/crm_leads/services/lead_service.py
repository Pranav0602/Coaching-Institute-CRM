"""
Lead Management & Conversion Service Layer
Encapsulates business logic for Lead workflows, follow-ups, auto-conversion to Student accounts, bulk importing, and public enquiries.
"""
import uuid
import logging
from django.db import transaction
from django.utils import timezone
from accounts.models import User, Role, Branch
from users_profiles.models import StudentProfile
from crm_leads.models import Lead, Admission
from crm_leads.serializers import LeadSerializer
from academics.models import Course, Batch, CourseEnrolment
from finance.models import FeeStructure, Installment
from aws_services.cognito_service import cognito_service
from aws_services.ses_sns_service import notification_service

logger = logging.getLogger('institute_crm.leads')

class LeadService:
    @staticmethod
    @transaction.atomic
    def convert_lead_to_student(lead_id, course_id, batch_id, agreed_fee, created_by_user):
        """
        Automated Lead Conversion Workflow:
        1. Validates Lead existence and stage.
        2. Creates Student User account.
        3. Provisions AWS Cognito User.
        4. Creates StudentProfile & CourseEnrolment.
        5. Generates Fee Installments.
        6. Sends Welcome Email via AWS SES.
        7. Updates Lead stage to 'Admitted'.
        """
        lead = Lead.objects.select_for_update().get(id=lead_id)
        if lead.stage == Lead.STAGE_ADMITTED:
            raise ValueError(f"Lead '{lead.name}' is already admitted.")

        course = Course.objects.get(id=course_id)
        batch = Batch.objects.get(id=batch_id)
        student_role = Role.objects.get(code=Role.STUDENT)

        # 1. Username and Temporary Password generation
        clean_name = "".join(e for e in lead.name.lower() if e.isalnum())
        username = f"std_{clean_name[:8]}_{uuid.uuid4().hex[:4]}"
        temp_password = f"Pass@{uuid.uuid4().hex[:6]}"

        # 2. Create Django User
        student_user = User.objects.create_user(
            username=username,
            email=lead.email,
            password=temp_password,
            first_name=lead.name.split()[0],
            last_name=" ".join(lead.name.split()[1:]) if len(lead.name.split()) > 1 else "",
            role=student_role,
            branch=lead.branch,
            phone=lead.phone
        )

        # 3. Provision AWS Cognito User
        cognito_sub = f"sub-{uuid.uuid4()}"
        try:
            cognito_res = cognito_service.create_user(
                email=lead.email,
                temporary_password=temp_password,
                role_name=Role.STUDENT,
                attributes={'custom:branch': lead.branch.code}
            )
            cognito_sub = cognito_res.get('User', {}).get('Username', cognito_sub)
        except Exception as e:
            logger.warning(f"Cognito provisioning failed, using fallback sub: {str(e)}")

        student_user.cognito_sub = cognito_sub
        student_user.save()

        # 4. Create Student Profile
        enrollment_no = f"ENR/{lead.branch.code}/{timezone.now().year}/{uuid.uuid4().hex[:5].upper()}"
        student_profile = StudentProfile.objects.create(
            user=student_user,
            enrollment_number=enrollment_no,
            batch=batch
        )

        # 5. Course Enrolment
        enrolment = CourseEnrolment.objects.create(
            student=student_user,
            course=course,
            batch=batch,
            status='ACTIVE'
        )

        # 6. Admission record
        admission = Admission.objects.create(
            lead=lead,
            student_user=student_user,
            course=course,
            batch=batch,
            agreed_fee=agreed_fee,
            admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}"
        )

        # 7. Fee Installments generation
        fee_structure = FeeStructure.objects.filter(course=course).first()
        if fee_structure:
            num_inst = fee_structure.num_installments or 3
            inst_amount = agreed_fee / num_inst
            for i in range(1, num_inst + 1):
                due_date = timezone.now().date() + timezone.timedelta(days=30 * (i - 1))
                Installment.objects.create(
                    student=student_user,
                    fee_structure=fee_structure,
                    installment_number=i,
                    due_date=due_date,
                    amount=inst_amount,
                    status='PENDING'
                )

        # 8. Dispatch Welcome Email via AWS SESDownload Qwen
        # For Mobile
        # Chat on the go, have voice conversations, and ask about photos
        
        email_body = f"""
        <h2>Welcome to {lead.branch.name} Coaching Institute!</h2>
        <p>Dear {lead.name},</p>
        <p>Congratulations! Your admission for <strong>{course.title}</strong> has been successfully processed.</p>
        <p>Here are your login credentials for the Student Portal:</p>
        <ul>
            <li><strong>Portal URL:</strong> https://crm.coachinginstitute.com/login</li>
            <li><strong>Username:</strong> {username}</li>
            <li><strong>Temporary Password:</strong> {temp_password}</li>
            <li><strong>Enrollment No:</strong> {enrollment_no}</li>
            <li><strong>Batch:</strong> {batch.name}</li>
        </ul>
        <p>Please change your password upon your first login.</p>
        <br>
        <p>Best regards,<br>Admission Desk, {lead.branch.name}</p>
        """
        notification_service.send_email(
            recipient_email=lead.email,
            subject=f"Welcome to {lead.branch.name} - Student Credentials",
            body_html=email_body
        )

        # 9. Update Lead Stage to ADMITTED
        lead.stage = Lead.STAGE_ADMITTED
        lead.save()

        return {
            "lead_id": str(lead.id),
            "student_user_id": str(student_user.id),
            "username": username,
            "enrollment_number": enrollment_no,
            "admission_number": admission.admission_number,
            "temporary_password": temp_password
        }

    @staticmethod
    @transaction.atomic
    def bulk_import_leads(leads_data: list, owner_user) -> dict:
        """
        Bulk creates leads from JSON import data.
        """
        created = []
        for l in leads_data:
            lead = Lead.objects.create(
                name=l.get('name'),
                email=l.get('email'),
                phone=l.get('phone'),
                branch_id=l.get('branch_id', getattr(owner_user, 'branch_id', None)),
                target_course=l.get('target_course', 'General'),
                source=l.get('source', 'WEBSITE'),
                lead_owner=owner_user
            )
            created.append(LeadSerializer(lead).data)
        return {
            "imported_count": len(created),
            "leads": created
        }

    @staticmethod
    def create_public_enquiry(name: str, email: str, phone: str, branch_id=None, target_course='General', notes='') -> Lead:
        """
        Validates branch assignment and creates a new lead enquiry submitted from the public portal.
        """
        if not name or not email or not phone:
            raise ValueError("Name, Email, and Phone number are required fields.")

        branch = None
        if branch_id:
            branch = Branch.objects.filter(id=branch_id, is_deleted=False).first()
        if not branch:
            branch = Branch.objects.filter(is_deleted=False).first()

        if not branch:
            raise ValueError("No active branch found to assign enquiry.")

        lead = Lead.objects.create(
            name=name,
            email=email,
            phone=phone,
            branch=branch,
            target_course=target_course,
            source='WEBSITE',
            stage=Lead.STAGE_NEW,
            notes=notes
        )
        return lead
