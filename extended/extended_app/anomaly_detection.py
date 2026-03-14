import statistics
from datetime import timedelta
from django.utils import timezone
from .models import PowerReading

# Thresholds
VOLTAGE_SPIKE_THRESHOLD_V = 20      # max - min within a batch
WATTAGE_SPIKE_MULTIPLIER = 3        # single reading > 3x batch average
VOLTAGE_FLUCTUATION_STDEV_PCT = 10  # stdev > 10% of mean across 15 min
WATTAGE_FLUCTUATION_STDEV_PCT = 10
STANDBY_POWER_THRESHOLD_W = 2       # watts above which button-off is suspicious

EXPECTED_WATTAGE = {
    'compact_flourescent_lamp':  (0.1, 1),
    'air_conditioner':           (250, 1750),
    'hairdryer':                 (500, 1250),
    'laptop':                    (10, 75),
    'vacuum':                    (250, 1250),
    'fridge':                    (25, 200),
    'washing_machine':           (150, 1250),
    'incandescent_light_bulb':   (12.5, 75),
    'microwave':                 (150, 750),
    'fan':                       (5, 50),
    'heater':                    (250, 1500),
    'coffee_maker':              (250, 750),
    'water_kettle':              (750, 1500),
    'hair_iron':                 (50, 117,5),
    'soldering_iron':            (10, 30),
    'blender':                   (150, 500),
}


def check_voltage_spike(reading):
   """Check within a single batch using min/max voltage."""
   spike_range = reading.max_voltage - reading.min_voltage
   if spike_range > VOLTAGE_SPIKE_THRESHOLD_V:
      return {
         'type': 'voltage_spike',
         'message': (
            f'Voltage spike detected: range of {spike_range:.1f}V '
            f'(min {reading.min_voltage:.1f}V, max {reading.max_voltage:.1f}V). '
            f'Possible unstable power supply.'
         )
      }
   return None


def check_wattage_spike(readings_qs):
   """Check within a batch — any single reading > 3x the batch average."""
   wattages = list(readings_qs.values_list('wattage', flat=True))
   if len(wattages) < 2:
      return None

   mean = statistics.mean(wattages)
   spikes = [w for w in wattages if w > mean * WATTAGE_SPIKE_MULTIPLIER]

   if spikes:
      worst = max(spikes)
      return {
         'type': 'wattage_spike',
         'message': (
            f'Wattage spike detected: {worst:.1f}W vs average {mean:.1f}W. '
            f'Possible surge or short circuit.'
         )
      }
   return None


def check_voltage_fluctuation(outlet):
   """Check stdev across last 15 minutes of batches."""
   since = timezone.now() - timedelta(minutes=1)
   voltages = list(
      PowerReading.objects.filter(outlet=outlet, projected_timestamp__gte=since)
      .values_list('voltage', flat=True)
   )
   if len(voltages) < 2:
      return None

   mean = statistics.mean(voltages)
   stdev = statistics.stdev(voltages)
   fluctuation_pct = (stdev / mean) * 100

   if fluctuation_pct > VOLTAGE_FLUCTUATION_STDEV_PCT:
      return {
         'type': 'voltage_fluctuation',
         'message': (
            f'Voltage fluctuating {fluctuation_pct:.1f}% from mean '
            f'({mean:.1f}V) over the last 15 minutes. '
            f'Possible faulty device or unstable supply.'
         )
      }
   return None


def check_wattage_fluctuation(outlet):
   """Check stdev across last 15 minutes of batches."""
   since = timezone.now() - timedelta(minutes=1)
   wattages = list(
      PowerReading.objects.filter(outlet=outlet, projected_timestamp__gte=since)
      .values_list('wattage', flat=True)
   )
   if len(wattages) < 2:
      return None

   mean = statistics.mean(wattages)
   stdev = statistics.stdev(wattages)
   fluctuation_pct = (stdev / mean) * 100

   if fluctuation_pct > WATTAGE_FLUCTUATION_STDEV_PCT:
      return {
         'type': 'wattage_fluctuation',
         'message': (
            f'Wattage fluctuating {fluctuation_pct:.1f}% from mean '
            f'({mean:.1f}W) over the last 15 minutes.'
         )
      }
   return None


def check_abnormal_consumption(outlet):
   """Compare 15 min average wattage against expected range for device type."""
   try:
      device_type = outlet.device_type.device_type
   except Exception:
      return None

   since = timezone.now() - timedelta(minutes=1)
   wattages = list(
      PowerReading.objects.filter(outlet=outlet, projected_timestamp__gte=since)
      .values_list('wattage', flat=True)
   )
   if not wattages:
      return None

   mean = statistics.mean(wattages)
   min_w, max_w = EXPECTED_WATTAGE.get(device_type, (1, 3000))

   if mean < min_w:
      return {
         'type': 'abnormal_consumption',
         'message': (
            f'{device_type.replace("_", " ").title()} drawing only {mean:.1f}W, '
            f'expected at least {min_w}W. Device may be malfunctioning.'
         )
      }
   elif mean > max_w:
      return {
         'type': 'abnormal_consumption',
         'message': (
            f'{device_type.replace("_", " ").title()} drawing {mean:.1f}W, '
            f'expected max {max_w}W. Risk of overheating or damage.'
         )
      }
   return None


def check_button_off_draw(reading):
   """Check if device is drawing significant power while button is off."""
   if not reading.button_state and reading.wattage > STANDBY_POWER_THRESHOLD_W:
      return {
         'type': 'button_off_draw',
         'message': (
            f'Device drawing {reading.wattage:.1f}W while button is off. '
            f'Device may not be fully plugged in — possible hazard.'
         )
      }
   return None


def run_per_reading_checks(reading):
   """Checks that run on every incoming reading."""
   anomalies = []
   for check in [
      check_voltage_spike(reading),
      check_button_off_draw(reading),
   ]:
      if check:
         anomalies.append(check)
   return anomalies


def run_periodic_checks(outlet, readings_qs):
   """Checks that run across a window of readings."""
   anomalies = []
   for check in [
      check_wattage_spike(readings_qs),
      check_voltage_fluctuation(outlet),
      check_wattage_fluctuation(outlet),
      check_abnormal_consumption(outlet),
   ]:
      if check:
         anomalies.append(check)
   return anomalies