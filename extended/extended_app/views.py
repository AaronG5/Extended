import json
import os
from urllib import error, request as urllib_request

from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ESP32, Outlet, Device, PowerReading
from .serializers import (
   ESP32PayloadSerializer,
   ClassifierInputSerializer,
   ClassifierLatestRequestSerializer,
)
from .utils import normalize_voltage, normalize_current, abs_wattage
from .anomaly_detection import run_per_reading_checks, run_periodic_checks


def call_classifier(payload):
   classifier_url = os.getenv('CLASSIFIER_URL', 'http://classifier:8000').rstrip('/')
   validation_url = f'{classifier_url}/validation'
   req = urllib_request.Request(
      validation_url,
      data=json.dumps(payload).encode('utf-8'),
      headers={'Content-Type': 'application/json'},
      method='POST',
   )

   try:
      with urllib_request.urlopen(req, timeout=12) as resp:
         body = json.loads(resp.read().decode('utf-8'))
   except error.HTTPError as exc:
      error_body = exc.read().decode('utf-8')
      return None, Response(
         {'error': 'Classifier rejected request', 'details': error_body},
         status=status.HTTP_502_BAD_GATEWAY,
      )
   except error.URLError as exc:
      return None, Response(
         {'error': 'Classifier unavailable', 'details': str(exc.reason)},
         status=status.HTTP_503_SERVICE_UNAVAILABLE,
      )
   except (ValueError, json.JSONDecodeError):
      return None, Response(
         {'error': 'Invalid classifier response'},
         status=status.HTTP_502_BAD_GATEWAY,
      )

   if 'label' not in body or 'confidence' not in body:
      return None, Response(
         {'error': 'Classifier response missing fields'},
         status=status.HTTP_502_BAD_GATEWAY,
      )

   return body, None


def normalize_device_label(label):
   if not label:
      return None

   normalized = str(label).strip().lower().replace(' ', '_')
   if normalized in Device.DEVICE_TYPES_LIST:
      return normalized
   return None


def get_saved_device_type(outlet):
   try:
      return outlet.device_type.device_type
   except Device.DoesNotExist:
      return None


def is_outlet_decided(outlet):
   latest = outlet.readings.order_by('-recorded_at').first()
   if latest is None:
      return False

   # Consider outlet "decided" when it's actively on or has meaningful load.
   return bool(latest.button_state) or abs_wattage(latest.voltage, latest.amperage) >= 1.0


def get_or_predict_device_type(outlet, source_hz=250, max_attempts=2, window_size=500):
   saved_device_type = get_saved_device_type(outlet)
   if saved_device_type is not None:
      return saved_device_type

   if not is_outlet_decided(outlet):
      return None

   base_queryset = outlet.readings.order_by('-recorded_at')

   for attempt in range(max_attempts):
      start = attempt * window_size
      end = start + window_size
      readings_desc = list(base_queryset[start:end])
      if len(readings_desc) < window_size:
         break

      readings = list(reversed(readings_desc))
      payload = {
         'voltage': [r.voltage for r in readings],
         'current': [r.amperage for r in readings],
         'source_hz': source_hz,
         'target_hz': 250,
      }

      body, error_response = call_classifier(payload)
      if error_response is not None or body is None:
         continue

      device_type = normalize_device_label(body.get('label'))
      if device_type is None:
         continue

      device, _ = Device.objects.update_or_create(
         outlet=outlet,
         defaults={'device_type': device_type},
      )
      return device.device_type

   return None


