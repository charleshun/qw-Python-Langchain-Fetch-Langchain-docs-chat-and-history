import json
from flask import (
    Blueprint, render_template, request, jsonify, Response,
    current_app, stream_with_context
)
from app import db
from app.models import Conversation, Message
from app.llm import stream_chat

bp = Blueprint("main", __name__)


def _run_async(gen):
    """Run an async generator synchronously (for Flask streaming)."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        async def collect():
            items = []
            async for item in gen:
                items.append(item)
            return items
        return loop.run_until_complete(collect())
    finally:
        loop.close()


@bp.route("/")
def index():
    """Render the main chat page."""
    conversations = Conversation.query.order_by(Conversation.updated_at.desc()).all()
    return render_template("index.html", conversations=conversations)


@bp.route("/api/conversations", methods=["GET"])
def list_conversations():
    """List all conversations, optionally filtered by search query."""
    query = request.args.get("q", "").strip()
    convos = Conversation.query.order_by(Conversation.updated_at.desc()).all()
    if query:
        q_lower = query.lower()
        convos = [
            c for c in convos
            if q_lower in c.title.lower()
            or any(q_lower in m.content.lower() for m in c.messages)
        ]
    return jsonify([c.to_dict() for c in convos])


@bp.route("/api/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "New Conversation")
    convo = Conversation(title=title)
    db.session.add(convo)
    db.session.commit()
    return jsonify(convo.to_dict()), 201


@bp.route("/api/conversations/<int:convo_id>", methods=["GET"])
def get_conversation(convo_id):
    """Get a conversation with its messages."""
    convo = db.session.get(Conversation, convo_id)
    if not convo:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        **convo.to_dict(),
        "messages": [m.to_dict() for m in convo.messages],
    })


@bp.route("/api/conversations/<int:convo_id>", methods=["DELETE"])
def delete_conversation(convo_id):
    """Delete a conversation and its messages."""
    convo = db.session.get(Conversation, convo_id)
    if not convo:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(convo)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/api/conversations/<int:convo_id>/chat", methods=["POST"])
def chat(convo_id):
    """Send a message and stream the LLM response (SSE)."""
    convo = db.session.get(Conversation, convo_id)
    if not convo:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    user_content = data.get("message", "").strip()
    if not user_content:
        return jsonify({"error": "Empty message"}), 400

    # Save user message
    user_msg = Message(conversation_id=convo_id, role="user", content=user_content)
    db.session.add(user_msg)

    # Update conversation title if it's the first message
    if convo.title == "New Conversation":
        convo.title = user_content[:60] + ("..." if len(user_content) > 60 else "")

    db.session.commit()

    # Build message history for the LLM
    history = [{"role": m.role, "content": m.content} for m in convo.messages]
    history.append({"role": "user", "content": user_content})

    def generate():
        full_response = []
        try:
            for chunk in _run_async(stream_chat(history)):
                full_response.append(chunk)
                # SSE format
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
        except Exception as e:
            error_msg = str(e)
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
            return

        # Save assistant response
        assistant_content = "".join(full_response)
        assistant_msg = Message(
            conversation_id=convo_id, role="assistant", content=assistant_content
        )
        db.session.add(assistant_msg)
        db.session.commit()

        # Signal done
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@bp.route("/api/conversations/<int:convo_id>/export", methods=["GET"])
def export_conversation(convo_id):
    """Export a conversation as plain text."""
    convo = db.session.get(Conversation, convo_id)
    if not convo:
        return jsonify({"error": "Not found"}), 404

    lines = [f"# {convo.title}\n"]
    for m in convo.messages:
        role_label = m.role.capitalize()
        lines.append(f"\n## {role_label}\n{m.content}")

    text = "\n".join(lines)
    return Response(text, mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename=chat_{convo_id}.txt"})
