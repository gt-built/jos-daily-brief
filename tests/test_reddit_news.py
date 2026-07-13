import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from daily_brief.reddit_news import fetch_reddit_news


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _token_response():
    return Response(json.dumps({"access_token": "test-token"}).encode())


class RedditNewsTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "REDDIT_CLIENT_ID": "client-id",
            "REDDIT_CLIENT_SECRET": "client-secret",
            "DAILY_BRIEF_REDDIT_SUBREDDITS": "AI_Agents",
        },
    )
    def test_builds_dutch_ai_news_from_favorite_subreddits(self) -> None:
        def opener(request, timeout):
            if request.full_url == "https://www.reddit.com/api/v1/access_token":
                self.assertTrue(request.get_header("Authorization").startswith("Basic "))
                return _token_response()
            if "oauth.reddit.com" in request.full_url:
                self.assertIn("r/AI_Agents/top", request.full_url)
                self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
                payload = {
                    "data": {
                        "children": [
                            {
                                "data": {
                                    "title": "New agent framework released",
                                    "score": 512,
                                    "selftext": "Details over het framework",
                                }
                            }
                        ]
                    }
                }
                return Response(json.dumps(payload).encode())
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            posts = {
                "posts": [
                    {
                        "title": "Nieuw agent-framework uitgebracht",
                        "source": "r/AI_Agents",
                        "lines": ["Een", "Twee", "Drie"],
                    }
                ]
            }
            payload = {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(posts),
                            }
                        ]
                    }
                ]
            }
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_reddit_news(opener, Path(directory))

        self.assertEqual(result.items[0].title, "Nieuw agent-framework uitgebracht")
        self.assertEqual(result.items[0].source, "r/AI_Agents")
        self.assertEqual(result.items[0].summary.splitlines(), ["Een", "Twee", "Drie"])

    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "REDDIT_CLIENT_ID": "client-id",
            "REDDIT_CLIENT_SECRET": "client-secret",
            "DAILY_BRIEF_REDDIT_SUBREDDITS": "AI_Agents;down",
        },
    )
    def test_continues_when_one_subreddit_is_unreachable(self) -> None:
        def opener(request, timeout):
            if request.full_url == "https://www.reddit.com/api/v1/access_token":
                return _token_response()
            if "r/down" in request.full_url:
                raise OSError("subreddit unreachable")
            if "oauth.reddit.com" in request.full_url:
                payload = {
                    "data": {
                        "children": [
                            {"data": {"title": "Werkt gewoon", "score": 10}}
                        ]
                    }
                }
                return Response(json.dumps(payload).encode())
            posts = {
                "posts": [
                    {"title": "Werkt gewoon", "source": "r/AI_Agents", "lines": ["Een"]}
                ]
            }
            payload = {
                "output": [
                    {"content": [{"type": "output_text", "text": json.dumps(posts)}]}
                ]
            }
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_reddit_news(opener, Path(directory))

        self.assertEqual(result.items[0].title, "Werkt gewoon")
        self.assertEqual(result.unavailable_sources, ["r/down"])
