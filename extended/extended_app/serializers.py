from rest_framework import serializers
from .models import ESP32, Outlet, PowerReading

class ReadingInputSerializer(serializers.Serializer):
   voltage = serializers.IntegerField(min_value=0, max_value=4096)
   min_voltage = serializers.IntegerField(min_value=0, max_value=4096)
   max_voltage = serializers.IntegerField(min_value=0, max_value=4096)
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

# JSON EXAMPLE:

#    "Content-Type: application/json" 
#    {
#       "id": "ABC123",
#       "max_voltage": 120,
#       "min_voltage": 110,
#       "readings": [
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
#       }]
#     }
