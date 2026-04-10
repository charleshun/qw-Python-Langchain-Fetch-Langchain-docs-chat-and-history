# Project Progress — LLM Chat App

**Date:** 2026-04-10
**Status:** ✅ LangChain refactored, Markdown rendering + Stop button added

---

## What Was Accomplished

Using skills: my-langchain-fetch, my-pyhon-tdd-coding-agent

### Initial Build (manual implementation)
- Flask + SQLite + manual SSE client + SQLAlchemy models

### LangChain Refactor (complete)
| Step | Task | Status |
|------|------|--------|
| 1 | Add LangChain dependencies | ✅ |
| 2 | Rewrite `app/llm.py` — `ChatOpenAI` for llama.cpp | ✅ |
| 3 | Replace `app/models.py` — lightweight Conversation + `SQLChatMessageHistory` | ✅ |
| 4 | Rewrite `app/routes.py` — `RunnableWithMessageHistory` | ✅ |
| 5 | Update all tests | ✅ |
| 6 | Verify frontend compatibility | ✅ |

### New Features
| Feature | Status |
|---------|--------|
| Markdown rendering for LLM responses | ✅ |
| Stop button during streaming | ✅ |

---

## Project Structure

```
qwpylnc/
├── app/
│   ├── __init__.py          # Flask app factory + SQLAlchemy init
│   ├── models.py            # Conversation + SQLChatMessageHistory wrapper
│   ├── llm.py               # LangChain ChatOpenAI for llama.cpp
│   ├── routes.py            # All routes with RunnableWithMessageHistory + streaming abort
│   ├── static/js/chat.js    # SSE streaming, Markdown rendering, Stop button
│   └── templates/
│       ├── base.html         # Tailwind CDN + marked.js (Markdown parser)
│       └── index.html        # Chat UI with Stop button
├── tests/
│   ├── conftest.py           # Fixtures
│   ├── test_llm.py           # LangChain LLM tests (4)
│   ├── test_models.py        # Conversation + SQLChatMessageHistory tests (6)
│   └── test_routes.py        # Route integration tests (17)
├── config.py                 # LLM_BASE_URL, LLM_MODEL, DB URI
├── requirements.txt
└── run.py
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | `ChatOpenAI` → `http://127.0.0.1:8080/v1`, model: `default-model` |
| Memory | `SQLChatMessageHistory` (SQLite per-session) |
| Chain | `ChatPromptTemplate \| ChatOpenAI` via `RunnableWithMessageHistory` |
| Backend | Flask 3.1 + SQLAlchemy |
| Frontend | Jinja2 + Tailwind CSS (CDN) + vanilla JS + marked.js |
| Streaming | SSE via `chain.stream()`, abortable via `AbortController` |
| Markdown | marked.js (CDN) — renders LLM responses |
| Testing | pytest — 27/27 passing |

---

## Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Main chat page |
| `GET` | `/api/conversations` | List (`?q=search`) |
| `POST` | `/api/conversations` | Create |
| `GET` | `/api/conversations/<id>` | Get with messages |
| `DELETE` | `/api/conversations/<id>` | Delete + clear history |
| `POST` | `/api/conversations/<id>/chat` | Stream response (SSE, abortable) |
| `GET` | `/api/conversations/<id>/export` | Export as plain text |

---

## Key Design Decisions

- `SQLChatMessageHistory` uses `session_id = conversation.id` for per-conversation history
- `ChatOpenAI` connects to local llama.cpp via `base_url="http://127.0.0.1:8080/v1"`
- Streaming uses sync `chain.stream()` (Flask WSGI, not async)
- Markdown rendered client-side via `marked.js` — no server-side rendering
- Stop button uses `AbortController.abort()` to cancel the SSE fetch
- Messages auto-saved by `RunnableWithMessageHistory` — no manual save needed

---

## To Run

1. **Start llama.cpp** on `127.0.0.1:8080`:
   ```bash
   ./llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
   ```

2. **Start Flask app:**
   ```bash
   cd /home/dev/apps/python/202604/qwpylnc
   uv pip install -r requirements.txt
   PYTHONPATH=. uv run python run.py
   ```

3. **Open browser:** `http://localhost:5000`

4. **Run tests:**
   ```bash
   PYTHONPATH=. uv run pytest tests/ -v
   ```

---

## Possible Future Enhancements

- [ ] Code syntax highlighting (highlight.js / Prism)
- [ ] Async Flask (Quart) for native async streaming
- [ ] System prompt customization per conversation
- [ ] Conversation folders/tags
- [ ] Docker containerization
