from __future__ import annotations

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from addons.research import llm  # noqa: E402


class _DeepSeek(BaseHTTPRequestHandler):
    def _send(self, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path.endswith("/search"):
            return self._send({"results": [{"title": "test result", "url": "https://www.gov.cn/a", "content": "test", "authority": 4}]})
        return self._send({"choices": [{"message": {"content": "test [S1] https://www.gov.cn/a"}}]})

    def log_message(self, *_args) -> None:
        return


class ResearchLlmTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _DeepSeek)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.old = (llm.SEARCH_URL, llm.CHAT_URL)
        llm.SEARCH_URL = f"http://127.0.0.1:{self.server.server_port}/search"
        llm.CHAT_URL = f"http://127.0.0.1:{self.server.server_port}/chat"

    def tearDown(self) -> None:
        self.server.shutdown()
        llm.SEARCH_URL, llm.CHAT_URL = self.old

    def test_search_and_answer_and_key(self) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "test-key"
        try:
            self.assertEqual(llm.deepseek_key(), "test-key")
            sources = llm.search("query", "test-key", limit=3)
            self.assertEqual(sources[0]["url"], "https://www.gov.cn/a")
            self.assertEqual(sources[0]["grade"], "official")
            answer = llm.answer("query", [{"id": "S1", **sources[0]}], "test-key")
            self.assertIn("[S1]", answer)
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)


if __name__ == "__main__":
    unittest.main()
