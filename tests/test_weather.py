import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from daily_brief.weather import TIMEZONE, fetch_weather_with_status


PAYLOAD = {
    "daily": {
        "weather_code": [2],
        "temperature_2m_min": [9.4],
        "temperature_2m_max": [18.7],
        "precipitation_probability_max": [23],
    }
}


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class WeatherTests(unittest.TestCase):
    def test_fetches_and_parses_forecast(self) -> None:
        def opener(url, timeout):
            self.assertIn("forecast_days=1", url)
            self.assertEqual(timeout, 10)
            return Response(json.dumps(PAYLOAD).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_weather_with_status(
                Path(directory),
                opener,
                datetime(2026, 7, 2, 8, tzinfo=TIMEZONE),
            )

        weather = result.weather
        self.assertEqual(weather.summary, "Halfbewolkt")
        self.assertEqual(weather.low_c, 9)
        self.assertEqual(weather.high_c, 19)
        self.assertEqual(weather.rain_chance, 23)

    def test_uses_cache_during_outage(self) -> None:
        def unavailable(url, timeout):
            raise OSError("offline")

        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            start = datetime(2026, 7, 2, 8, tzinfo=TIMEZONE)
            fetch_weather_with_status(
                cache_dir,
                lambda url, timeout: Response(json.dumps(PAYLOAD).encode()),
                start,
            )
            result = fetch_weather_with_status(
                cache_dir,
                unavailable,
                start + timedelta(hours=4),
            )

        self.assertEqual(result.weather.summary, "Halfbewolkt")
        self.assertTrue(result.stale)


if __name__ == "__main__":
    unittest.main()
