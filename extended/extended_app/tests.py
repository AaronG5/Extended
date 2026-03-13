from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import ESP32, Outlet, PowerReading


class ReceiveReadingsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/readings/'
        self.valid_payload = {
            "esp32_id": "TEST123",
            "readings": [
                {
                    "outlet_index": 0,
                    "amperage": 5.0,
                    "voltage": 230.0,
                    "timestamp_ms": 45231,
                    "button_state": False
                }
            ]
        }

    def test_auto_creates_esp32_on_first_reading(self):
        self.client.post(self.url, self.valid_payload, format='json')
        self.assertTrue(ESP32.objects.filter(esp32_id='TEST123').exists())

    def test_auto_creates_4_outlets_on_first_reading(self):
        self.client.post(self.url, self.valid_payload, format='json')
        esp32 = ESP32.objects.get(esp32_id='TEST123')
        self.assertEqual(esp32.outlets.count(), 4)

    def test_does_not_duplicate_esp32_on_second_request(self):
        self.client.post(self.url, self.valid_payload, format='json')
        self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(ESP32.objects.filter(esp32_id='TEST123').count(), 1)

    def test_valid_payload_saves_reading(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], '1 readings saved')

    def test_missing_field_returns_400(self):
        del self.valid_payload['readings'][0]['amperage']
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_outlet_index_is_skipped(self):
        self.valid_payload['readings'][0]['outlet_index'] = 9
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], '0 readings saved')

    def test_wattage_calculated_correctly(self):
        self.client.post(self.url, self.valid_payload, format='json')
        reading = PowerReading.objects.first()
        self.assertAlmostEqual(reading.wattage, 5.0 * 230.0)

    def test_projected_timestamp_is_set(self):
        self.client.post(self.url, self.valid_payload, format='json')
        reading = PowerReading.objects.first()
        self.assertIsNotNone(reading.projected_timestamp)

    def test_multiple_readings_in_one_batch(self):
        self.valid_payload['readings'].append({
            "outlet_index": 1,
            "amperage": 2.0,
            "voltage": 230.0,
            "timestamp_ms": 45250,
            "button_state": False
        })
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.data['message'], '2 readings saved')