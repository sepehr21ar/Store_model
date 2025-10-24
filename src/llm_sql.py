
import os
from dotenv import load_dotenv
from langchain_community.utilities import sql_database
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_cohere import ChatCohere
from langchain_core.prompts import PromptTemplate
from langgraph.prebuilt import create_react_agent

load_dotenv()
if not os.environ.get("COHERE_API_KEY"):
    os.environ["COHERE_API_KEY"] = input("Enter API key for Cohere: ")

db = sql_database.SQLDatabase.from_uri("sqlite:///store.db")

llm = ChatCohere(model="command-a-03-2025", temperature=0)
#command-r-plus
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

prompt_template = PromptTemplate.from_template("""
شما یک دستیار SQL برای پایگاه‌داده SQLite فروشگاه هستید.
- از ابزارهای sql_db_list_tables و sql_db_schema برای تایید اسکیمای SQLite استفاده کنید.
- پرس‌وجوهای صحیح SQLite بسازید و قبل از اجرا با sql_db_query_checker اعتبارسنجی کنید.
- خروجی نهایی را به‌صورت پاسخ طبیعی برای کاربر برگردانید.
""")
system_message = prompt_template.format()

agent_executor = create_react_agent(
    llm,
    toolkit.get_tools(),
    prompt=system_message 
)

def _to_tuples(history):
    """Gradio Chatbot(type='messages') => لیست تاپل‌های (role, content)"""
    return [(m["role"], m["content"]) for m in history]


def chat_with_llm(history):
    """
    history: list[{'role': 'user'|'assistant'|'system', 'content': str}]
    returns: (updated_history, status_str)
    """
    try:
        result = agent_executor.invoke({"messages": history})
        msgs = result.get("messages", [])
        final_answer = None
        if msgs:
            last = msgs[-1]
            final_answer = getattr(last, "content", None) or str(last)
        if not final_answer:
            final_answer = "پاسخی از عامل دریافت نشد."
        history.append({"role": "assistant", "content": final_answer})
        return history, "✅ پرس‌وجو انجام شد."
    except Exception as e:
        err = f"❌ خطا: {e}"
        history.append({"role": "assistant", "content": err})
        return history, err

