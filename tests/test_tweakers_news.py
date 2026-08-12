import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from daily_brief.tweakers_news import fetch_tweakers_news

FEED_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
<title>Anthropic zet watermerk in AI-gegenereerde teksten</title>
<description>Anthropic voegt een watermerk toe aan tekst van nieuwe Claude-modellen.</description>
<category>Nieuws / IT Pro / Internet</category>
</item>
<item>
<title>Fairphone brengt nieuw model uit</title>
<description>Een gewone smartphone-aankondiging over camera en accuduur.</description>
<category>Nieuws / Tablets en telefoons / Smartphones</category>
</item>
<item>
<title>Spotify markeert AI-gegenereerde artiesten</title>
<description>Spotify gaat artiesten labelen die AI-gegenereerd zijn.</description>
<category>Nieuws / IT Pro / Internet</category>
</item>
</channel></rss>"""


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TweakersNewsTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_filters_ai_news_and_keeps_original_headline(self) -> None:
        def opener(request, timeout):
            if "tweakers.net" in request.full_url:
                return Response(FEED_TEMPLATE.encode())
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            body = json.loads(request.data)
            candidates = json.loads(body["input"])
            self.assertEqual(len(candidates), 2)
            summaries = {
                "summaries": [
                    {"lines": ["Een", "Twee", "Drie", "Vier", "Vijf"]}
                    for _ in candidates
                ]
            }
            payload = {
                "output": [
                    {"content": [{"type": "output_text", "text": json.dumps(summaries)}]}
                ]
            }
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_tweakers_news(opener, Path(directory))

        self.assertEqual(len(result.items), 2)
        self.assertEqual(
            result.items[0].title, "Anthropic zet watermerk in AI-gegenereerde teksten"
        )
        self.assertEqual(result.items[0].source, "Tweakers")
        self.assertEqual(
            result.items[0].summary.splitlines(), ["Een", "Twee", "Drie", "Vier", "Vijf"]
        )
        self.assertEqual(
            result.items[1].title, "Spotify markeert AI-gegenereerde artiesten"
        )

    def test_raises_when_no_ai_news_found(self) -> None:
        def opener(request, timeout):
            payload = """<?xml version="1.0"?><rss version="2.0"><channel>
            <item><title>Gewoon nieuws</title><description>Niets bijzonders vandaag.</description>
            <category>Nieuws / Gaming / Games</category></item>
            </channel></rss>"""
            return Response(payload.encode())

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                fetch_tweakers_news(opener, Path(directory))
