from django.urls import path
from .views import (
    ReceiveReadingsView,
    ListESP32View,
    ClassifyDeviceView,
    ClassifyLatestDeviceView,
    ESP32DashboardView,
    ESP32LatestReadingsView
)

urlpatterns = [
    path('readings/', ReceiveReadingsView.as_view(), name='receive-readings'),
    path('devices/', ListESP32View.as_view(), name='list-devices'),
    path('classify/', ClassifyDeviceView.as_view(), name='classify-device'),
    path('classify-latest/', ClassifyLatestDeviceView.as_view(), name='classify-latest-device'),
    path('dashboard/<str:esp32_id>/', ESP32DashboardView.as_view(), name='esp32-dashboard'),
    path('latest/<str:esp32_id>/', ESP32LatestReadingsView.as_view(), name='esp32-latest'),
]