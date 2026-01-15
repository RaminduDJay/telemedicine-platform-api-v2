from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.appointments.views import AppointmentViewSet, DoctorSearchViewSet

router = DefaultRouter()
router.register(r'', AppointmentViewSet, basename='appointment')
router.register(r'search', DoctorSearchViewSet, basename='doctor-search')

urlpatterns = [
    path('', include(router.urls)),
]
