"""Tests for Flask routes."""
import json
from unittest.mock import patch, AsyncMock
from app import db
from app.models import Conversation, Message


class TestIndexRoute:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Start a conversation" in resp.data


class TestConversationAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        assert resp.json == []

    def test_list_conversations(self, client):
        c = Conversation(title="Test")
        db.session.add(c)
        db.session.commit()
        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        assert len(resp.json) == 1
        assert resp.json[0]["title"] == "Test"

    def test_create_conversation(self, client):
        resp = client.post("/api/conversations", json={"title": "My Chat"})
        assert resp.status_code == 201
        assert resp.json["title"] == "My Chat"

    def test_create_conversation_default_title(self, client):
        resp = client.post("/api/conversations", json={})
        assert resp.status_code == 201
        assert resp.json["title"] == "New Conversation"

    def test_get_conversation(self, client):
        c = Conversation(title="Test")
        db.session.add(c)
        db.session.commit()
        db.session.add(Message(conversation_id=c.id, role="user", content="Hello"))
        db.session.commit()
        resp = client.get(f"/api/conversations/{c.id}")
        assert resp.status_code == 200
        assert resp.json["title"] == "Test"
        assert len(resp.json["messages"]) == 1

    def test_get_conversation_not_found(self, client):
        resp = client.get("/api/conversations/999")
        assert resp.status_code == 404

    def test_delete_conversation(self, client):
        c = Conversation(title="Test")
        db.session.add(c)
        db.session.commit()
        resp = client.delete(f"/api/conversations/{c.id}")
        assert resp.status_code == 200
        assert db.session.get(Conversation, c.id) is None

    def test_delete_conversation_not_found(self, client):
        resp = client.delete("/api/conversations/999")
        assert resp.status_code == 404

    def test_search_conversations(self, client):
        c = Conversation(title="Python Programming")
        db.session.add(c)
        db.session.commit()
        resp = client.get("/api/conversations?q=python")
        assert len(resp.json) == 1
        resp = client.get("/api/conversations?q=xyznotfound")
        assert len(resp.json) == 0


class TestChatAPI:
    def test_chat_empty_message(self, client):
        c = Conversation(title="Test")
        db.session.add(c)
        db.session.commit()
        resp = client.post(f"/api/conversations/{c.id}/chat", json={"message": ""})
        assert resp.status_code == 400

    def test_chat_not_found(self, client):
        resp = client.post("/api/conversations/999/chat", json={"message": "hi"})
        assert resp.status_code == 404

    def test_chat_streams_response(self, client):
        c = Conversation(title="Test")
        db.session.add(c)
        db.session.commit()

        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield " there!"

        with patch("app.routes.stream_chat", side_effect=mock_stream):
            resp = client.post(f"/api/conversations/{c.id}/chat", json={"message": "Hi"})
            assert resp.status_code == 200
            data = resp.data.decode()
            assert "Hello" in data
            assert "done" in data

        # Verify messages saved
        c = db.session.get(Conversation, c.id)
        assert len(c.messages) == 2
        assert c.messages[0].role == "user"
        assert c.messages[1].role == "assistant"
        assert c.messages[1].content == "Hello there!"

    def test_chat_updates_title(self, client):
        c = Conversation(title="New Conversation")
        db.session.add(c)
        db.session.commit()

        async def mock_stream(*args, **kwargs):
            yield "Hi"
            yield "!"

        with patch("app.routes.stream_chat", side_effect=mock_stream):
            client.post(f"/api/conversations/{c.id}/chat", json={"message": "Hello world"})

        c = db.session.get(Conversation, c.id)
        assert c.title != "New Conversation"
        assert "Hello world" in c.title

    def test_chat_handles_stream_error(self, client):
        c = Conversation(title="Test")
        db.session.add(c)
        db.session.commit()

        async def mock_stream_error(*args, **kwargs):
            raise ConnectionError("LLM unavailable")
            yield  # pragma: no cover

        with patch("app.routes.stream_chat", side_effect=mock_stream_error):
            resp = client.post(f"/api/conversations/{c.id}/chat", json={"message": "Hi"})
            assert resp.status_code == 200
            data = resp.data.decode()
            assert "error" in data


class TestExportAPI:
    def test_export_conversation(self, client):
        c = Conversation(title="My Chat")
        db.session.add(c)
        db.session.commit()
        db.session.add(Message(conversation_id=c.id, role="user", content="Hello"))
        db.session.add(Message(conversation_id=c.id, role="assistant", content="Hi"))
        db.session.commit()
        resp = client.get(f"/api/conversations/{c.id}/export")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "My Chat" in text
        assert "Hello" in text
        assert "Hi" in text

    def test_export_not_found(self, client):
        resp = client.get("/api/conversations/999/export")
        assert resp.status_code == 404
