"""
HTTP controller layer for the users_profiles app.
Views validate incoming requests and delegate business logic to ProfileService.
"""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.models import Role
from users_profiles.models import StudentProfile, TeacherProfile, ParentProfile
from users_profiles.serializers import (
    StudentProfileSerializer, TeacherProfileSerializer, ParentProfileSerializer
)
from users_profiles.services import ProfileService
from institute_crm.exceptions import ValidationFailed
from institute_crm.pagination import OptionalPageNumberPagination
from institute_crm.scoping import assert_role, is_global

#: Roles allowed to turn a scanned ID into a student record. Students and parents are
#: excluded on purpose: an enrollment number is a lookup key, and letting any
#: authenticated account resolve arbitrary ones turns it into an enumeration oracle.
QR_RESOLVER_ROLES = (
    Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.RECEPTIONIST,
    Role.ADMISSION_COUNSELOR, Role.TEACHER,
)


class StudentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination
    # Registration numbers can contain slashes (for example ENR/BR/2026/001).
    lookup_value_regex = r'.+'

    def get_queryset(self):
        params = self.request.query_params
        return ProfileService.filter_students(
            self.request.user,
            batch_id=params.get('batch_id'),
            course_id=params.get('course_id'),
            branch_id=params.get('branch_id'),
            branch_ids=params.getlist('branch_ids') or params.get('branch_ids'),
            search=params.get('search'),
        )

    def update(self, request, *args, **kwargs):
        # Unauthorized users are rejected before any object lookup.
        ProfileService.assert_student_profile_editor(request.user)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        profile = serializer.instance
        ProfileService.update_student_profile(
            actor=self.request.user,
            profile=profile,
            data=serializer.validated_data,
        )

    def destroy(self, request, *args, **kwargs):
        """Remove a cancelled-admission student from active views.

        Server-enforced: reception desk or admin, branch scope, eligible
        cancelled-admission record only, explicit confirmation required.
        Soft-delete - nothing is hard-erased; history and audit are retained.
        """
        # Role check first (does not reveal whether the record exists).
        ProfileService.assert_student_admin(request.user)
        profile = self.get_object()
        data = request.data if isinstance(request.data, dict) else {}
        ProfileService.delete_cancelled_student(
            actor=request.user,
            profile=profile,
            reason=data.get('reason') or data.get('deletion_reason'),
            confirm=bool(data.get('confirm') or data.get('confirmed')),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def assign_batch(self, request, pk=None):
        """Assign a valid batch to a student (or clear it)."""
        ProfileService.assert_student_profile_editor(request.user)
        profile = self.get_object()
        data = request.data if isinstance(request.data, dict) else {}
        updated = ProfileService.assign_batch(
            actor=request.user,
            profile=profile,
            batch=data.get('batch'),
        )
        return Response(StudentProfileSerializer(updated, context={'request': request}).data)

    def cancel_admission(self, request, pk=None):
        """Mark a student's admission cancelled (with optional reason)."""
        ProfileService.assert_student_admin(request.user)
        profile = self.get_object()
        data = request.data if isinstance(request.data, dict) else {}
        updated = ProfileService.cancel_admission(
            actor=request.user,
            profile=profile,
            reason=data.get('reason') or data.get('cancellation_reason'),
        )
        return Response(StudentProfileSerializer(updated, context={'request': request}).data)

    def deletion_eligibility(self, request, pk=None):
        """Whether this record may currently be removed, and why not."""
        profile = self.get_object()
        blocked = ProfileService.deletion_blocked_reason(profile)
        return Response({
            'eligible': blocked is None,
            'admission_status': profile.admission_status,
            'reason': blocked,
        })

    @action(detail=True, methods=['get'], url_path='id-card')
    def id_card(self, request, pk=None):
        """Everything the app needs to render or print an ID card for one student.

        Returned as its own action rather than derived client-side from the list
        payload so reception staff can open a single card without paging through
        every student in the branch first.
        """
        profile = self.get_queryset().filter(pk=pk).select_related(
            'user', 'batch', 'batch__course', 'batch__branch'
        ).first()
        if profile is None:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        batch = profile.batch
        course = getattr(batch, 'course', None) if batch else None
        branch = getattr(batch, 'branch', None) if batch else None
        return Response(
            {
                'student_id': str(profile.pk),
                'user_id': str(profile.user_id),
                'full_name': profile.user.get_full_name() or profile.user.username,
                'username': profile.user.username,
                'phone': profile.user.phone,
                'secondary_phone': profile.secondary_phone,
                'email': profile.user.email,
                'reg_no': profile.reg_no,
                # Compatibility alias for clients that still read the old key.
                'enrollment_number': profile.reg_no,
                'qr_payload': profile.qr_payload,
                'dob': profile.dob,
                'gender': profile.gender,
                'blood_group': profile.blood_group,
                'address': profile.address,
                'emergency_contact': profile.emergency_contact,
                'batch': str(batch.pk) if batch else None,
                'batch_name': getattr(batch, 'name', None),
                'batch_code': getattr(batch, 'code', None),
                'course_title': getattr(course, 'title', None),
                'branch_name': getattr(branch, 'name', None),
                'branch_code': getattr(branch, 'code', None),
                'profile_photo_url': profile.user.profile_photo_url,
            }
        )

    @action(detail=False, methods=['post'], url_path='resolve-qr')
    def resolve_qr(self, request):
        """Look up a student from a scanned ``graphix://student/<reg_no>`` code."""
        assert_role(
            request.user,
            QR_RESOLVER_ROLES,
            message='Only staff can scan student ID cards.',
        )
        payload = str(request.data.get('qr_payload') or '').strip()
        if not payload:
            raise ValidationFailed(
                'A QR payload is required.',
                field_errors={'qr_payload': ['This field is required.']},
            )

        profile = StudentProfile.from_qr_payload(payload)
        # Scoped to the resolver's own branch unless they are global, so a scan at
        # one campus cannot confirm the roster of another.
        if profile is not None and not is_global(request.user):
            own_branch = getattr(request.user, 'branch_id', None)
            candidate_branch = getattr(getattr(profile.batch, 'branch', None), 'pk', None)
            if own_branch is None or str(candidate_branch) != str(own_branch):
                profile = None

        if profile is None:
            return Response(
                {
                    'matched': False,
                    'detail': 'No active student matches that code at your campus.',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'matched': True, 'student': StudentProfileSerializer(profile).data})


class TeacherProfileViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        params = self.request.query_params
        return ProfileService.filter_teachers(
            self.request.user,
            branch_id=params.get('branch_id'),
            branch_ids=params.getlist('branch_ids') or params.get('branch_ids'),
            search=params.get('search'),
        )


class ParentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ParentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProfileService.filter_parents(
            self.request.user,
            search=self.request.query_params.get('search'),
        )
