import os
import json
import base64
from datetime import datetime
import streamlit as st
from openai import OpenAI
from ddgs import DDGS
from dotenv import load_dotenv
from PIL import Image

# ---------------------------------------------------------
# 1. Page Configuration & Dynamic Responsive Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Agent Workspace",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Responsive CSS using Streamlit's native theme variables
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Container - Adapts to Light/Dark Mode */
    .header-container {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 24px;
    }
    .header-title {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-subtitle {
        font-size: 0.95rem;
        opacity: 0.8;
        margin-top: 6px;
    }

    /* Badges Container */
    .badge-container {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 8px;
    }
    .badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .badge-model {
        background-color: #3b82f6;
        color: #ffffff;
    }
    .badge-status {
        background-color: #10b981;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Environment & API Key Setup
# ---------------------------------------------------------
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = None

if not api_key or "YOUR_KEY" in api_key:
    st.error("⚠️ OpenAI API Key not found. Please set it in your .env file or Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# ---------------------------------------------------------
# 3. Agent Tools Definition
# ---------------------------------------------------------
def calculate_power(base: float, exponent: float) -> str:
    return json.dumps({"result": base ** exponent})

def get_current_time() -> str:
    return json.dumps({"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

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
                "properties": {"base": {"type": "number"}, "exponent": {"type": "number"}},
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

# Initialize state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful AI Agent with internet access via tools. Answer clearly in English."}
    ]

# ---------------------------------------------------------
# 4. Sidebar Controls & Attachments
# ---------------------------------------------------------
send_image_triggered = False

with st.sidebar:
    st.markdown("### ⚙️ Control Panel")
    
    if st.button("🗑️ Clear Conversation", use_container_width=True, type="secondary"):
        st.session_state.messages = [
            {"role": "system", "content": "You are a helpful AI Agent with internet access via tools. Answer clearly in English."}
        ]
        st.session_state.last_tool = None
        st.session_state.uploaded_img_data = None
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 📎 Media Attachments")
    
    uploaded_image = st.file_uploader("Upload Image (Vision Analysis)", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Attached Image", use_container_width=True)
        st.session_state.uploaded_img_data = uploaded_image
        
        # Express button to analyze image immediately
        if st.button("📤 Send Image for Analysis", use_container_width=True, type="primary"):
            send_image_triggered = True

    st.write("")
    audio_val = st.audio_input("Record Voice Message")

    st.markdown("---")
    st.markdown("### 📊 System Status")
    st.markdown("""
        <div class="badge-container">
            <span class="badge badge-model">GPT-4o-mini</span>
            <span class="badge badge-status">Search Active</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    if "last_tool" in st.session_state and st.session_state.last_tool:
        st.info(f"🛠️ **Last Executed Tool:**\n`{st.session_state.last_tool}`")

# ---------------------------------------------------------
# 5. Header Area
# ---------------------------------------------------------
st.markdown("""
<div class="header-container">
    <div class="header-title">⚡ AI Agent Workspace</div>
    <div class="header-subtitle">Smart assistant with multi-modal capabilities (Web Search, Math, Vision & Voice Transcription).</div>
</div>
""", unsafe_allow_html=True)

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] != "system" and "content" in msg and msg["content"]:
        avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            if isinstance(msg["content"], str):
                st.write(msg["content"])
            elif isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item.get("type") == "text":
                        st.write(item.get("text"))
                    elif item.get("type") == "image_url":
                        st.image(item.get("image_url", {}).get("url"), caption="Uploaded Image", width=300)

# ---------------------------------------------------------
# 6. Inputs & Processing Logic
# ---------------------------------------------------------
chat_input_val = st.chat_input("Ask a question, calculate math, or describe the image...")

# Voice Transcription
if audio_val and "audio_processed" not in st.session_state:
    with st.spinner("🎙️ Transcribing audio..."):
        try:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_val
            )
            chat_input_val = transcription.text
            st.session_state.audio_processed = True
        except Exception as e:
            st.error(f"Error processing audio: {e}")

# Determine if we should process input
user_input_text = chat_input_val
should_process = False

if send_image_triggered and st.session_state.get("uploaded_img_data"):
    should_process = True
    if not user_input_text:
        user_input_text = "Please analyze and describe this image."
elif user_input_text:
    should_process = True

# Process Input
if should_process:
    if st.session_state.get("uploaded_img_data"):
        base64_img = encode_image(st.session_state.uploaded_img_data)
        user_content = [
            {"type": "text", "text": user_input_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
            }
        ]
        st.session_state.uploaded_img_data = None
    else:
        user_content = user_input_text

    st.session_state.messages.append({"role": "user", "content": user_content})
    
    with st.chat_message("user", avatar="🧑‍💻"):
        if isinstance(user_content, list):
            st.write(user_input_text)
            st.image(user_content[1]["image_url"]["url"], caption="Uploaded Image", width=300)
        else:
            st.write(user_content)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Processing request..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=600
                )

                response_message = response.choices[0].message
                
                if response_message.tool_calls:
                    st.session_state.messages.append(response_message)
                    
                    for tool_call in response_message.tool_calls:
                        fn_name = tool_call.function.name
                        fn_args = json.loads(tool_call.function.arguments)
                        
                        st.session_state.last_tool = fn_name
                        
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
                        max_tokens=600
                    )
                    reply = final_res.choices[0].message.content
                else:
                    reply = response_message.content

                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

            except Exception as e:
                st.error(f"❌ Error: {e}")