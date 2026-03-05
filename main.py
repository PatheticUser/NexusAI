from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser


llm = ChatOllama(
    model="qwen2.5-coder:3b",
    temperature=0.7,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])

chain = prompt | llm | StrOutputParser()

chat_history = []

MAX_TURNS = 5  # 10 exchanges = 20 messages (human + AI)


def chat(question: str) -> str:
    # Check if context window is full BEFORE sending
    current_turns = len(chat_history) // 2

    if current_turns >= MAX_TURNS:
        return (
            "Context window is full! "
            "The AI may not follow the previous thread properly.\n"
            "   Please type 'clear' to start a new chat."
        )

    try:
        response = chain.invoke({
            "question": question,
            "chat_history": chat_history,
        })
    except Exception as e:
        return f"Error: {e}"

    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=response))

    # Warn when getting close (80% full)
    remaining = MAX_TURNS - (current_turns + 1)
    if remaining <= 2:
        response += f"\n\nWarning: Only {remaining} turn(s) left before context is full."

    return response


# -- Interactive Loop --
if __name__ == "__main__":
    print("Chatbot Ready! (type 'quit' to exit, 'clear' to reset memory)\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "clear":
            chat_history.clear()
            print("Memory cleared. Starting fresh!\n")
            continue

        print(f"AI: {chat(user_input)}\n")
