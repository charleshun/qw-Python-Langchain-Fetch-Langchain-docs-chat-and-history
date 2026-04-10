(function () {
    "use strict";

    // ── State ──────────────────────────────────────────────
    let currentConvoId = window.initialConvoId || null;
    let isStreaming = false;

    // ── DOM refs ───────────────────────────────────────────
    const messagesEl = document.getElementById("messages");
    const welcomeEl = document.getElementById("welcome-screen");
    const inputEl = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-btn");
    const newChatBtn = document.getElementById("new-chat-btn");
    const searchInput = document.getElementById("search-input");
    const convoList = document.getElementById("conversation-list");
    const chatTitle = document.getElementById("chat-title");
    const exportBtn = document.getElementById("export-btn");

    // ── Helpers ────────────────────────────────────────────
    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function autoResize(el) {
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 200) + "px";
    }

    function hideWelcome() {
        if (welcomeEl) welcomeEl.style.display = "none";
    }

    function showWelcome() {
        if (welcomeEl) welcomeEl.style.display = "flex";
    }

    // ── Render messages ───────────────────────────────────
    function appendMessage(role, content) {
        hideWelcome();
        const div = document.createElement("div");
        div.className = `flex ${role === "user" ? "justify-end" : "justify-start"}`;
        const bubble = document.createElement("div");
        bubble.className = `max-w-2xl px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            role === "user"
                ? "bg-blue-600 text-white rounded-br-sm"
                : "bg-gray-800 text-gray-100 rounded-bl-sm"
        }`;
        bubble.textContent = content;
        div.appendChild(bubble);
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return bubble;
    }

    // ── Load conversation ─────────────────────────────────
    async function loadConversation(id) {
        currentConvoId = id;
        if (!id) {
            chatTitle.textContent = "New Conversation";
            messagesEl.innerHTML = "";
            if (welcomeEl) {
                messagesEl.appendChild(welcomeEl);
                showWelcome();
            }
            return;
        }

        // Update active state
        document.querySelectorAll(".conversation-item").forEach(el => {
            el.classList.toggle("active", parseInt(el.dataset.id) === id);
            el.classList.toggle("bg-gray-800", parseInt(el.dataset.id) === id);
        });

        const resp = await fetch(`/api/conversations/${id}`);
        if (!resp.ok) return;
        const data = await resp.json();

        chatTitle.textContent = data.title;
        messagesEl.innerHTML = "";
        if (data.messages.length === 0) {
            if (welcomeEl) messagesEl.appendChild(welcomeEl);
            showWelcome();
        } else {
            hideWelcome();
            data.messages.forEach(m => appendMessage(m.role, m.content));
        }
        inputEl.focus();
    }

    // ── Send message (SSE streaming) ──────────────────────
    async function sendMessage() {
        const text = inputEl.value.trim();
        if (!text || isStreaming) return;
        if (!currentConvoId) {
            // Create a new conversation first
            const resp = await fetch("/api/conversations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: text.slice(0, 60) }),
            });
            if (!resp.ok) return;
            const data = await resp.json();
            currentConvoId = data.id;
            addConvoToList(data);
        }

        inputEl.value = "";
        inputEl.style.height = "auto";
        isStreaming = true;
        sendBtn.disabled = true;

        appendMessage("user", text);
        const assistantBubble = appendMessage("assistant", "");

        try {
            const resp = await fetch(`/api/conversations/${currentConvoId}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });
            if (!resp.ok) {
                const err = await resp.json();
                assistantBubble.textContent = `Error: ${err.error || "Unknown error"}`;
                finishStreaming();
                return;
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let fullContent = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.error) {
                            assistantBubble.textContent = `Error: ${data.error}`;
                            finishStreaming();
                            return;
                        }
                        if (data.delta) {
                            fullContent += data.delta;
                            assistantBubble.textContent = fullContent;
                            messagesEl.scrollTop = messagesEl.scrollHeight;
                        }
                        if (data.done) {
                            finishStreaming();
                            // Refresh conversation list to update title
                            refreshConvoList();
                            return;
                        }
                    } catch (_) {}
                }
            }
            finishStreaming();
            refreshConvoList();
        } catch (err) {
            assistantBubble.textContent = `Error: ${err.message}`;
            finishStreaming();
        }
    }

    function finishStreaming() {
        isStreaming = false;
        sendBtn.disabled = false;
        inputEl.focus();
    }

    // ── Conversation list ─────────────────────────────────
    function addConvoToList(data) {
        const existing = convoList.querySelector(`[data-id="${data.id}"]`);
        if (existing) return;

        const div = document.createElement("div");
        div.className = "conversation-item group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer hover:bg-gray-800 transition-colors text-sm";
        div.dataset.id = data.id;
        div.innerHTML = `
            <svg class="w-4 h-4 shrink-0 text-gray-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round"
                      d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"/>
            </svg>
            <span class="truncate flex-1">${escapeHtml(data.title)}</span>
            <button class="delete-btn hidden group-hover:block text-gray-500 hover:text-red-400 transition-colors p-0.5"
                    data-id="${data.id}" title="Delete">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round"
                          d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/>
                </svg>
            </button>
        `;
        convoList.prepend(div);
        div.addEventListener("click", (e) => {
            if (e.target.closest(".delete-btn")) return;
            loadConversation(data.id);
        });
    }

    async function refreshConvoList() {
        const resp = await fetch("/api/conversations");
        if (!resp.ok) return;
        const convos = await resp.json();
        // Rebuild list preserving order
        convoList.innerHTML = "";
        if (convos.length === 0) {
            convoList.innerHTML = '<div class="text-center text-gray-600 text-sm py-8">No conversations yet</div>';
            return;
        }
        convos.forEach(c => addConvoToList(c));
    }

    async function deleteConversation(id) {
        if (!confirm("Delete this conversation?")) return;
        const resp = await fetch(`/api/conversations/${id}`, { method: "DELETE" });
        if (!resp.ok) return;
        if (currentConvoId === id) {
            currentConvoId = null;
            chatTitle.textContent = "New Conversation";
            messagesEl.innerHTML = "";
            if (welcomeEl) {
                messagesEl.appendChild(welcomeEl);
                showWelcome();
            }
        }
        refreshConvoList();
    }

    // ── Event listeners ───────────────────────────────────
    sendBtn.addEventListener("click", sendMessage);
    inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    inputEl.addEventListener("input", () => autoResize(inputEl));

    newChatBtn.addEventListener("click", () => {
        currentConvoId = null;
        chatTitle.textContent = "New Conversation";
        messagesEl.innerHTML = "";
        if (welcomeEl) {
            messagesEl.appendChild(welcomeEl);
            showWelcome();
        }
        document.querySelectorAll(".conversation-item").forEach(el => {
            el.classList.remove("active", "bg-gray-800");
        });
        inputEl.focus();
    });

    // Delegate clicks on conversation list
    convoList.addEventListener("click", (e) => {
        const deleteBtn = e.target.closest(".delete-btn");
        if (deleteBtn) {
            e.stopPropagation();
            deleteConversation(parseInt(deleteBtn.dataset.id));
            return;
        }
        const item = e.target.closest(".conversation-item");
        if (item) loadConversation(parseInt(item.dataset.id));
    });

    // Search
    let searchTimeout;
    searchInput.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            const q = searchInput.value.trim();
            const url = q ? `/api/conversations?q=${encodeURIComponent(q)}` : "/api/conversations";
            const resp = await fetch(url);
            if (!resp.ok) return;
            const convos = await resp.json();
            convoList.innerHTML = "";
            if (convos.length === 0) {
                convoList.innerHTML = '<div class="text-center text-gray-600 text-sm py-8">No results</div>';
                return;
            }
            convos.forEach(c => addConvoToList(c));
        }, 250);
    });

    // Export
    exportBtn.addEventListener("click", async () => {
        if (!currentConvoId) return;
        window.open(`/api/conversations/${currentConvoId}/export`, "_blank");
    });

    // ── Init ───────────────────────────────────────────────
    if (currentConvoId) {
        loadConversation(currentConvoId);
    }
})();
