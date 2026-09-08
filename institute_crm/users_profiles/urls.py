from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users_profiles.views import (
    StudentProfileViewSet, TeacherProfileViewSet, ParentProfileViewSet
)

router = DefaultRouter()
router.register(r'students', StudentProfileViewSet, basename='student-profile')
router.register(r'teachers', TeacherProfileViewSet, basename='teacher-profile')
router.register(r'parents', ParentProfileViewSet, basename='parent-profile')

urlpatterns = [
    path('', include(router.urls)),
]
