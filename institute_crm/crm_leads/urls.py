from django.urls import path, include
from rest_framework.routers import DefaultRouter
from crm_leads.views import (
    LeadViewSet, FollowUpViewSet, CounsellingNoteViewSet, 
    AdmissionViewSet, VisitorViewSet, PublicLeadEnquiryView, PublicOptionsView
)

router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'follow-ups', FollowUpViewSet, basename='followup')
router.register(r'counselling-notes', CounsellingNoteViewSet, basename='counsellingnote')
router.register(r'admissions', AdmissionViewSet, basename='admission')
router.register(r'visitors', VisitorViewSet, basename='visitor')

urlpatterns = [
    path('public-enquiry/', PublicLeadEnquiryView.as_view(), name='public_lead_enquiry'),
    path('public-options/', PublicOptionsView.as_view(), name='public_options'),
    path('', include(router.urls)),
]

