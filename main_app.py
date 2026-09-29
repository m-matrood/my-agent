import os
import json
import base64
from datetime import datetime
import streamlit as st
from openai import OpenAI
from ddgs import DDGS
from dotenv import load_dotenv
from PIL import Image

# PDF support import check
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ---------------------------------------------------------
# 1. Page Configuration & Emerald Dark Theme + Mobile Responsive
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ultra AI Agent Workspace",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    #MainMenu, footer, header, [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px !important;
    }

    /* Emerald Obsidian Hero Banner */
    .hero-container {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 40%, #0f172a 100%);
        padding: 24px 20px;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 30px -5px rgba(16, 185, 129, 0.25);
        margin-bottom: 20px;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #34d399, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 0.9rem;
        color: #a7f3d0;
        opacity: 0.9;
        margin-top: 6px;
    }

    /* Chat Messages styling */
    [data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        background-color: #0f172a;
        border: 1px solid rgba(16, 185, 129, 0.15);
    }

    /* Interactive Controls - Optimized Padding & No-Wrap for Full Text Visibility */
    .stButton>button, [data-testid="stPopover"]>button, [data-testid="stDownloadButton"]>button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        width: 100% !important;
        padding: 0.45rem 0.4rem !important;
        font-size: 0.88rem !important;
        white-space: nowrap !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover, [data-testid="stPopover"]>button:hover, [data-testid="stDownloadButton"]>button:hover {
        border-color: #10b981 !important;
        color: #10b981 !important;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
    }

    [data-testid="stChatInput"] {
        border-radius: 20px !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }

    .token-badge {
        font-size: 0.82rem;
        color: #34d399;
        background: rgba(6, 78, 59, 0.5);
        padding: 5px 14px;
        border-radius: 20px;
        border: 1px solid rgba(52, 211, 153, 0.3);
        display: inline-block;
        margin-bottom: 12px;
    }

    /* ---------------------------------------------------------
       Mobile Responsiveness Styles (شاشات الجوال < 768px)
       --------------------------------------------------------- */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.8rem !important;
        }

        .hero-container {
            padding: 14px 10px !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
        }
        .hero-title {
            font-size: 1.3rem !important;
        }
        .hero-subtitle {
            font-size: 0.75rem !important;
        }

        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 6px !important;
        }

        [data-testid="stColumn"], [data-testid="column"] {
            width: 47% !important;
            flex: 1 1 47% !important;
            min-width: 47% !important;
            margin-bottom: 4px !important;
        }

        .stButton>button, [data-testid="stPopover"]>button, [data-testid="stDownloadButton"]>button {
            font-size: 0.78rem !important;
            padding: 0.35rem 0.2rem !important;
            letter-spacing: -0.3px !important;
        }

        [data-testid="stChatMessage"] {
            padding: 0.7rem !important;
            border-radius: 10px !important;
        }

        [data-testid="stChatInput"] {
            margin-bottom: 5px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Client Setup & State Initialization
# ---------------------------------------------------------
load_dotenv()

@st.cache_resource
def get_openai_client():
    key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not key or "YOUR_KEY" in key:
        return None
    return OpenAI(api_key=key)

client = get_openai_client()

if not client:
    st.error("⚠️ OpenAI API Key is missing. Please add it to your .env file or Streamlit Secrets.")
    st.stop()

PERSONAS = {
    "General Assistant": "You are a fast, highly capable AI Agent. Help the user clearly and effectively. IMPORTANT: Whenever you use search_web or search_images, you MUST append a section titled '📌 References & Sources:' at the end of your response, listing the titles and markdown link URLs of all sources used.",
    "Senior Developer": "You are an expert software engineer. Provide clean, robust code with clear comments. Always list source URLs at the end if web search is used.",
    "Concise Mode": "Provide extremely direct, short, and accurate answers. Always append source links at the bottom if searched.",
    "Academic Expert": "Provide structured, deep, and scholarly answers. Always cite and list sources with clickable URLs at the bottom."
}

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": PERSONAS["General Assistant"]}]
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0
if "uploaded_doc_text" not in st.session_state:
    st.session_state.uploaded_doc_text = None

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def extract_file_text(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf"):
        if not HAS_PYPDF:
            return "[Error: pypdf library is not installed. Run `pip install pypdf` to support PDFs.]"
        try:
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        except Exception as e:
            return f"[Error parsing PDF: {e}]"
    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")

def generate_tts_audio(text: str):
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text[:1000]
        )
        return response.content
    except Exception:
        return None

# ---------------------------------------------------------
# 3. Agent Tools Setup
# ---------------------------------------------------------
def calculate_power(base: float, exponent: float) -> str:
    return json.dumps({"result": base ** exponent})

def get_current_time() -> str:
    return json.dumps({"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

def search_web(query: str) -> str:
    try:
        results = list(DDGS().text(query, max_results=4))
        if not results:
            return json.dumps({"result": "No search results found."})
        formatted_results = [
            {
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "url": item.get("href", "")
            }
            for item in results
        ]
        return json.dumps(formatted_results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def search_images(query: str) -> str:
    try:
        results = list(DDGS().images(query, max_results=4))
        if not results:
            return json.dumps({"result": "No images found."})
        images = [
            {
                "title": item.get("title", ""),
                "image_url": item.get("image", ""),
                "source_url": item.get("url", "")
            }
            for item in results
        ]
        return json.dumps(images, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

available_functions = {
    "calculate_power": calculate_power,
    "get_current_time": get_current_time,
    "search_web": search_web,
    "search_images": search_images
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
            "description": "Search the live internet for recent real-time text information. Always include a sources list with clickable URLs at the end of the final response when this tool is used.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_images",
            "description": "Search the live internet for images. Always include source links at the end.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    }
]

def get_optimized_messages():
    system_msg = st.session_state.messages[0]
    recent_msgs = st.session_state.messages[1:][-10:]
    return [system_msg] + recent_msgs

# ---------------------------------------------------------
# 4. Header & Token Counter Badge
# ---------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div class="hero-title">⚡ Ultra AI Workspace</div>
    <div class="hero-subtitle">Multi-Modal Workspace: Web Search, Images, PDF Documents, Voice & Vision</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="token-badge">📊 Total Session Tokens Used: <b>{st.session_state.total_tokens:,}</b></div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. Render Message History
# ---------------------------------------------------------
for msg in st.session_state.messages:
    if isinstance(msg, dict):
        role = msg.get("role")
        content = msg.get("content")
    else:
        role = getattr(msg, "role", None)
        content = getattr(msg, "content", None)

    if role and role not in ["system", "tool"] and content:
        avatar = "🧑‍💻" if role == "user" else "⚡"
        with st.chat_message(role, avatar=avatar):
            if isinstance(content, str):
                st.write(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            st.write(item.get("text"))
                        elif item.get("type") == "image_url":
                            st.image(item.get("image_url", {}).get("url"), width=300)

# ---------------------------------------------------------
# 6. Expanded Action Bar Controls Dock
# ---------------------------------------------------------
with st.container(border=True):
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.5, 1.5, 1.8, 2.3, 1.4, 1.4])

    with col1:
        with st.popover("🖼️ Image", use_container_width=True):
            uploaded_image = st.file_uploader("Attach image for vision", type=["png", "jpg", "jpeg"])
            if uploaded_image:
                st.image(Image.open(uploaded_image), caption="Attached", use_container_width=True)
                st.session_state.uploaded_img_data = uploaded_image

    with col2:
        with st.popover("📄 File", use_container_width=True):
            uploaded_doc = st.file_uploader("Attach PDF or Text file", type=["pdf", "txt", "md", "py", "json"])
            if uploaded_doc:
                extracted_text = extract_file_text(uploaded_doc)
                st.session_state.uploaded_doc_text = extracted_text
                st.success("Document loaded successfully!")

    with col3:
        with st.popover("🎙️ Voice", use_container_width=True):
            audio_val = st.audio_input("Record audio input")

    with col4:
        with st.popover("⚙️ Settings", use_container_width=True):
            selected_persona = st.selectbox("AI Persona", options=list(PERSONAS.keys()), index=0)
            st.session_state.messages[0]["content"] = PERSONAS[selected_persona]
            
            temperature_val = st.slider("Temperature (Creativity)", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
            max_tokens_val = st.slider("Max Output Tokens", min_value=250, max_value=4000, value=1000, step=250)
            enable_tts = st.checkbox("Enable Voice Responses (TTS)", value=False)

    with col5:
        selected_engine = st.selectbox(
            "Model Engine",
            options=["gpt-4o-mini", "gpt-4o", "o1-mini"],
            index=0,
            label_visibility="collapsed"
        )

    with col6:
        chat_export_data = json.dumps(
            [m for m in st.session_state.messages if isinstance(m, dict) and m.get("role") != "system"],
            ensure_ascii=False,
            indent=2
        )
        st.download_button(
            label="📥 Save",
            data=chat_export_data,
            file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    with col7:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = [{"role": "system", "content": PERSONAS[selected_persona]}]
            st.session_state.uploaded_img_data = None
            st.session_state.uploaded_doc_text = None
            st.rerun()

chat_input_val = st.chat_input("Ask a question, request web search, or analyze images & files...")

# ---------------------------------------------------------
# 7. Core Request Processing
# ---------------------------------------------------------
if 'audio_val' in locals() and audio_val and "audio_processed" not in st.session_state:
    with st.spinner("⚡ Transcribing audio..."):
        try:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_val
            )
            chat_input_val = transcription.text
            st.session_state.audio_processed = True
        except Exception as e:
            st.error(f"Audio error: {e}")

user_input_text = chat_input_val

if user_input_text:
    if st.session_state.get("uploaded_doc_text"):
        doc_excerpt = st.session_state.uploaded_doc_text[:4000]
        user_input_text = "📄 [Attached File Content]:\n```\n" + doc_excerpt + "\n```\n\n" + user_input_text
        st.session_state.uploaded_doc_text = None

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
            st.image(user_content[1]["image_url"]["url"], width=300)
        else:
            st.write(user_content)

    with st.chat_message("assistant", avatar="⚡"):
        try:
            supports_tools = selected_engine not in ["o1-mini", "o1"]

            api_args = {
                "model": selected_engine,
                "messages": get_optimized_messages(),
                "max_tokens": max_tokens_val
            }

            if supports_tools:
                api_args["tools"] = tools
                api_args["tool_choice"] = "auto"
                api_args["temperature"] = temperature_val

            initial_response = client.chat.completions.create(**api_args)
            
            if hasattr(initial_response, 'usage') and initial_response.usage:
                st.session_state.total_tokens += initial_response.usage.total_tokens

            response_message = initial_response.choices[0].message

            if supports_tools and response_message.tool_calls:
                st.session_state.messages.append(response_message.model_dump())
                
                for tool_call in response_message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)
                    
                    with st.status(f"⚡ Executing tool `{fn_name}`...", expanded=False):
                        st.write(fn_args)
                        
                    if fn_name in available_functions:
                        output = available_functions[fn_name](**fn_args)
                        st.session_state.messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": fn_name,
                            "content": output
                        })

                stream_args = {
                    "model": selected_engine,
                    "messages": get_optimized_messages(),
                    "stream": True,
                    "max_tokens": max_tokens_val
                }
                if supports_tools:
                    stream_args["temperature"] = temperature_val

                stream = client.chat.completions.create(**stream_args)
                reply = st.write_stream(stream)
            else:
                stream_args = {
                    "model": selected_engine,
                    "messages": get_optimized_messages(),
                    "stream": True,
                    "max_tokens": max_tokens_val
                }
                if supports_tools:
                    stream_args["temperature"] = temperature_val

                stream = client.chat.completions.create(**stream_args)
                reply = st.write_stream(stream)

            st.session_state.messages.append({"role": "assistant", "content": reply})

            if 'enable_tts' in locals() and enable_tts and reply:
                audio_bytes = generate_tts_audio(reply)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

        except Exception as e:
            st.error(f"❌ Processing error: {e}")