class ReceiveReadingsView(APIView):
   def post(self, request):
      # print(request.data)
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
      all_anomalies = []

      min_voltage = normalize_voltage(data['min_voltage'])
      max_voltage = normalize_voltage(data['max_voltage'])
      anchor_timestamp_ms = data['readings'][-1]['timestamp_ms']
      for reading in data['readings']:
         voltage = normalize_voltage(reading['voltage'])

         for outlet_index in range(4):
            raw_current = reading[f'current_{outlet_index + 1}']
            button_state = reading[f'button_{outlet_index + 1}']

            try:
               outlet = Outlet.objects.get(esp32=esp32, outlet_index=outlet_index)
               r = PowerReading(
                  outlet=outlet,
                  amperage=normalize_current(raw_current),
                  voltage=voltage,
                  min_voltage=min_voltage,
                  max_voltage=max_voltage,
                  timestamp_ms=reading['timestamp_ms'],
                  button_state=button_state,
               )
               r.save(
                  anchor_timestamp_ms=anchor_timestamp_ms,
                  recorded_at=recorded_at,
               )
               saved_readings += 1

               # Run per-reading anomaly checks immediately after saving
               anomalies = run_per_reading_checks(r)
               for anomaly in anomalies:
                  all_anomalies.append({
                     'outlet': outlet_index,
                     'timestamp': recorded_at.isoformat(),
                     **anomaly
                  })

            except Outlet.DoesNotExist:
               continue

      return Response({
         'message': f'{saved_readings} readings saved',
         'anomalies': all_anomalies,
      }, status=status.HTTP_201_CREATED)


class ClassifyDeviceView(APIView):
   def post(self, request):
      serializer = ClassifierInputSerializer(data=request.data)
      if not serializer.is_valid():
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      data = serializer.validated_data
      payload = {
         'voltage': data['voltage'],
         'current': data['current'],
         'source_hz': data['source_hz'],
         'target_hz': 250,
      }

      body, error_response = call_classifier(payload)
      if error_response is not None:
         return error_response

      return Response(
         {
            'device_guess': body['label'],
            'probability': body['confidence'],
         },
         status=status.HTTP_200_OK,
      )


class ClassifyLatestDeviceView(APIView):
   def post(self, request):
      serializer = ClassifierLatestRequestSerializer(data=request.data)
      if not serializer.is_valid():
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      data = serializer.validated_data

      try:
         outlet = Outlet.objects.get(
            esp32__esp32_id=data['esp32_id'],
            outlet_index=data['outlet_index'],
         )
      except Outlet.DoesNotExist:
         return Response({'error': 'Outlet not found'}, status=status.HTTP_404_NOT_FOUND)

      latest_readings_desc = list(
         outlet.readings.order_by('-recorded_at')[:500]
      )
      if len(latest_readings_desc) < 500:
         return Response(
            {
               'error': f'Need 500 samples, found {len(latest_readings_desc)}',
               'sample_count': len(latest_readings_desc),
            },
            status=status.HTTP_400_BAD_REQUEST,
         )

      latest_readings = list(reversed(latest_readings_desc))
      payload = {
         'voltage': [r.voltage for r in latest_readings],
         'current': [r.amperage for r in latest_readings],
         'source_hz': data['source_hz'],
         'target_hz': 250,
      }

      body, error_response = call_classifier(payload)
      if error_response is not None:
         return error_response

      return Response(
         {
            'esp32_id': data['esp32_id'],
            'outlet_index': data['outlet_index'],
            'sample_count': 500,
            'device_guess': body['label'],
            'probability': body['confidence'],
         },
         status=status.HTTP_200_OK,
      )


