/* ═══════════════════════════════════════════════════════════════════
   NexusAI — Main JavaScript
   Handles: chat, markdown rendering, web search toggle, UI state
   ═══════════════════════════════════════════════════════════════════ */

'use strict';

// ── marked.js config ──────────────────────────────────────────────
marked.setOptions({
    breaks: true,
    gfm: true,
});

// Custom renderer to add code headers + copy buttons
const renderer = new marked.Renderer();
renderer.code = function (code, language) {
    const lang = language || 'text';
    const highlighted = hljs.getLanguage(lang)
        ? hljs.highlight(code, { language: lang }).value
        : hljs.highlightAuto(code).value;

    return `
    <pre>
      <div class="code-header">
        <span>${lang}</span>
        <button class="copy-btn" onclick="copyCode(this)">Copy</button>
      </div>
      <code class="hljs language-${lang}">${highlighted}</code>
    </pre>`;
};
marked.use({ renderer });

// ── DOM refs ──────────────────────────────────────────────────────
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const messagesList = document.getElementById('messagesList');
const messagesContainer = document.getElementById('messagesContainer');
const typingIndicator = document.getElementById('typingIndicator');
const welcomeState = document.getElementById('welcomeState');
const clearBtn = document.getElementById('clearBtn');
const contextFill = document.getElementById('contextFill');
const contextLabel = document.getElementById('contextLabel');
const tokenCount = document.getElementById('tokenCount');
const msgCountEl = document.getElementById('msgCount');
const toast = document.getElementById('toast');
const webSearchToggle = document.getElementById('webSearchToggle');
const webToggleSwitch = document.getElementById('webToggleSwitch');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');
const sidebarToggleMobile = document.getElementById('sidebarToggleMobile');

// ── State ─────────────────────────────────────────────────────────
let isLoading = false;
let forceWebSearch = false;
let messageCount = 0;

// ── Sidebar toggle ────────────────────────────────────────────────
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});
sidebarToggleMobile.addEventListener('click', () => {
    sidebar.classList.toggle('mobile-open');
    // Add overlay
    const existing = document.querySelector('.mobile-overlay');
    if (existing) { existing.remove(); return; }
    const overlay = document.createElement('div');
    overlay.className = 'mobile-overlay';
    overlay.addEventListener('click', () => {
        sidebar.classList.remove('mobile-open');
        overlay.remove();
    });
    document.body.appendChild(overlay);
});

// ── Web search toggle ─────────────────────────────────────────────
webSearchToggle.addEventListener('click', () => {
    forceWebSearch = !forceWebSearch;
    webToggleSwitch.classList.toggle('on', forceWebSearch);
    webSearchToggle.classList.toggle('active', forceWebSearch);
    showToast(forceWebSearch ? '🌐 Web Search ON — all queries will search the web' : '🤖 Web Search OFF — using local AI');
});

// ── Auto-resize textarea ──────────────────────────────────────────
messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + 'px';
    sendBtn.disabled = messageInput.value.trim() === '' || isLoading;
});

// ── Send on Enter / Shift+Enter for newline ───────────────────────
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!sendBtn.disabled) sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

// ── Suggestion chips ──────────────────────────────────────────────
document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const text = chip.dataset.text;
        messageInput.value = text;
        messageInput.dispatchEvent(new Event('input'));
        sendMessage();
    });
});

// ── Clear conversation ────────────────────────────────────────────
clearBtn.addEventListener('click', async () => {
    try {
        await fetch('/clear', { method: 'POST' });
        messagesList.innerHTML = '';
        messageCount = 0;
        updateStats(0, 0, 0);
        welcomeState.classList.remove('hidden');
        showToast('✨ Conversation cleared');
    } catch (e) {
        showToast('⚠️ Failed to clear conversation');
    }
});

// ── Main send message function ────────────────────────────────────
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isLoading) return;

    // Show user message
    appendMessage('user', text);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Hide welcome state
    welcomeState.classList.add('hidden');

    // Show typing
    setLoading(true);

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                force_web_search: forceWebSearch,
            }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }

        const data = await res.json();
        appendMessage('assistant', data.answer, {
            source: data.source,
            webResults: data.web_results,
            wasTrimmed: data.was_trimmed,
        });

        updateStats(data.tokens_used, data.context_pct, data.message_count);

    } catch (e) {
        appendMessage('assistant', `⚠️ **Error:** ${e.message}\n\nMake sure Ollama is running locally.`, {
            source: 'error',
        });
    } finally {
        setLoading(false);
        sendBtn.disabled = messageInput.value.trim() === '';
    }
}

