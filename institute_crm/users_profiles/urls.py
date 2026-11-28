from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from users_profiles.views import (
    StudentProfileViewSet, TeacherProfileViewSet, ParentProfileViewSet
)

router = DefaultRouter()
router.register(r'students', StudentProfileViewSet, basename='student-profile')
router.register(r'teachers', TeacherProfileViewSet, basename='teacher-profile')
router.register(r'parents', ParentProfileViewSet, basename='parent-profile')

# Custom student actions are registered explicitly BEFORE the router's greedy
# `(?P<pk>.+)/$` detail route so action suffixes are never swallowed into `pk`
# (registration numbers may themselves contain slashes, e.g. ENR/BR/2026/001).
student_action_view = StudentProfileViewSet.as_view

urlpatterns = [
    re_path(
        r'^students/(?P<pk>.+)/id-card/$',
        student_action_view({'get': 'id_card'}),
        name='student-profile-id-card',
    ),
    re_path(
        r'^students/(?P<pk>.+)/cancel-admission/$',
        student_action_view({'post': 'cancel_admission'}),
        name='student-profile-cancel-admission',
    ),
    re_path(
        r'^students/(?P<pk>.+)/deletion-eligibility/$',
        student_action_view({'get': 'deletion_eligibility'}),
        name='student-profile-deletion-eligibility',
    ),
    path('', include(router.urls)),
]
