import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


def answer_question(question: str, dataset_name: str, profile: dict, history: list[dict]) -> dict:
    if not os.getenv("GAP"):
        raise RuntimeError("GAP is not configured on the server.")
    api_key = os.getenv("GAP")

    llm = ChatOpenAI(
        model="gemini-2.5-flash",
        base_url="https://api.gapgpt.app/v1",
        api_key=api_key,
        temperature=0,
    )
    prompt = """You are a careful data analyst. Answer only from the supplied dataset profile and sample. Never invent values. Use grouped_statistics for exact category-by-metric comparisons when available. If the user asks which group is 'best' but does not name a metric, ask a concise clarification such as whether they mean count, sales, score, or another numeric column; do not claim that the profile is insufficient merely because every row is absent. Clearly say when the requested relationship is not present in grouped_statistics. Be concise. Return strict JSON with keys: answer (string), chart (null or object). A chart object has type='bar', title, labels (strings), and series=[{name, values}]. Only create a chart when the supplied statistics contain all exact values used."""
    recent = history[-6:]
    payload = {"dataset": dataset_name, "profile": profile, "recent_conversation": recent, "question": question}
    response = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=json.dumps(payload, default=str))])
    content = response.content if isinstance(response.content, str) else "".join(str(part) for part in response.content)
    try:
        clean = content.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(clean)
        return {"answer": str(result.get("answer", "")), "chart": result.get("chart")}
    except json.JSONDecodeError:
        return {"answer": content, "chart": None}
