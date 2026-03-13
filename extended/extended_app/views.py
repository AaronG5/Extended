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
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      data = serializer.validated_data
      recorded_at = timezone.now()  # capture once for the whole batch


      esp32, created = ESP32.objects.get_or_create(esp32_id=data['esp32_id'])
      if created:
         for i in range(4):
            Outlet.objects.create(esp32=esp32, outlet_index=i)

      # The last reading's timestamp_ms is the anchor for projecting all timestamps
      anchor_timestamp_ms = data['readings'][-1]['timestamp_ms']

      saved_readings = 0
      for reading in data['readings']:
         try:
            outlet = Outlet.objects.get(esp32=esp32, outlet_index=reading['outlet_index'])
            r = PowerReading(
               outlet=outlet,
               amperage=reading['amperage'],
               voltage=reading['voltage'],
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
         {'message': f'{saved_readings} readings saved'},
         status=status.HTTP_201_CREATED
      )
   