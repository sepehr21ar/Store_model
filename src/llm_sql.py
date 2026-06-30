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

from .init_db import database_url


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
    url = database_url()
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache(maxsize=1)
def get_agent():
    load_dotenv()

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY is not configured.")

    db = SQLDatabase.from_uri(db_uri())

    llm = ChatCohere(
        model=os.getenv("COHERE_MODEL", "command-a-03-2025"),
        cohere_api_key=api_key,
        temperature=0,
    )
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
You are a read-only PostgreSQL analytics assistant for a store management app.
You answer questions by inspecting the live cloud database and, when useful, creating charts.

Database dialect: {db.dialect}

Tables you may encounter:
- products: product_id, product_name, price, availability
- storage: product_id, quantity
- store_sales: product_id, sale_date, quantity
- online_sales: product_id, sale_date, quantity
- action_logs: action_text, created_at

Business logic:
- Total sales means the sum of quantities from both store_sales and online_sales.
- Store sales come from store_sales.quantity.
- Online sales come from online_sales.quantity.
- For best-selling / highest sales / most sold product questions, calculate:
  total_sales = COALESCE(store_sales total, 0) + COALESCE(online_sales total, 0)
- Never say there is no sales data before checking both store_sales and online_sales.
- Always join sales results with products to show product_name.
- For sales ranking, aggregate store_sales and online_sales separately first, then LEFT JOIN them to products.

Example query for best-selling product:

SELECT
    p.product_name,
    COALESCE(ss.store_total, 0) AS store_sales,
    COALESCE(os.online_total, 0) AS online_sales,
    COALESCE(ss.store_total, 0) + COALESCE(os.online_total, 0) AS total_sales
FROM products p
LEFT JOIN (
    SELECT product_id, SUM(quantity) AS store_total
    FROM store_sales
    GROUP BY product_id
) ss ON p.product_id = ss.product_id
LEFT JOIN (
    SELECT product_id, SUM(quantity) AS online_total
    FROM online_sales
    GROUP BY product_id
) os ON p.product_id = os.product_id
ORDER BY total_sales DESC
LIMIT 1;

Safety rules:
- Use only read-only SQL. Only SELECT statements are allowed.
- Never run INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, or REPLACE.
- If the user asks to change data, explain that they should use the app controls instead.
- Always inspect tables and relevant schemas before writing a query unless they are already clear from the current conversation.
- Double-check each SQL query before execution.
- If a query fails, repair it once or twice, then explain the limitation clearly.
- Never invent numbers. Use only database results.

Answer rules:
- Always answer in Persian.
- Be concise and business-focused.
- Mention the main number or insight first.
- Use product names in the answer, not only IDs.
- If there is no matching data, say so directly and suggest a nearby valid query.

Chart rules:
- When the user asks for a chart, graph, visual, report, compare, trend, breakdown, top, ranking, sales, inventory, value, or price analysis, call create_bar_chart after the SQL query.
- For single-product sales questions, create a chart when a breakdown is possible, for example Store sales vs Online sales.
- For multi-product questions, prefer product names as labels.
- Good chart examples:
  - Store vs Online sales by product
  - Inventory by product
  - Total sales by product
  - Inventory value by product
  - Price by product
- Chart labels and values must come directly from SQL results.
- Keep charts small: use the top 8 categories unless the user asks for more.
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

    try:
        result = get_agent().invoke(
            {
                "messages": messages,
            }
        )
    except Exception as exc:
        message = str(exc)
        if "403" in message or "Forbidden" in message:
            raise RuntimeError(
                "AI provider rejected the request. Check COHERE_API_KEY, account access, and model permissions."
            ) from exc
        raise

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