class ListESP32View(APIView):
   def get(self, request):
      limit_raw = request.query_params.get('limit', '10')
      try:
         limit = max(1, min(int(limit_raw), 1000))
      except ValueError:
         return Response({'error': 'limit must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

      # Lightweight DB query: distinct IDs only, capped result size.
      devices = list(
         ESP32.objects.values_list('esp32_id', flat=True).distinct()[:limit]
      )
      return Response({'devices': devices, 'returned': len(devices)}, status=status.HTTP_200_OK)

class ESP32DashboardView(APIView):
   def get(self, request, esp32_id):
      predict_missing = request.query_params.get('predict_missing', '').lower() in ('1', 'true', 'yes')

      try:
         esp32 = ESP32.objects.get(esp32_id=esp32_id)
      except ESP32.DoesNotExist:
         return Response(
            {'error': 'ESP32 not found'},
            status=status.HTTP_404_NOT_FOUND
         )

      outlets = Outlet.objects.filter(esp32=esp32).order_by('outlet_index').prefetch_related('readings')
      now = timezone.now()
      all_anomalies = []
      outlet_data = []

      for outlet in outlets:
         readings_15m = outlet.readings.filter(
            projected_timestamp__gte=now - timedelta(minutes=15)
         )

         # Run periodic checks across the last 15 minutes of readings
         anomalies = run_periodic_checks(outlet, readings_15m)
         for anomaly in anomalies:
            all_anomalies.append({
               'outlet': outlet.outlet_index,
               'timestamp': now.isoformat(),
               **anomaly
            })

         readings_desc = list(
            outlet.readings.order_by('-projected_timestamp', '-recorded_at')[:400]
         )
         readings = list(reversed(readings_desc))
         latest = readings_desc[0] if readings_desc else None

         kwh_recorded = 0.0
         if len(readings) > 1:
            first = readings[0]
            last = readings[-1]
            t_start = first.projected_timestamp or first.recorded_at
            t_end = last.projected_timestamp or last.recorded_at
            total_hours = (t_end - t_start).total_seconds() / 3600
            if total_hours > 0:
               avg_wattage = sum(abs_wattage(r.voltage, r.amperage) for r in readings) / len(readings)
               kwh_recorded = round(avg_wattage * total_hours / 1000, 6)

         if predict_missing:
            device_type = get_or_predict_device_type(outlet)
         else:
            device_type = get_saved_device_type(outlet)

         outlet_data.append({
            'outlet_index': outlet.outlet_index,
            'device_type': device_type,
            'button_state': latest.button_state if latest else None,
            'wattage': abs_wattage(latest.voltage, latest.amperage) if latest else None,
            'kwh_recorded': kwh_recorded,
         })

      return Response({
         'esp32_id': esp32_id,
         'timestamp': now.isoformat(),
         'predict_missing': predict_missing,
         'outlets': outlet_data,
         'anomalies': all_anomalies,
      }, status=status.HTTP_200_OK)
   

class ESP32LatestReadingsView(APIView):
   def get(self, request, esp32_id):
      try:
         esp32 = ESP32.objects.get(esp32_id=esp32_id)
      except ESP32.DoesNotExist:
         return Response(
            {'error': 'ESP32 not found'},
            status=status.HTTP_404_NOT_FOUND
         )

      outlets = Outlet.objects.filter(esp32=esp32).order_by('outlet_index')
      result = []

      for outlet in outlets:
         readings_desc = list(
            PowerReading.objects.filter(outlet=outlet).order_by('-projected_timestamp', '-recorded_at')[:400]
         )
         readings = list(reversed(readings_desc))
         latest = readings_desc[0] if readings_desc else None

         kwh_recorded = 0.0
         if len(readings) > 1:
            first = readings[0]
            last = readings[-1]
            t_start = first.projected_timestamp or first.recorded_at
            t_end = last.projected_timestamp or last.recorded_at
            total_hours = (t_end - t_start).total_seconds() / 3600
            if total_hours > 0:
               avg_wattage = sum(abs_wattage(r.voltage, r.amperage) for r in readings) / len(readings)
               kwh_recorded = round(avg_wattage * total_hours / 1000, 6)

         device_type = get_saved_device_type(outlet)

         result.append({
            'outlet_index': outlet.outlet_index,
            'device_type': device_type,
            'button_state': latest.button_state if latest else None,
            'wattage': abs_wattage(latest.voltage, latest.amperage) if latest else None,
            'kwh_recorded': kwh_recorded,
            'readings': [
               {
                  'voltage': r.voltage,
                  'min_voltage': r.min_voltage,
                  'max_voltage': r.max_voltage,
                  'amperage': r.amperage,
                  'wattage': abs_wattage(r.voltage, r.amperage),
                  'button_state': r.button_state,
                  'timestamp_ms': r.timestamp_ms,
                  'projected_timestamp': r.projected_timestamp,
               }
               for r in readings
            ]
         })

      return Response({
         'esp32_id': esp32_id,
         'outlets': result,
      }, status=status.HTTP_200_OK)


class OutletReadingsView(APIView):
   PERIOD_HOURS = {
      'hour': 1,
      'day': 24,
      'week': 24 * 7,
   }

   def get(self, request, esp32_id):
      outlet_index_raw = request.query_params.get('outlet_index')
      period = request.query_params.get('period', 'hour')

      if outlet_index_raw is None:
         return Response({'error': 'outlet_index is required'}, status=status.HTTP_400_BAD_REQUEST)
      try:
         outlet_index = int(outlet_index_raw)
      except ValueError:
         return Response({'error': 'outlet_index must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

      if period not in self.PERIOD_HOURS:
         return Response(
            {'error': f'period must be one of: {list(self.PERIOD_HOURS.keys())}'},
            status=status.HTTP_400_BAD_REQUEST,
         )

      try:
         outlet = Outlet.objects.get(esp32__esp32_id=esp32_id, outlet_index=outlet_index)
      except Outlet.DoesNotExist:
         return Response({'error': 'Outlet not found'}, status=status.HTTP_404_NOT_FOUND)

      since = timezone.now() - timedelta(hours=self.PERIOD_HOURS[period])
      readings = (
         outlet.readings
         .filter(recorded_at__gte=since)
         .order_by('projected_timestamp', 'recorded_at')
      )

      return Response([
         {
            'timestamp': (r.projected_timestamp or r.recorded_at).isoformat(),
            'wattage': abs_wattage(r.voltage, r.amperage),
         }
         for r in readings
      ], status=status.HTTP_200_OK)


class EnergyBreakdownView(APIView):
   PERIOD_HOURS = {
      'day': 24,
      'week': 24 * 7,
      'month': 24 * 30,
   }

   def get(self, request, esp32_id):
      period = request.query_params.get('period', 'day')
      if period not in self.PERIOD_HOURS:
         return Response(
            {'error': f'period must be one of: {list(self.PERIOD_HOURS.keys())}'},
            status=status.HTTP_400_BAD_REQUEST,
         )

      try:
         esp32 = ESP32.objects.get(esp32_id=esp32_id)
      except ESP32.DoesNotExist:
         return Response({'error': 'ESP32 not found'}, status=status.HTTP_404_NOT_FOUND)

      since = timezone.now() - timedelta(hours=self.PERIOD_HOURS[period])
      entries = []

      for outlet in Outlet.objects.filter(esp32=esp32).order_by('outlet_index'):
         readings = list(
            outlet.readings.filter(recorded_at__gte=since).order_by('projected_timestamp', 'recorded_at')
         )
         if len(readings) < 2:
            continue

         first = readings[0]
         last = readings[-1]
         t_start = first.projected_timestamp or first.recorded_at
         t_end = last.projected_timestamp or last.recorded_at
         total_hours = (t_end - t_start).total_seconds() / 3600
         if total_hours <= 0:
            continue

         avg_wattage = sum(abs_wattage(r.voltage, r.amperage) for r in readings) / len(readings)
         kwh = round(avg_wattage * total_hours / 1000, 6)

         device_type = get_saved_device_type(outlet)

         entries.append({'device_type': device_type, 'kwh': kwh})

      totals_by_type = {}
      for entry in entries:
         key = entry['device_type']
         totals_by_type[key] = totals_by_type.get(key, 0.0) + entry['kwh']

      total_kwh = sum(totals_by_type.values())
      response = []
      for device_type, kwh in sorted(totals_by_type.items(), key=lambda item: item[1], reverse=True):
         percentage = round((kwh / total_kwh) * 100, 1) if total_kwh > 0 else 0.0
         response.append({
            'device_type': device_type,
            'kwh': round(kwh, 6),
            'percentage': percentage,
         })

      return Response(response, status=status.HTTP_200_OK)