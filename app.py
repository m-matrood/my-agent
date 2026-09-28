import os
import json
from datetime import datetime
import streamlit as st
from openai import OpenAI
from ddgs import DDGS
from dotenv import load_dotenv

# 1. تحميل المفتاح بأمان من ملف .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key or "ضع_مفتاحك" in api_key:
    st.error("⚠️ يرجى إضافة مفتاح OpenAI API الصحيح داخل ملف .env")
    st.stop()

client = OpenAI(api_key=api_key)

# 2. تعريف أدوات الـ Agent
def calculate_power(base: float, exponent: float) -> str:
    result = base ** exponent
    return json.dumps({"result": result})

def get_current_time() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return json.dumps({"current_time": now})

def search_web(query: str) -> str:
    try:
        results = list(DDGS().text(query, max_results=3))
        if not results:
            return json.dumps({"result": "No search results found."})
        short_results = [
            {"title": item.get("title", ""), "snippet": item.get("body", "")}
            for item in results
        ]
        return json.dumps(short_results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

available_functions = {
    "calculate_power": calculate_power,
    "get_current_time": get_current_time,
    "search_web": search_web
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_power",
            "description": "Calculate power of a base to exponent",
            "parameters": {
                "type": "object",
                "properties": {
                    "base": {"type": "number"},
                    "exponent": {"type": "number"}
                },
                "required": ["base", "exponent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get current date and time",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the live internet for recent real-time information",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    }
]

MODEL_NAME = "gpt-4o-mini"

# 3. إعدادات واجهة Streamlit
st.set_page_config(page_title="AI Agent Chat", page_icon="🤖", layout="centered")
st.title("🤖 My Personal AI Agent")
st.caption("مساعد ذكي متصل بالإنترنت ومزود بأدوات حاسوبية وبحثية")

# 4. تهيئة ذاكرة الجلسة (Session State)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful AI Agent with internet access via tools. Always use search_web output to answer real-time questions."}
    ]

# 5. القائمة الجانبية لمسح المحادثة
with st.sidebar:
    st.header("⚙️ التحكم")
    if st.button("🗑️ مسح المحادثة وبدء جلسة جديدة", use_container_width=True):
        st.session_state.messages = [
            {"role": "system", "content": "You are a helpful AI Agent with internet access via tools. Always use search_web output to answer real-time questions."}
        ]
        st.rerun()

# 6. عرض سجل المحادثات السابق
for msg in st.session_state.messages:
    if msg["role"] != "system" and "content" in msg and msg["content"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# 7. استقبال مدخلات المستخدم ومعالجة الرد
if user_input := st.chat_input("كيف يمكنني مساعدتك اليوم؟"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("جاري التفكير واستخدام الأدوات..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=500
                )

                response_message = response.choices[0].message
                
                if response_message.tool_calls:
                    st.session_state.messages.append(response_message)
                    
                    for tool_call in response_message.tool_calls:
                        fn_name = tool_call.function.name
                        fn_args = json.loads(tool_call.function.arguments)
                        
                        st.info(f"🔧 أداة مستخدمة: `{fn_name}`")
                        
                        if fn_name in available_functions:
                            output = available_functions[fn_name](**fn_args)
                            st.session_state.messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": fn_name,
                                "content": output
                            })

                    final_res = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=st.session_state.messages,
                        max_tokens=500
                    )
                    reply = final_res.choices[0].message.content
                else:
                    reply = response_message.content

                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

            except Exception as e:
                st.error(f"❌ حدث خطأ: {e}")