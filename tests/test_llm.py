"""Tests for the LLM client."""
import pytest
from app.llm import stream_chat


class FakeAsyncIterator:
    """Mimics aiohttp stream content iterator."""
    def __init__(self, lines):
        self._lines = lines
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._lines):
            raise StopAsyncIteration
        val = self._lines[self._idx].encode("utf-8")
        self._idx += 1
        return val


class FakeResponse:
    """Mimics aiohttp ClientResponse as an async context manager."""
    status = 200

    def __init__(self, lines):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    @property
    def content(self):
        return FakeAsyncIterator(self._lines)


class FakeSession:
    """Mimics aiohttp ClientSession as an async context manager."""
    def __init__(self, lines):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def post(self, url, json):
        return FakeResponse(self._lines)


class TestStreamChat:
    @pytest.mark.asyncio
    async def test_stream_yields_content_chunks(self, monkeypatch):
        lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            'data: {"choices": [{"delta": {"content": " world"}}]}\n',
            "data: [DONE]\n",
        ]

        def make_session():
            return FakeSession(lines)

        monkeypatch.setattr("aiohttp.ClientSession", make_session)

        messages = [{"role": "user", "content": "Hi"}]
        results = [c async for c in stream_chat(messages, base_url="http://test/v1", model="test")]
        assert results == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_skips_empty_lines(self, monkeypatch):
        lines = [
            "\n",
            'data: {"choices": [{"delta": {"content": "X"}}]}\n',
            "",
            "data: [DONE]\n",
        ]

        def make_session():
            return FakeSession(lines)

        monkeypatch.setattr("aiohttp.ClientSession", make_session)

        messages = [{"role": "user", "content": "Hi"}]
        results = [c async for c in stream_chat(messages, base_url="http://test/v1", model="test")]
        assert results == ["X"]

    @pytest.mark.asyncio
    async def test_stream_handles_json_error(self, monkeypatch):
        lines = [
            "data: not-json\n",
            "data: [DONE]\n",
        ]

        def make_session():
            return FakeSession(lines)

        monkeypatch.setattr("aiohttp.ClientSession", make_session)

        messages = [{"role": "user", "content": "Hi"}]
        results = [c async for c in stream_chat(messages, base_url="http://test/v1", model="test")]
        assert results == []
