from django.urls import path
from .views import ReceiveReadingsView, ESP32DashboardView

urlpatterns = [
    path('readings/', ReceiveReadingsView.as_view(), name='receive-readings'),
    path('dashboard/<str:esp32_id>/', ESP32DashboardView.as_view(), name='esp32-dashboard'),
]