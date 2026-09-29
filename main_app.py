import os
import json
import base64
from datetime import datetime
import streamlit as st
from openai import OpenAI
from ddgs import DDGS
from dotenv import load_dotenv
from PIL import Image

# التحقق من دعم قراءة ملفات PDF
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم العربي المائل لليمن (RTL)
# ---------------------------------------------------------
st.set_page_config(
    page_title="مساحة التفكير الذكية",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif !important;
        direction: rtl;
        text-align: right;
    }
    
    #MainMenu, footer, header, [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px !important;
    }

    /* الهيدر الرئيسي */
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
        background: linear-gradient(90deg, #34d399, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #a7f3d0;
        opacity: 0.9;
        margin-top: 6px;
    }

    /* تنسيق فقاعات المحادثة */
    [data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        background-color: #0f172a;
        border: 1px solid rgba(16, 185, 129, 0.15);
    }

    /* تنسيق الأزرار والقوائم */
    .stButton>button, [data-testid="stPopover"]>button, [data-testid="stDownloadButton"]>button {
        border-radius: 12px !important;
        font-weight: 700 !important;
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
        font-size: 0.85rem;
        color: #34d399;
        background: rgba(6, 78, 59, 0.5);
        padding: 6px 16px;
        border-radius: 20px;
        border: 1px solid rgba(52, 211, 153, 0.3);
        display: inline-block;
        margin-bottom: 12px;
    }

    /* ---------------------------------------------------------
       تنسيقات الجوال (< 768px)
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
            font-size: 1.4rem !important;
        }
        .hero-subtitle {
            font-size: 0.78rem !important;
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
# 2. تهيئة العميل والشخصيات بالعربية
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
    st.error("⚠️ مفتاح OpenAI API مفقود. يرجى إضافته إلى ملف .env أو إعدادات Streamlit Secrets.")
    st.stop()

PERSONAS = {
    "مساعد عام": "أنت مساعد ذكي وسريع للغاية. أجب على أسئلة المستخدم بوضوح ودقة. ملاحظة هامة: عند استخدام أداة البحث search_web أو search_images، يجب أن تنهي إجابتك دائماً بقسم بعنوان '📌 المصادر المعتمدة:' تذكر فيه عناوين المصادر وروابطها المباشرة.",
    "مطور برمجيات": "أنت مهندس برمجيات خبير. قدم كوداً نقياً ومنظماً مع شرح واضح باللغة العربية. اذكر المصادر وروابطها في النهاية إذا تم استخدام البحث.",
    "نمط مختصر": "قدم إجابات مباشرة وسريعة ودقيقة بدون مقدمات طويلة. اذكر روابط المصادر في الأسفل إن وجدت.",
    "خبير أكاديمي": "قدم إجابات مفصلة ومنظمة بأسلوب علمي ودقيق. قم دائماً بالتوثيق وذكر المصادر بروابطها المباشرة في النهاية."
}

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": PERSONAS["مساعد عام"]}]
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
            return "[خطأ: مكتبة pypdf غير مثبتة. قم بتشغيل `pip install pypdf` لدعم قراءة PDF.]"
        try:
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        except Exception as e:
            return f"[خطأ في قراءة ملف PDF: {e}]"
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
# 3. إعداد أدوات البحث والوظائف
# ---------------------------------------------------------
def calculate_power(base: float, exponent: float) -> str:
    return json.dumps({"result": base ** exponent})

def get_current_time() -> str:
    return json.dumps({"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

def search_web(query: str) -> str:
    try:
        results = list(DDGS().text(query, max_results=4))
        if not results:
            return json.dumps({"result": "لم يتم العثور على نتائج بحث."})
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
            return json.dumps({"result": "لم يتم العثور على صور."})
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
            "description": "حساب القوة والأس للقام بالعمليات الحسابية المعقدة",
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
            "description": "جلب التاريخ والتوقيت الحالي",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "البحث في شبكة الإنترنت عن معلومات وأخبار محدثة. يجب عليك دائماً طباعة قائمة المصادر مع الروابط في نهاية الإجابة.",
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
            "description": "البحث في الإنترنت عن الصور المباشرة.",
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
# 4. الواجهة الرئيسية باللغة العربية
# ---------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div class="hero-title">⚡ مساحة التفكير الذكية</div>
    <div class="hero-subtitle">بيئة عمل متكاملة: بحث في الإنترنت، تحليل الصور والمستندات، الصوت والتفاعل المباشر</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="token-badge">📊 إجمالي الرموز (Tokens) المستهلكة: <b>{st.session_state.total_tokens:,}</b></div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. عرض سجل المحادثات
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
# 6. شريط التحكم والأدوات العلوية بالعربية
# ---------------------------------------------------------
with st.container(border=True):
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.5, 1.5, 1.8, 2.3, 1.4, 1.4])

    with col1:
        with st.popover("🖼️ صورة", use_container_width=True):
            uploaded_image = st.file_uploader("ارفق صورة للتحليل", type=["png", "jpg", "jpeg"])
            if uploaded_image:
                st.image(Image.open(uploaded_image), caption="الصورة المرفقة", use_container_width=True)
                st.session_state.uploaded_img_data = uploaded_image

    with col2:
        with st.popover("📄 ملف", use_container_width=True):
            uploaded_doc = st.file_uploader("ارفق ملف PDF أو نصي", type=["pdf", "txt", "md", "py", "json"])
            if uploaded_doc:
                extracted_text = extract_file_text(uploaded_doc)
                st.session_state.uploaded_doc_text = extracted_text
                st.success("تم تحميل المستند بنجاح!")

    with col3:
        with st.popover("🎙️ صوت", use_container_width=True):
            audio_val = st.audio_input("سجل رسالة صوتية")

    with col4:
        with st.popover("⚙️ الإعدادات", use_container_width=True):
            selected_persona = st.selectbox("شخصية الذكاء الاصطناعي", options=list(PERSONAS.keys()), index=0)
            st.session_state.messages[0]["content"] = PERSONAS[selected_persona]
            
            temperature_val = st.slider("درجة الإبداع (Temperature)", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
            max_tokens_val = st.slider("الحد الأقصى للكلمات", min_value=250, max_value=4000, value=1000, step=250)
            enable_tts = st.checkbox("تفعيل الرد الصوتي (TTS)", value=False)

    with col5:
        selected_engine = st.selectbox(
            "محرك النموذج",
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
            label="📥 حفظ",
            data=chat_export_data,
            file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    with col7:
        if st.button("🗑️ مسح", use_container_width=True):
            st.session_state.messages = [{"role": "system", "content": PERSONAS[selected_persona]}]
            st.session_state.uploaded_img_data = None
            st.session_state.uploaded_doc_text = None
            st.rerun()

chat_input_val = st.chat_input("اكتب سؤالك، اطلب بحثاً في الإنترنت، أو قم بتحليل الملفات والصور...")

# ---------------------------------------------------------
# 7. معالجة طلبات المستخدم
# ---------------------------------------------------------
if 'audio_val' in locals() and audio_val and "audio_processed" not in st.session_state:
    with st.spinner("⚡ جاري تحويل الصوت إلى نص..."):
        try:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_val
            )
            chat_input_val = transcription.text
            st.session_state.audio_processed = True
        except Exception as e:
            st.error(f"خطأ في معالجة الصوت: {e}")

user_input_text = chat_input_val

if user_input_text:
    if st.session_state.get("uploaded_doc_text"):
        doc_excerpt = st.session_state.uploaded_doc_text[:4000]
        user_input_text = "📄 [محتوى الملف المرفق]:\n```\n" + doc_excerpt + "\n```\n\n" + user_input_text
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
                    
                    with st.status(f"⚡ جاري تشغيل أداة `{fn_name}`...", expanded=False):
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
            st.error(f"❌ حدث خطأ أثناء المعالجة: {e}")