from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ESP32, Outlet, PowerReading
from .serializers import ESP32PayloadSerializer


class ReceiveReadingsView(APIView):
   def post(self, request):
      serializer = ESP32PayloadSerializer(data=request.data)

      if not serializer.is_valid():
         return Response(status=status.HTTP_400_BAD_REQUEST)
      
      data = serializer.validated_data

      try:
         esp32 = ESP32.objects.get(esp32_id=data['esp32_id'])
      except ESP32.DoesNotExist:
         return Response(status=status.HTTP_404_NOT_FOUND)
      
      saved_readings = 0
      for reading in data['readings']:
         try:
            amperage = reading['amperage']
            voltage = reading['voltage']
            PowerReading.objects.create(
               outlet = Outlet.objects.get(esp32=esp32, outlet_index=reading['outlet_index']),
               amperage = amperage,
               voltage = voltage,
               wattage = amperage * voltage,
               timestamp_ms = reading['timestamp_ms']
            )
            saved_readings += 1
         except Outlet.DoesNotExist:
            continue

      return Response(status=status.HTTP_200_OK)

