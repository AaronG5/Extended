from datetime import timedelta
from django.db import models
from django.utils import timezone

class ESP32(models.Model):
   esp32_id = models.CharField(max_length=100, unique=True)
   created_at = models.DateTimeField(auto_now_add=True)

   def __str__(self):
      return f'SP32 {self.esp32_id}'


class Outlet(models.Model):
   OUTLET_CHOICES = [(i, f'Outlet {i}') for i in range(4)]  # 0, 1, 2, 3

   esp32 = models.ForeignKey(ESP32, on_delete=models.CASCADE, related_name='outlets')
   outlet_index = models.IntegerField(choices=OUTLET_CHOICES)  # which of the 4 outlets
   created_at = models.DateTimeField(auto_now_add=True)

   class Meta:
      unique_together = ('esp32', 'outlet_index')  # no duplicate outlet 0 on same ESP32

   def __str__(self):
      return f'{self.esp32} - Outlet {self.outlet_index}'


class Device(models.Model):
   DEVICE_TYPES_LIST = [
      'compact_flourescent_lamp', 'air_conditioner', 'hairdryer', 
      'laptop', 'vacuum', 'fridge', 'washing_machine',
      'incandescent_light_bulb', 'microwave', 'fan', 'heater',
      'coffee_maker', 'water_kettle', 'hair_iron', 'soldering_iron', 
      'blender'
   ]
   DEVICE_TYPES = [(t, t.replace('_', ' ').title()) for t in DEVICE_TYPES_LIST]

   outlet = models.OneToOneField(Outlet, on_delete=models.CASCADE, related_name='device_type')
   device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
   updated_at = models.DateTimeField(auto_now=True)

   def __str__(self):
      return f"{self.outlet} -> {self.device_type}"


class PowerReading(models.Model):
   outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name='readings')
   amperage = models.FloatField()
   voltage = models.FloatField()
   min_voltage = models.FloatField(default=0.0)
   max_voltage = models.FloatField(default=0.0)
   wattage = models.FloatField()
   timestamp_ms = models.BigIntegerField()       # ms from ESP32 boot
   button_state = models.BooleanField(default=False)            # True if button pressed, else False
   
   recorded_at = models.DateTimeField(auto_now_add=True)  # when server received it
   projected_timestamp = models.DateTimeField(null=True, blank=True)  # when it likely occurred

   class Meta:
      ordering = ['projected_timestamp']

   @staticmethod
   def calculate_projected_timestamp(recorded_at, anchor_timestamp_ms, timestamp_ms, rtt_ms=0):
      if recorded_at is None:
         raise ValueError('recorded_at is required to calculate projected_timestamp')

      one_way_delay_ms = rtt_ms / 2
      age_delta_ms = anchor_timestamp_ms - timestamp_ms

      return recorded_at - timedelta(milliseconds=one_way_delay_ms + age_delta_ms)

   def set_projected_timestamp(self, anchor_timestamp_ms, recorded_at=None, rtt_ms=0):
      effective_recorded_at = recorded_at or self.recorded_at or timezone.now()
      self.projected_timestamp = self.calculate_projected_timestamp(
         recorded_at=effective_recorded_at,
         anchor_timestamp_ms=anchor_timestamp_ms,
         timestamp_ms=self.timestamp_ms,
         rtt_ms=rtt_ms,
      )
      return self.projected_timestamp

   def save(self, *args, **kwargs):
      anchor_timestamp_ms = kwargs.pop('anchor_timestamp_ms', None)
      recorded_at = kwargs.pop('recorded_at', None)
      rtt_ms = kwargs.pop('rtt_ms', 0)

      # Keep wattage consistent with the incoming electrical values.
      self.wattage = self.voltage * self.amperage

      if anchor_timestamp_ms is not None:
         self.set_projected_timestamp(
            anchor_timestamp_ms=anchor_timestamp_ms,
            recorded_at=recorded_at,
            rtt_ms=rtt_ms,
         )

      super().save(*args, **kwargs)

   def __str__(self):
      return f"{self.outlet} - {self.wattage}W / {self.voltage}V at {self.timestamp_ms}ms"