import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import sql_database
from langchain_cohere import ChatCohere
from langchain_core.prompts import PromptTemplate
from langgraph.prebuilt import create_react_agent


BASE_DIR = Path(__file__).resolve().parent


def db_uri() -> str:
    db_path = Path(os.getenv("STORE_DB_PATH", str(BASE_DIR / "store.db")))
    return f"sqlite:///{db_path.as_posix()}"


@lru_cache(maxsize=1)
def get_agent_executor():
    load_dotenv()
    if not os.getenv("COHERE_API_KEY"):
        raise RuntimeError("COHERE_API_KEY is not configured. Add it as a Hugging Face Space secret to enable chat.")

    db = sql_database.SQLDatabase.from_uri(db_uri())
    llm = ChatCohere(model=os.getenv("COHERE_MODEL", "command-a-03-2025"), temperature=0)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    prompt_template = PromptTemplate.from_template(
        """
You are a read-only SQL assistant for a SQLite store management database.
- Use sql_db_list_tables and sql_db_schema before writing queries.
- Build valid SQLite SELECT queries and verify them with sql_db_query_checker.
- Do not insert, update, delete, drop, or alter database data.
- Reply with a concise business answer for the user.
"""
    )

    return create_react_agent(
        llm,
        toolkit.get_tools(),
        prompt=prompt_template.format(),
    )


def chat_with_llm(history):
    """
    history: list[{'role': 'user'|'assistant'|'system', 'content': str}] or a single string.
    returns: (updated_history, status_str)
    """
    messages = [{"role": "user", "content": history}] if isinstance(history, str) else list(history)

    result = get_agent_executor().invoke({"messages": messages})
    returned_messages = result.get("messages", [])
    final_answer = None

    if returned_messages:
        last_message = returned_messages[-1]
        final_answer = getattr(last_message, "content", None) or str(last_message)

    if not final_answer:
        final_answer = "No answer was returned by the assistant."

    messages.append({"role": "assistant", "content": final_answer})
    return messages, "Query completed."
