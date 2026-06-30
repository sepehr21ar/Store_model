import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langchain_cohere import ChatCohere

from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit


BASE_DIR = Path(__file__).resolve().parent


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    return float(value)


def _normalize_chart(visual: dict) -> dict:
    labels = [str(label) for label in visual.get("labels", [])]
    normalized_series = []

    for item in visual.get("series", []):
        values = [_number(value) for value in item.get("values", [])]
        if len(values) != len(labels):
            raise ValueError("Each chart series must have one value for every label.")
        normalized_series.append(
            {
                "name": str(item.get("name", "Value")),
                "values": values,
            }
        )

    if not labels:
        raise ValueError("A chart must include at least one label.")
    if not normalized_series:
        raise ValueError("A chart must include at least one series.")

    return {
        "type": "bar",
        "title": str(visual.get("title", "Chart")),
        "unit": str(visual.get("unit", "units")),
        "labels": labels,
        "series": normalized_series,
    }


@tool
def create_bar_chart(title: str, labels: list[str], series: list[dict], unit: str = "units") -> str:
    """Create a bar chart from SQL result data when the answer compares numeric values.

    Use this only after querying the database. Labels should be product names, dates, or
    categories. Series items must be dictionaries like {"name": "Store", "values": [1, 2]}.
    The returned JSON is shown as a chart in the app.
    """

    chart = _normalize_chart(
        {
            "title": title,
            "unit": unit,
            "labels": labels,
            "series": series,
        }
    )
    return json.dumps(chart)


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
    tools = [*toolkit.get_tools(), create_bar_chart]

    system_prompt = f"""
You are a read-only SQL and visualization assistant for a SQLite store management database.

Rules:
- Always inspect the available tables first.
- Then inspect the schema of the relevant tables.
- Generate only SQLite SELECT statements.
- Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE or REPLACE.
- Double-check every SQL query before executing it.
- If a query fails, fix it and retry.
- Reply with concise business answers.
- If the answer compares numeric values, rankings, sales, inventory, prices, or totals,
  use the create_bar_chart tool after the SQL query to generate a chart.
- Build chart labels and values only from SQL results. Never invent chart data.
- Good chart series examples: Store vs Online sales, Inventory by product,
  Total sales by product, Inventory value by product.

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


def _extract_visuals(returned_messages) -> list[dict]:
    visuals = []

    for message in returned_messages:
        if getattr(message, "name", None) != "create_bar_chart":
            continue

        try:
            content = message.content
            if isinstance(content, list):
                content = "".join(str(part) for part in content)
            visuals.append(_normalize_chart(json.loads(content)))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

    return visuals


def chat_with_llm(history):
    """
    history:
        list[{"role": ..., "content": ...}]
        OR
        str

    returns:
        updated_history,
        status,
        visuals
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
    visuals = _extract_visuals(returned_messages)

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
            "visuals": visuals,
        }
    )

    status = "Query completed with chart." if visuals else "Query completed."
    return history, status, visuals

if __name__ == "__main__":
    test_history = [
        {"role": "user", "content": "سلام، تعداد محصولات در انبار چقدر است؟"}
    ]
    
    updated_history, status, visuals = chat_with_llm(test_history)
    
    print("وضعیت:", status)
    print("\nپاسخ:")
    print(updated_history[-1]["content"])
    print("\nVisuals:")
    print(visuals)
