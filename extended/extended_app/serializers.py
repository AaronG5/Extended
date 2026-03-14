from rest_framework import serializers
from .models import ESP32, Outlet, PowerReading

class ReadingInputSerializer(serializers.Serializer):
   voltage = serializers.IntegerField(min_value=0, max_value=4096)
   timestamp_ms = serializers.IntegerField()
   current_1 = serializers.IntegerField(min_value=0, max_value=4096)
   current_2 = serializers.IntegerField(min_value=0, max_value=4096)
   current_3 = serializers.IntegerField(min_value=0, max_value=4096)
   current_4 = serializers.IntegerField(min_value=0, max_value=4096)
   button_1 = serializers.BooleanField()
   button_2 = serializers.BooleanField()
   button_3 = serializers.BooleanField()
   button_4 = serializers.BooleanField()


class ESP32PayloadSerializer(serializers.Serializer):
   id = serializers.CharField()
   readings = ReadingInputSerializer(many=True)


class OutletDashboardSerializer(serializers.Serializer):
   outlet_index = serializers.IntegerField()
   device_type = serializers.CharField(allow_null=True)
   # Latest reading values
   button_state = serializers.BooleanField(allow_null=True)
   wattage = serializers.FloatField(allow_null=True)
   kwh_recorded = serializers.FloatField()


class ESP32DashboardSerializer(serializers.Serializer):
   esp32_id = serializers.CharField()
   outlets = OutletDashboardSerializer(many=True)


class WattageReadingSerializer(serializers.Serializer):
   timestamp = serializers.DateTimeField()
   wattage = serializers.FloatField()


class EnergyBreakdownSerializer(serializers.Serializer):
   device_type = serializers.CharField(allow_null=True)
   kwh = serializers.FloatField()
   percentage = serializers.FloatField()

# JSON EXAMPLE:
# {
#    "id": "ABC123",
#    "voltage": 5,
#    "timestamp_ms": 12345,
#    "readings": [
#    {
#       "current_1": 10,
#       "current_2": 11,
#       "current_3": 12,
#       "current_4": 13,
#       "button_1": False,
#       "button_2": False,
#       "button_3": True,
#       "button_4": True
#    }]
# }

# curl -X POST http://stavaris.com/api/readings/ \
# -H "Content-Type: application/json" \
# -d '{
#    "id": "ABC123",
#    "readings": [
#       {
#          "voltage": 5.2,
#          "timestamp_ms": 12345,
#          "current_1": 10.1,
#          "current_2": 11.1,
#          "current_3": 12.1,
#          "current_4": 13.1,
#          "button_1": false,
#          "button_2": false,
#          "button_3": true,
#          "button_4": true
#       }
#    ]
# }'