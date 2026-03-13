from django.urls import path
from .views import ReceiveReadingsView

urlpatterns = [
    path('readings/', ReceiveReadingsView.as_view(), name='receive-readings'),
]