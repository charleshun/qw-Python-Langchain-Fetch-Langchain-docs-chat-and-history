"""Tests for database models."""
from app import db
from app.models import Conversation, Message


class TestConversation:
    def test_create_conversation(self, session):
        c = Conversation(title="Test Chat")
        session.add(c)
        session.commit()
        assert c.id is not None
        assert c.title == "Test Chat"
        assert c.messages == []

    def test_default_title(self, session):
        c = Conversation()
        session.add(c)
        session.commit()
        assert c.title == "New Conversation"

    def test_to_dict(self, session):
        c = Conversation(title="Test")
        session.add(c)
        session.commit()
        d = c.to_dict()
        assert d["id"] == c.id
        assert d["title"] == "Test"
        assert "created_at" in d
        assert "updated_at" in d


class TestMessage:
    def test_create_message(self, session):
        c = Conversation(title="Test")
        session.add(c)
        session.flush()
        m = Message(conversation_id=c.id, role="user", content="Hello")
        session.add(m)
        session.commit()
        assert m.id is not None
        assert m.role == "user"
        assert m.content == "Hello"
        assert m.conversation_id == c.id

    def test_to_dict(self, session):
        c = Conversation(title="Test")
        session.add(c)
        session.flush()
        m = Message(conversation_id=c.id, role="assistant", content="Hi there")
        session.add(m)
        session.commit()
        d = m.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "Hi there"
        assert d["conversation_id"] == c.id

    def test_cascade_delete(self, session):
        c = Conversation(title="Test")
        session.add(c)
        session.flush()
        session.add(Message(conversation_id=c.id, role="user", content="Hello"))
        session.commit()
        session.delete(c)
        session.commit()
        assert Message.query.count() == 0

    def test_message_ordering(self, session):
        c = Conversation(title="Test")
        session.add(c)
        session.flush()
        session.add(Message(conversation_id=c.id, role="user", content="First"))
        session.add(Message(conversation_id=c.id, role="assistant", content="Second"))
        session.commit()
        c = session.get(Conversation, c.id)
        roles = [m.role for m in c.messages]
        assert roles == ["user", "assistant"]
