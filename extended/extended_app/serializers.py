from rest_framework import serializers
from .models import ESP32, Outlet, PowerReading

class ReadingInputSerializer(serializers.Serializer):
   current_1 = serializers.FloatField()
   current_2 = serializers.FloatField()
   current_3 = serializers.FloatField()
   current_4 = serializers.FloatField()
   button_1 = serializers.BooleanField()
   button_2 = serializers.BooleanField()
   button_3 = serializers.BooleanField()
   button_4 = serializers.BooleanField()


class ESP32PayloadSerializer(serializers.Serializer):
   id = serializers.CharField()
   voltage = serializers.FloatField()
   timestamp_ms = serializers.IntegerField()
   readings = ReadingInputSerializer(many=True)

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