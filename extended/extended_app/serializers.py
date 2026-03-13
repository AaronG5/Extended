from rest_framework import serializers
from .models import ESP32, Outlet, PowerReading

class PowerReadingInputSerializer(serializers.Serializer):
   outlet_index = serializers.IntegerField(min_value=0, max_value=0)
   amperage = serializers.FloatField()
   voltage = serializers.FloatField()
   # wattage = serializers.FloatField() # Should calculate in views
   timestamp_ms = serializers.IntegerField()
   button_state = serializers.BooleanField()

class ESP32PayloadSerializer(serializers.Serializer):
   esp32_id = serializers.CharField()
   readings = PowerReadingInputSerializer(many=True)