// ── Append a message to the DOM ───────────────────────────────────
function appendMessage(role, content, meta = {}) {
    messageCount = (meta.message_count !== undefined) ? meta.message_count : messageCount;
    msgCountEl.textContent = messageCount;

    const div = document.createElement('div');
    div.className = `message ${role}`;

    const avatarLetter = role === 'user' ? 'U' : 'N';
    const avatar = `<div class="message-avatar">${avatarLetter}</div>`;

    let bodyInner = '';

    // Source badge (assistant only)
    if (role === 'assistant') {
        const src = meta.source || 'llm';
        const badgeClass = src === 'web' ? 'badge-web' : src === 'error' ? 'badge-error' : 'badge-llm';
        const badgeIcon = src === 'web' ? '🌐' : src === 'error' ? '⚠️' : '🤖';
        const badgeLabel = src === 'web' ? 'Web Search' : src === 'error' ? 'Error' : 'NexusAI';
        bodyInner += `<div class="source-badge ${badgeClass}">${badgeIcon} ${badgeLabel}</div>`;
    }

    // Trimmed notice
    if (meta.wasTrimmed) {
        bodyInner += `<div class="trimmed-notice">📌 Older messages trimmed to fit context window</div>`;
    }

    // Message bubble
    const html = role === 'user'
        ? escapeHtml(content).replace(/\n/g, '<br>')
        : marked.parse(content);

    bodyInner += `<div class="message-bubble"><div class="md-content">${html}</div></div>`;

    // Web results
    if (meta.webResults && meta.webResults.length > 0) {
        let results = `<div class="web-results">
      <div class="web-results-title">🔗 Sources</div>`;
        meta.webResults.forEach(r => {
            if (!r.url && !r.title) return;
            results += `<a class="web-result-item" href="${escapeHtml(r.url)}" target="_blank" rel="noopener">
        <div class="web-result-title">${escapeHtml(r.title)}</div>
        <div class="web-result-snippet">${escapeHtml(r.snippet.substring(0, 120))}…</div>
        <div class="web-result-url">${escapeHtml(r.url)}</div>
      </a>`;
        });
        results += `</div>`;
        bodyInner += results;
    }

    // Timestamp
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    bodyInner += `<div class="message-meta">${time}</div>`;

    div.innerHTML = `
    ${avatar}
    <div class="message-body">${bodyInner}</div>
  `;

    messagesList.appendChild(div);
    scrollToBottom();
}

// ── Context & stats update ────────────────────────────────────────
function updateStats(tokensUsed, contextPct, msgCnt) {
    messageCount = msgCnt || messageCount;
    msgCountEl.textContent = messageCount;

    const pct = Math.min(contextPct || 0, 100);
    contextFill.style.width = pct + '%';
    contextLabel.textContent = pct + '%';
    tokenCount.textContent = `${(tokensUsed || 0).toLocaleString()} tokens used`;

    // Color the bar based on usage
    contextFill.className = 'context-fill';
    if (pct >= 90) contextFill.classList.add('full');
    else if (pct >= 70) contextFill.classList.add('warn');
}

// ── Typing / loading state ────────────────────────────────────────
function setLoading(loading) {
    isLoading = loading;
    typingIndicator.classList.toggle('hidden', !loading);
    if (loading) scrollToBottom();

    // Swap send button icon
    sendBtn.classList.toggle('loading', loading);
    if (loading) {
        sendBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>
    </svg>`;
    } else {
        sendBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>`;
    }
}

// ── Scroll to bottom ──────────────────────────────────────────────
function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
}

// ── Copy code button ──────────────────────────────────────────────
function copyCode(btn) {
    const code = btn.closest('pre').querySelector('code').innerText;
    navigator.clipboard.writeText(code).then(() => {
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
        }, 2000);
    });
}

// ── Toast notification ────────────────────────────────────────────
let toastTimer;
function showToast(msg, duration = 2800) {
    clearTimeout(toastTimer);
    toast.textContent = msg;
    toast.classList.add('show');
    toastTimer = setTimeout(() => toast.classList.remove('show'), duration);
}

// ── Escape HTML ───────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ── On load — focus input ─────────────────────────────────────────
window.addEventListener('load', () => {
    messageInput.focus();
});
