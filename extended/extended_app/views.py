from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ESP32, Outlet, PowerReading
from .serializers import ESP32PayloadSerializer
from .utils import normalize_current, normalize_voltage


class ReceiveReadingsView(APIView):
   def post(self, request):
      print(request.data)
      serializer = ESP32PayloadSerializer(data=request.data)

      if not serializer.is_valid():
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      data = serializer.validated_data
      recorded_at = timezone.now()

      esp32, created = ESP32.objects.get_or_create(esp32_id=data['id'])
      if created:
         for i in range(4):
            Outlet.objects.create(esp32=esp32, outlet_index=i)

      saved_readings = 0
      # anchor_timestamp_ms = reading['timestamp_ms']
      anchor_timestamp_ms = max(r["timestamp_ms"] for r in data["readings"])
      for reading in data['readings']:
         voltage = reading['voltage']

         for outlet_index in range(4):
            raw_current = reading[f'current_{outlet_index + 1}']
            button_state = reading[f'button_{outlet_index + 1}']
            try:
               outlet = Outlet.objects.get(esp32=esp32, outlet_index=outlet_index)
               r = PowerReading(
                  outlet=outlet,
                  amperage=normalize_current(raw_current),
                  voltage=normalize_voltage(reading['voltage']),
                  timestamp_ms=reading['timestamp_ms'],
                  button_state=button_state,
               )
               r.save(
                  anchor_timestamp_ms=anchor_timestamp_ms,
                  recorded_at=recorded_at,
               )
               saved_readings += 1
            except Outlet.DoesNotExist:
               continue

      return Response(
         {'message': f'{saved_readings} readings saved'},
         status=status.HTTP_201_CREATED
      )
class ESP32DashboardView(APIView):
   def get(self, request, esp32_id):
      try:
         esp32 = ESP32.objects.get(esp32_id=esp32_id)
      except ESP32.DoesNotExist:
         return Response(
            {'error': 'ESP32 not found'},
            status=status.HTTP_404_NOT_FOUND
         )
      
      outlets = Outlet.objects.filter(esp32=esp32).prefetch_related('readings')
      # TODO: add serialization and change the data that is supposed to be sent
