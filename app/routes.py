"""
Flask routes — all API endpoints for the chatbot.
"""

from __future__ import annotations
from flask import Blueprint, render_template, request, jsonify, session

from .chatbot import chat, get_model_info

bp = Blueprint("main", __name__)

SESSION_HISTORY_KEY = "chat_history"


@bp.route("/")
def index():
    return render_template("index.html", model_info=get_model_info())


@bp.route("/chat", methods=["POST"])
def chat_endpoint():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    force_web_search = bool(data.get("force_web_search", False))

    if not question:
        return jsonify({"error": "Empty message"}), 400

    # Get or init session history
    history = session.get(SESSION_HISTORY_KEY, [])

    result = chat(question, history, force_web_search=force_web_search)

    # Append to session history (store raw strings, not message objects)
    history.append({"role": "human", "content": question})
    history.append({"role": "ai", "content": result["answer"]})
    session[SESSION_HISTORY_KEY] = history

    return jsonify(
        {
            "answer": result["answer"],
            "source": result["source"],
            "web_results": result.get("web_results"),
            "tokens_used": result.get("tokens_used", 0),
            "context_pct": result.get("context_pct", 0.0),
            "was_trimmed": result.get("was_trimmed", False),
            "message_count": len(history) // 2,
        }
    )


@bp.route("/clear", methods=["POST"])
def clear_history():
    session.pop(SESSION_HISTORY_KEY, None)
    return jsonify({"status": "ok", "message": "Conversation cleared."})


@bp.route("/status", methods=["GET"])
def status():
    history = session.get(SESSION_HISTORY_KEY, [])
    model_info = get_model_info()
    return jsonify(
        {
            "model": model_info["model"],
            "temperature": model_info["temperature"],
            "max_tokens": model_info["max_tokens"],
            "message_count": len(history) // 2,
            "status": "online",
        }
    )
