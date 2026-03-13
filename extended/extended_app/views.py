from django.utils import timezone
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
      recorded_at = timezone.now()  # capture once for the whole batch

      try:
         esp32 = ESP32.objects.get(esp32_id=data['esp32_id'])
      except ESP32.DoesNotExist:
         return Response(
            status=status.HTTP_404_NOT_FOUND
         )

      # The last reading's timestamp_ms is the anchor for projecting all timestamps
      anchor_timestamp_ms = data['readings'][-1]['timestamp_ms']

      saved_readings = 0
      for reading in data['readings']:
         try:
            outlet = Outlet.objects.get(esp32=esp32, outlet_index=reading['outlet_index'])
            r = PowerReading(
               outlet=outlet,
               amperage=reading['amperage'],
               volts=reading['volts'],
               timestamp_ms=reading['timestamp_ms'],
               button_state=reading['button_state']
            )
            r.save(
               anchor_timestamp_ms=anchor_timestamp_ms,
               recorded_at=recorded_at,
            )
            saved_readings += 1
         except Outlet.DoesNotExist:
            continue

      return Response(
         status=status.HTTP_201_CREATED
      )