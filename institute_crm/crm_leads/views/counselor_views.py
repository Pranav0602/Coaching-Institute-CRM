from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from crm_leads.models import Lead, FollowUp, CounsellingNote, Admission, Visitor
from crm_leads.serializers import (
    LeadSerializer, FollowUpSerializer, CounsellingNoteSerializer, 
    AdmissionSerializer, VisitorSerializer, LeadConvertSerializer
)
from crm_leads.services.lead_service import LeadService
from accounts.models import Role

class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.filter(is_deleted=False).select_related('branch', 'lead_owner')
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        stage = self.request.query_params.get('stage')
        branch_id = self.request.query_params.get('branch_id')
        course_id = self.request.query_params.get('course_id')
        if stage:
            qs = qs.filter(stage=stage)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if course_id:
            qs = qs.filter(course_id=course_id)
        if self.request.user.role and self.request.user.role.code in [Role.ADMISSION_COUNSELOR]:
            qs = qs.filter(Q(lead_owner=self.request.user) | Q(lead_owner__isnull=True))
        return qs

    @action(detail=False, methods=['get'], url_path='stage-counts')
    def stage_counts(self, request):
        counts = self.get_queryset().values('stage').annotate(count=Count('id'))
        result = {}
        for c in counts:
            result[c['stage']] = c['count']
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='convert')
    def convert_to_student(self, request, pk=None):
        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            res = LeadService.convert_lead_to_student(
                lead_id=pk,
                course_id=serializer.validated_data['course_id'],
                batch_id=serializer.validated_data['batch_id'],
                agreed_fee=serializer.validated_data['agreed_fee'],
                created_by_user=request.user
            )
            return Response(res, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        leads_data = request.data.get('leads', [])
        result = LeadService.bulk_import_leads(
            leads_data=leads_data,
            owner_user=request.user
        )
        return Response(result, status=status.HTTP_200_OK)


class FollowUpViewSet(viewsets.ModelViewSet):
    queryset = FollowUp.objects.filter(is_deleted=False).select_related('lead', 'counselor')
    serializer_class = FollowUpSerializer
    permission_classes = [IsAuthenticated]


class CounsellingNoteViewSet(viewsets.ModelViewSet):
    queryset = CounsellingNote.objects.filter(is_deleted=False).select_related('lead', 'author')
    serializer_class = CounsellingNoteSerializer
    permission_classes = [IsAuthenticated]


class AdmissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Admission.objects.filter(is_deleted=False).select_related('lead', 'student_user', 'course', 'batch')
    serializer_class = AdmissionSerializer
    permission_classes = [IsAuthenticated]


class VisitorViewSet(viewsets.ModelViewSet):
    queryset = Visitor.objects.filter(is_deleted=False).select_related('branch', 'host_staff')
    serializer_class = VisitorSerializer
    permission_classes = [IsAuthenticated]
