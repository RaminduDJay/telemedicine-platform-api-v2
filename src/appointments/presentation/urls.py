from django.urls import path

from appointments.presentation.views import AppointmentCancelView, AppointmentListCreateView

urlpatterns = [
    path("", AppointmentListCreateView.as_view(), name="appointments-list-create"),
    path(
        "<str:appointment_id>/cancel/",
        AppointmentCancelView.as_view(),
        name="appointments-cancel",
    ),
]
