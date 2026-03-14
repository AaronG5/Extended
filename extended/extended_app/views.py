from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ESP32, Outlet, Device, PowerReading
from .serializers import ESP32PayloadSerializer, ESP32DashboardSerializer, WattageReadingSerializer
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

class OutletReadingsView(APIView):
   PERIODS = {'hour': 1, 'day': 24, 'week': 168}

   def get(self, request, esp32_id):
      period = request.query_params.get('period', 'hour')
      outlet_index = request.query_params.get('outlet_index')

      if period not in self.PERIODS:
         return Response(
            {'error': f'period must be one of: {list(self.PERIODS)}'},
            status=status.HTTP_400_BAD_REQUEST
         )
      if outlet_index is None:
         return Response({'error': 'outlet_index is required'}, status=status.HTTP_400_BAD_REQUEST)
      try:
         outlet_index = int(outlet_index)
      except ValueError:
         return Response({'error': 'outlet_index must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

      try:
         outlet = Outlet.objects.get(esp32__esp32_id=esp32_id, outlet_index=outlet_index)
      except Outlet.DoesNotExist:
         return Response({'error': 'Outlet not found'}, status=status.HTTP_404_NOT_FOUND)

      since = timezone.now() - timedelta(hours=self.PERIODS[period])
      readings = (
         outlet.readings
         .filter(recorded_at__gte=since)
         .order_by('projected_timestamp', 'recorded_at')
         .values('wattage', 'projected_timestamp', 'recorded_at')
      )

      data = [
         {
            'timestamp': r['projected_timestamp'] or r['recorded_at'],
            'wattage': r['wattage'],
         }
         for r in readings
      ]

      serializer = WattageReadingSerializer(data=data, many=True)
      serializer.is_valid(raise_exception=True)
      return Response(serializer.data)


class ListESP32View(APIView):
   def get(self, request):
      esp32s = ESP32.objects.values_list('esp32_id', flat=True)
      return Response({'devices': list(esp32s)})


class ESP32DashboardView(APIView):
   def get(self, request, esp32_id):
      try:
         esp32 = ESP32.objects.get(esp32_id=esp32_id)
      except ESP32.DoesNotExist:
         return Response(
            {'error': 'ESP32 not found'},
            status=status.HTTP_404_NOT_FOUND
         )

      outlets_data = []
      for outlet in Outlet.objects.filter(esp32=esp32).order_by('outlet_index'):
         readings = outlet.readings.order_by('recorded_at')
         reading_count = readings.count()

         latest = readings.last()

         kwh_recorded = 0.0
         if reading_count > 1 and latest:
            first = readings.first()
            t_start = first.projected_timestamp or first.recorded_at
            t_end = latest.projected_timestamp or latest.recorded_at
            total_hours = (t_end - t_start).total_seconds() / 3600
            if total_hours > 0:
               avg_wattage = sum(r.wattage for r in readings) / reading_count
               kwh_recorded = round(avg_wattage * total_hours / 1000, 6)

         try:
            device_type = outlet.device_type.device_type
         except Device.DoesNotExist:
            device_type = None

         outlets_data.append({
            'outlet_index': outlet.outlet_index,
            'device_type': device_type,
            'button_state': latest.button_state if latest else None,
            'wattage': latest.wattage if latest else None,
            'kwh_recorded': kwh_recorded,
         })

      serializer = ESP32DashboardSerializer(data={'esp32_id': esp32_id, 'outlets': outlets_data})
      serializer.is_valid(raise_exception=True)
      return Response(serializer.data)
