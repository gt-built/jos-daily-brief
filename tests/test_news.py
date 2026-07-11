import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from daily_brief.news import fetch_news


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class NewsTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_builds_dutch_ai_news_from_last_24_hours(self) -> None:
        def opener(request, timeout):
            if "gdeltproject.org" in request.full_url:
                self.assertIn("timespan=24h", request.full_url)
                payload = {
                    "articles": [
                        {
                            "title": "AI agents enter compliance",
                            "url": "https://news.test/article",
                            "domain": "news.test",
                        }
                    ]
                }
                return Response(json.dumps(payload).encode())
            if request.full_url == "https://news.test/article":
                raise OSError("article blocks metadata fetch")
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            topics = {
                "topics": [
                    {
                        "title": "AI-agents controleren regels",
                        "source": "news.test",
                        "lines": ["Een", "Twee", "Drie", "Vier", "Vijf"],
                    }
                ]
            }
            payload = {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(topics),
                            }
                        ]
                    }
                ]
            }
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_news(opener, Path(directory))

        self.assertEqual(result.items[0].title, "AI-agents controleren regels")
        self.assertEqual(
            result.items[0].summary.splitlines(),
            ["Een", "Twee", "Drie", "Vier", "Vijf"],
        )
