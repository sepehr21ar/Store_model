
from langchain_openai import ChatOpenAI
import dotenv
import os

dotenv.load_dotenv()
api = os.getenv("GAP")
llm = ChatOpenAI(
        model="gemini-2.5-flash",                   
        base_url="https://api.gapgpt.app/v1",
                   api_key=api,             
        temperature=0,
     
        max_tokens=1024,
        top_p=1.0,
    )
print(llm.invoke("hello speak in effil view "))