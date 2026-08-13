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
<guid isPermaLink="false">https://tweakers.net/nieuws/1</guid>
</item>
<item>
<title>Fairphone brengt nieuw model uit</title>
<description>Een gewone smartphone-aankondiging over camera en accuduur.</description>
<category>Nieuws / Tablets en telefoons / Smartphones</category>
<guid isPermaLink="false">https://tweakers.net/nieuws/2</guid>
</item>
<item>
<title>Spotify markeert AI-gegenereerde artiesten</title>
<description>Spotify gaat artiesten labelen die AI-gegenereerd zijn.</description>
<category>Nieuws / IT Pro / Internet</category>
<guid isPermaLink="false">https://tweakers.net/nieuws/3</guid>
</item>
</channel></rss>"""


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _openai_response(candidates):
    summaries = {"summaries": [{"summary": "Een lopende samenvatting van vijf zinnen."} for _ in candidates]}
    payload = {
        "output": [{"content": [{"type": "output_text", "text": json.dumps(summaries)}]}]
    }
    return Response(json.dumps(payload).encode())


class TweakersNewsTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_filters_ai_news_keeps_headline_and_flowing_summary(self) -> None:
        def opener(request, timeout):
            if "tweakers.net" in request.full_url:
                return Response(FEED_TEMPLATE.encode())
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            candidates = json.loads(json.loads(request.data)["input"])
            self.assertEqual(len(candidates), 2)
            return _openai_response(candidates)

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_tweakers_news(opener, Path(directory))

        self.assertEqual(len(result.items), 2)
        self.assertEqual(
            result.items[0].title, "Anthropic zet watermerk in AI-gegenereerde teksten"
        )
        self.assertEqual(result.items[0].source, "Tweakers")
        self.assertEqual(result.items[0].summary, "Een lopende samenvatting van vijf zinnen.")
        self.assertNotIn("\n", result.items[0].summary)

    def test_raises_when_no_ai_news_found(self) -> None:
        def opener(request, timeout):
            payload = """<?xml version="1.0"?><rss version="2.0"><channel>
            <item><title>Gewoon nieuws</title><description>Niets bijzonders vandaag.</description>
            <category>Nieuws / Gaming / Games</category>
            <guid isPermaLink="false">https://tweakers.net/nieuws/9</guid></item>
            </channel></rss>"""
            return Response(payload.encode())

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                fetch_tweakers_news(opener, Path(directory))

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_does_not_repeat_previously_shown_articles(self) -> None:
        next_day_feed = FEED_TEMPLATE.replace(
            "</channel></rss>",
            "<item>"
            "<title>Nieuw AI-model verslaat benchmark</title>"
            "<description>Een compleet nieuw AI-model zet een record neer.</description>"
            "<category>Nieuws / IT Pro / Internet</category>"
            "<guid isPermaLink=\"false\">https://tweakers.net/nieuws/4</guid>"
            "</item></channel></rss>",
        )
        state = {"feed": FEED_TEMPLATE}

        def opener(request, timeout):
            if "tweakers.net" in request.full_url:
                return Response(state["feed"].encode())
            candidates = json.loads(json.loads(request.data)["input"])
            return _openai_response(candidates)

        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            first = fetch_tweakers_news(opener, cache_dir, now=None)
            first_titles = {item.title for item in first.items}
            self.assertEqual(
                first_titles,
                {
                    "Anthropic zet watermerk in AI-gegenereerde teksten",
                    "Spotify markeert AI-gegenereerde artiesten",
                },
            )

            # Simulate the next day: the feed has moved on and gained one new
            # AI article, but still lists the two already-shown ones too.
            # Force a fresh (non-cached) fetch, keeping the "seen" file intact.
            (cache_dir / "tweakers-ai-news.json").unlink()
            state["feed"] = next_day_feed

            second = fetch_tweakers_news(opener, cache_dir, now=None)

        self.assertEqual(
            [item.title for item in second.items], ["Nieuw AI-model verslaat benchmark"]
        )
