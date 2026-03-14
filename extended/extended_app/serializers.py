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
   min_voltage = serializers.IntegerField(min_value=0, max_value=4096)
   max_voltage = serializers.IntegerField(min_value=0, max_value=4096)
   readings = ReadingInputSerializer(many=True)


class ClassifierInputSerializer(serializers.Serializer):
   voltage = serializers.ListField(
      child=serializers.FloatField(),
      min_length=500,
      max_length=500,
   )
   current = serializers.ListField(
      child=serializers.FloatField(),
      min_length=500,
      max_length=500,
   )
   source_hz = serializers.IntegerField(required=False, default=250, min_value=1)


class ClassifierLatestRequestSerializer(serializers.Serializer):
   esp32_id = serializers.CharField()
   outlet_index = serializers.IntegerField(min_value=0, max_value=3)
   source_hz = serializers.IntegerField(required=False, default=250, min_value=1)

# JSON EXAMPLE:
   # "Content-Type: application/json" 
   # {
# curl -X POST http://stavaris.com/api/readings/ \
# -H "Content-Type: application/json" \
# -d '{
#       "id": "ABC123",
#       "max_voltage": 120,
#       "min_voltage": 110,
#       "readings": [
#       {
#          "voltage": 5,
#          "timestamp_ms": 12345,
#          "current_1": 10,
#          "current_2": 11,
#          "current_3": 12,
#          "current_4": 13,
#          "button_1": false,
#          "button_2": false,
#          "button_3": true,
#          "button_4": true
#       }
#    ]
# }'

# ai classifier input example:
# curl -X POST http://stavaris.com/api/classify/ \
# -H "Content-Type: application/json" \
# -d '{
#    "voltage": [0.1, 0.2, ..., 0.5],  # 500 values
#    "current": [0.01, 0.02, ..., 0.05],  # 500 values
#    "source_hz": 250
# }'
