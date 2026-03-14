from django.urls import path
from .views import ReceiveReadingsView, ListESP32View, OutletReadingsView, ESP32DashboardView

urlpatterns = [
    path('readings/', ReceiveReadingsView.as_view(), name='receive-readings'),
    path('devices/', ListESP32View.as_view(), name='list-devices'),
    path('dashboard/<str:esp32_id>/', ESP32DashboardView.as_view(), name='esp32-dashboard'),
    path('outlet/<str:esp32_id>/readings/', OutletReadingsView.as_view(), name='outlet-readings'),
]