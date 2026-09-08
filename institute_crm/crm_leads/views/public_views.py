from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from crm_leads.serializers import LeadSerializer
from crm_leads.services.lead_service import LeadService
from accounts.models import Branch
from academics.models import Course

class PublicLeadEnquiryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        branch_id = request.data.get('branch_id')
        target_course = request.data.get('target_course', 'General')
        notes = request.data.get('notes', '')

        try:
            lead = LeadService.create_public_enquiry(
                name=name,
                email=email,
                phone=phone,
                branch_id=branch_id,
                target_course=target_course,
                notes=notes
            )
            return Response({
                "detail": "Enquiry submitted successfully! Our admission counselor will contact you soon.",
                "lead": LeadSerializer(lead).data
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicOptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        branches = Branch.objects.filter(is_deleted=False).values('id', 'name', 'city', 'code')
        courses = Course.objects.filter(is_deleted=False).values('id', 'code', 'title', 'total_fee', 'field_of_engineering')
        fields = [
            {'id': '1', 'name': 'Mechanical CAD/CAM/CAE'},
            {'id': '2', 'name': 'Civil CAD'},
            {'id': '3', 'name': 'Electrical CAD'},
            {'id': '4', 'name': 'Design & BIM'},
            {'id': '5', 'name': 'Data Science & AI/ML'},
            {'id': '6', 'name': 'IT & Software Development'},
            {'id': '7', 'name': 'Cloud Computing'}
        ]
        return Response({
            "branches": list(branches),
            "courses": list(courses),
            "fields": fields
        })
