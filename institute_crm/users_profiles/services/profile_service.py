"""
Service layer for users_profiles.
Encapsulates business logic for Student, Teacher, and Parent profiles.
"""
from __future__ import annotations

import logging
from typing import Any
from django.db import transaction
from django.db.models import Q, QuerySet

from accounts.models import Role, User
from users_profiles.models import StudentProfile, TeacherProfile, ParentProfile, StudentParent

logger = logging.getLogger('institute_crm.profiles')


class ProfileService:
    @staticmethod
    def filter_students(
        actor: User,
        *,
        batch_id: str | None = None,
        course_id: str | None = None,
        branch_id: str | None = None,
        search: str | None = None,
    ) -> QuerySet[StudentProfile]:
        qs = StudentProfile.objects.filter(is_deleted=False).select_related(
            'user', 'user__branch', 'batch', 'batch__course'
        )

        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        if course_id:
            qs = qs.filter(
                Q(batch__course_id=course_id) | Q(user__enrolments__course_id=course_id)
            ).distinct()
        if branch_id:
            qs = qs.filter(user__branch_id=branch_id)

        if search:
            search = search.strip()
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(enrollment_number__icontains=search)
            )

        # Scoping based on actor role
        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code in [Role.BRANCH_ADMIN, Role.RECEPTIONIST, Role.ACCOUNTANT] and actor.branch:
                qs = qs.filter(user__branch=actor.branch)
            elif role_code == Role.TEACHER:
                if not (batch_id or course_id or branch_id):
                    qs = qs.filter(batch__timetables__teacher=actor).distinct()
            elif role_code == Role.STUDENT:
                qs = qs.filter(user=actor)
            elif role_code == Role.PARENT:
                qs = qs.filter(parent_links__parent__user=actor)

        return qs

    @staticmethod
    def filter_teachers(
        actor: User,
        *,
        branch_id: str | None = None,
        search: str | None = None,
    ) -> QuerySet[TeacherProfile]:
        qs = TeacherProfile.objects.filter(is_deleted=False).select_related('user', 'user__branch')

        if branch_id:
            qs = qs.filter(user__branch_id=branch_id)
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(employee_id__icontains=search)
                | Q(qualification__icontains=search)
                | Q(specialization__icontains=search)
            )

        if actor and actor.is_authenticated and actor.role:
            if actor.role.code in [Role.BRANCH_ADMIN, Role.RECEPTIONIST] and actor.branch:
                qs = qs.filter(user__branch=actor.branch)

        return qs

    @staticmethod
    def filter_parents(
        actor: User,
        *,
        search: str | None = None,
    ) -> QuerySet[ParentProfile]:
        qs = ParentProfile.objects.filter(is_deleted=False).select_related('user')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(occupation__icontains=search)
            )
        return qs

    @staticmethod
    @transaction.atomic
    def update_student_profile(
        actor: User,
        profile: StudentProfile,
        data: dict[str, Any],
    ) -> StudentProfile:
        allowed_fields = {'dob', 'gender', 'blood_group', 'address', 'emergency_contact', 'batch'}
        for field, value in data.items():
            if field in allowed_fields:
                setattr(profile, field, value)
        profile.save()
        return profile

    @staticmethod
    @transaction.atomic
    def link_parent_to_student(
        student_profile: StudentProfile,
        parent_profile: ParentProfile,
        is_primary: bool = True,
    ) -> StudentParent:
        link, created = StudentParent.objects.update_or_create(
            student=student_profile,
            parent=parent_profile,
            defaults={'is_primary': is_primary}
        )
        return link
