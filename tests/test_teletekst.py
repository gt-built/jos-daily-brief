import io
import json
import tempfile
import unittest
from pathlib import Path

from daily_brief.teletekst import fetch_teletekst_headlines


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TeletekstTests(unittest.TestCase):
    def test_fetches_headlines_from_page_payload(self) -> None:
        def opener(request, timeout):
            self.assertEqual(timeout, 10)
            payload = {
                "content": (
                    '<span class="cyan "> Heetste juni ooit in West-Europa...</span>'
                    '<span class="yellow "> <a class="yellow" href="#130">130</a></span>'
                    '<span class="cyan "> Sloop woonblok na explosie Huizen..</span>'
                    '<span class="yellow "> <a class="yellow" href="#105">105</a></span>'
                )
            }
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_teletekst_headlines(opener, Path(directory))

        self.assertEqual(
            result.headlines,
            [
                "Heetste juni ooit in West-Europa 130",
                "Sloop woonblok na explosie Huizen 105",
            ],
        )
