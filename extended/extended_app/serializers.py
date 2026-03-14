from rest_framework import serializers
from .models import ESP32, Outlet, PowerReading

class PowerReadingInputSerializer(serializers.Serializer):
   outlet_index = serializers.IntegerField()
   amperage = serializers.FloatField()
   voltage = serializers.FloatField()
   timestamp_ms = serializers.IntegerField()
   button_state = serializers.BooleanField()

class ESP32PayloadSerializer(serializers.Serializer):
   esp32_id = serializers.CharField()
   readings = PowerReadingInputSerializer(many=True)