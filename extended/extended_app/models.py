from django.db import models

class ESP32(models.Model):
    esp32_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ESP32 {self.esp32_id}"


class Outlet(models.Model):
    OUTLET_CHOICES = [(i, f"Outlet {i}") for i in range(4)]  # 0, 1, 2, 3

    esp32 = models.ForeignKey(ESP32, on_delete=models.CASCADE, related_name='outlets')
    outlet_index = models.IntegerField(choices=OUTLET_CHOICES)  # which of the 4 outlets
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('esp32', 'outlet_index')  # no duplicate outlet 0 on same ESP32

    def __str__(self):
        return f"{self.esp32} - Outlet {self.outlet_index}"


# class Device(models.Model):
#     DEVICE_TYPES = [
#         ('television', 'Television'),
#         ('fridge', 'Fridge'),
#         ('washing_machine', 'Washing Machine'),
#         ('dishwasher', 'Dishwasher'),
#         ('microwave', 'Microwave'),
#         ('computer', 'Computer'),
#         ('other', 'Other'),
#     ]

#     outlet = models.OneToOneField(Outlet, on_delete=models.CASCADE, related_name='device')
#     name = models.CharField(max_length=100)         # e.g. "Samsung TV"
#     device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.name} ({self.device_type})"


class PowerReading(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name='readings')
    amperage = models.FloatField()
    voltage = models.FloatField()
    wattage = models.FloatField()
    timestamp_ms = models.BigIntegerField()       # ms from ESP32 boot
    recorded_at = models.DateTimeField(auto_now_add=True)  # when server received it

    class Meta:
        ordering = ['timestamp_ms']

    def __str__(self):
        return f"{self.outlet} - {self.wattage}W / {self.voltage}V at {self.timestamp_ms}ms"