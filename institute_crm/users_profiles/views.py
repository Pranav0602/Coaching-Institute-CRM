"""
HTTP controller layer for the users_profiles app.
Views validate incoming requests and delegate business logic to ProfileService.
"""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users_profiles.models import StudentProfile, TeacherProfile, ParentProfile
from users_profiles.serializers import (
    StudentProfileSerializer, TeacherProfileSerializer, ParentProfileSerializer
)
from users_profiles.services import ProfileService


class StudentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProfileService.filter_students(
            self.request.user,
            batch_id=self.request.query_params.get('batch_id'),
            course_id=self.request.query_params.get('course_id'),
            branch_id=self.request.query_params.get('branch_id'),
            search=self.request.query_params.get('search'),
        )

    def perform_update(self, serializer):
        profile = serializer.instance
        ProfileService.update_student_profile(
            actor=self.request.user,
            profile=profile,
            data=serializer.validated_data,
        )


class TeacherProfileViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProfileService.filter_teachers(
            self.request.user,
            branch_id=self.request.query_params.get('branch_id'),
            search=self.request.query_params.get('search'),
        )


class ParentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ParentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProfileService.filter_parents(
            self.request.user,
            search=self.request.query_params.get('search'),
        )
