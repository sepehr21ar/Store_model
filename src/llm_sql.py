import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_cohere import ChatCohere

from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit


BASE_DIR = Path(__file__).resolve().parent


def db_uri() -> str:
    db_path = Path(
        os.getenv(
            "STORE_DB_PATH",
            str(BASE_DIR / "store.db"),
        )
    )
    return f"sqlite:///{db_path.as_posix()}"


@lru_cache(maxsize=1)
def get_agent():
    load_dotenv()

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY is not configured.")

    db = SQLDatabase.from_uri(db_uri())

    llm = ChatCohere(model=os.getenv("COHERE_MODEL", "command-a-03-2025"), temperature=0)   
     # llm = ChatOpenAI(
    #     model="gpt-4.1-mini",                   
    #     base_url="https://api.gapgpt.app/v1",
    #     api_key=api_key,                         
    #     temperature=0,
     
    #     max_tokens=1024,
    #     top_p=1.0,
    # )

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    system_prompt = f"""
You are a read-only SQL assistant for a SQLite store management database.

Rules:
- Always inspect the available tables first.
- Then inspect the schema of the relevant tables.
- Generate only SQLite SELECT statements.
- Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE or REPLACE.
- Double-check every SQL query before executing it.
- If a query fails, fix it and retry.
- Reply with concise business answers.

Database dialect: {db.dialect}
"""

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent


def _convert_history(history):

    messages = []

    for msg in history:

        role = msg["role"]
        content = msg["content"]

        if role == "system":
            messages.append(SystemMessage(content))

        elif role == "assistant":
            messages.append(AIMessage(content))

        else:
            messages.append(HumanMessage(content))

    return messages


def chat_with_llm(history):
    """
    history:
        list[{"role": ..., "content": ...}]
        OR
        str

    returns:
        updated_history,
        status
    """

    if isinstance(history, str):
        history = [
            {
                "role": "user",
                "content": history,
            }
        ]

    messages = _convert_history(history)

    result = get_agent().invoke(
        {
            "messages": messages,
        }
    )

    returned_messages = result["messages"]

    answer = ""

    for message in reversed(returned_messages):
        if isinstance(message, AIMessage):
            answer = message.content
            break

    if not answer:
        answer = "No answer was returned."

    history.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    return history, "Query completed."

if __name__ == "__main__":
    test_history = [
        {"role": "user", "content": "سلام، تعداد محصولات در انبار چقدر است؟"}
    ]
    
    updated_history, status = chat_with_llm(test_history)
    
    print("وضعیت:", status)
    print("\nپاسخ:")
    print(updated_history[-1]["content"])