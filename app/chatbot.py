"""
Core chatbot logic.

Uses LangChain + Ollama with:
- tiktoken-based context window management
- Tavily web-search tool when forced from GUI or when routed as out-of-domain/recent
- In-memory session chat history
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import tiktoken
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

from .web_search import format_search_results, search_web

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:cloud")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "3000"))
RESERVE_TOKENS = int(os.getenv("RESERVE_TOKENS", "800"))
BOT_DOMAIN = os.getenv(
    "BOT_DOMAIN",
    "software engineering, programming, AI tooling, and developer workflows",
)

try:
    ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:
    ENCODING = None


def count_tokens(text: str) -> int:
    if ENCODING is None:
        return len(text) // 4
    return len(ENCODING.encode(text))


def count_messages_tokens(messages: List[BaseMessage]) -> int:
    return sum(count_tokens(m.content) + 4 for m in messages)


SYSTEM_PROMPT = """You are NexusAI, a friendly and concise AI assistant.

You must:
- Respond clearly using markdown when helpful.
- Cite source links when web results are provided.
- Be explicit when information may be uncertain or time-sensitive.
- Keep answers focused and practical.
"""

ROUTER_PROMPT = """You are a strict router for NexusAI.
NexusAI's primary domain is: {bot_domain}

Return exactly one token:
- WEB: if the query is outside that domain, needs real-time/current information, or clearly asks to browse/search.
- LOCAL: if the query can be answered well from model knowledge in-domain without browsing.

Query:
{question}
"""

WEB_TRIGGER_PATTERNS = [
    r"\bsearch\b",
    r"\bweb\b.*\bfor\b",
    r"\blatest\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\bnews\b",
    r"\b202[4-9]\b",
    r"\bright now\b",
    r"\brecent\b",
    r"\bwhat is happening\b",
    r"\bwho won\b",
    r"\bwhat happened\b",
    r"\blook up\b",
    r"\bfind out\b",
]

llm = ChatOllama(model=MODEL_NAME, temperature=TEMPERATURE)
router_llm = ChatOllama(model=MODEL_NAME, temperature=0.0)

answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ]
)
answer_chain = answer_prompt | llm | StrOutputParser()

router_prompt = ChatPromptTemplate.from_messages([("human", ROUTER_PROMPT)])
router_chain = router_prompt | router_llm | StrOutputParser()


def _is_explicit_web_query(question: str) -> bool:
    q = question.lower()
    return any(re.search(pattern, q) for pattern in WEB_TRIGGER_PATTERNS)


def _is_out_of_domain(question: str) -> bool:
    try:
        decision = router_chain.invoke(
            {
                "question": question,
                "bot_domain": BOT_DOMAIN,
            }
        )
    except Exception:
        return False
    return decision.strip().upper().startswith("WEB")


def _should_search_web(question: str, force_web_search: bool) -> bool:
    if force_web_search:
        return True
    if _is_explicit_web_query(question):
        return True
    return _is_out_of_domain(question)


def _trim_history(history: List[BaseMessage], question: str) -> List[BaseMessage]:
    budget = (
        MAX_TOKENS
        - RESERVE_TOKENS
        - count_tokens(question)
        - count_tokens(SYSTEM_PROMPT)
    )
    trimmed = list(history)
    while trimmed and count_messages_tokens(trimmed) > budget:
        trimmed = trimmed[2:] if len(trimmed) >= 2 else []
    return trimmed


def chat(
    question: str,
    session_history: List[Dict[str, str]],
    force_web_search: bool = False,
) -> Dict[str, Any]:
    history_messages: List[BaseMessage] = []
    for entry in session_history:
        if entry["role"] == "human":
            history_messages.append(HumanMessage(content=entry["content"]))
        else:
            history_messages.append(AIMessage(content=entry["content"]))

    trimmed_history = _trim_history(history_messages, question)
    was_trimmed = len(trimmed_history) < len(history_messages)

    source = "llm"
    web_results = None
    augmented_question = question

    if _should_search_web(question, force_web_search=force_web_search):
        web_results = search_web(question, max_results=5)
        first_title = web_results[0].get("title", "").lower() if web_results else ""
        first_snippet = web_results[0].get("snippet", "") if web_results else ""
        is_search_error = first_title == "search error"

        if is_search_error and force_web_search:
            return {
                "answer": f"Web search failed: {first_snippet}",
                "source": "error",
                "web_results": None,
                "tokens_used": 0,
                "context_pct": 0.0,
                "was_trimmed": was_trimmed,
            }

        if first_snippet and not is_search_error:
            source = "web"
            search_context = format_search_results(web_results)
            augmented_question = (
                f"{question}\n\n"
                f"[WEB SEARCH RESULTS]\n{search_context}\n[/WEB SEARCH RESULTS]"
            )

    try:
        answer = answer_chain.invoke(
            {"question": augmented_question, "chat_history": trimmed_history}
        )
    except Exception as e:
        return {
            "answer": (
                f"Error communicating with Ollama: {e}\n\n"
                f"Make sure Ollama is running and the model `{MODEL_NAME}` is available."
            ),
            "source": "error",
            "web_results": None,
            "tokens_used": 0,
            "context_pct": 0.0,
            "was_trimmed": False,
        }

    tokens_used = (
        count_messages_tokens(trimmed_history)
        + count_tokens(question)
        + count_tokens(answer)
    )
    context_pct = round((tokens_used / MAX_TOKENS) * 100, 1)

    return {
        "answer": answer,
        "source": source,
        "web_results": web_results if source == "web" else None,
        "tokens_used": tokens_used,
        "context_pct": context_pct,
        "was_trimmed": was_trimmed,
    }


def get_model_info() -> Dict[str, Any]:
    return {
        "model": MODEL_NAME,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reserve_tokens": RESERVE_TOKENS,
        "bot_domain": BOT_DOMAIN,
    }
