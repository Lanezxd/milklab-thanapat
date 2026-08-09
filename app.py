import os
import re
import math
from collections import Counter
import streamlit as st
from dotenv import load_dotenv
from google import genai

# โหลด Environment Variables
load_dotenv(override=True)

# ---------------------------------------------------------
# 1. ตั้งค่าหน้าตา Streamlit (มินิมอล โทนฟ้า-ขาว)
# ---------------------------------------------------------
st.set_page_config(
    page_title="MilkLab° RAG Chatbot",
    page_icon="🥛",
    layout="centered"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Kanit', sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .title-container {
        background: linear-gradient(135deg, #E0F2FE 0%, #BAE6FD 100%);
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(186, 230, 253, 0.4);
    }
    .title-container h1 {
        color: #0284C7;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .title-container p {
        color: #0369A1;
        font-size: 0.95rem;
        margin: 0;
    }
    .stChatMessage {
        border-radius: 16px !important;
        padding: 1rem !important;
        margin-bottom: 0.8rem !important;
    }
    .stChatInputContainer > div {
        border-radius: 25px !important;
        border: 1.5px solid #BAE6FD !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
    }
    .stChatInputContainer > div:focus-within {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="title-container">
        <h1>🥛 MilkLab° </h1>
        <p>ถามตอบเมนู ราคา และข้อมูลร้าน</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. RAG Pipeline: Lightweight Chunking & Pure Python Retrieval
# ---------------------------------------------------------
@st.cache_resource
def load_knowledge_chunks():
    kb_path = "menu_kb.md"
    if not os.path.exists(kb_path):
        st.error(f"⚠️ ไม่พบไฟล์คลังข้อมูล {kb_path}")
        return []

    with open(kb_path, "r", encoding="utf-8") as f:
        text = f.read()

    raw_chunks = text.split("\n\n")
    chunks = [c.strip() for c in raw_chunks if c.strip()]
    return chunks

chunks = load_knowledge_chunks()

def tokenize(text: str) -> list[str]:
    """แยกคำไทยและอังกฤษอย่างง่าย"""
    return re.findall(r'[\u0E00-\u0E7F]+|[a-zA-Z0-9]+', text.lower())

def retrieve_top_k(query: str, k: int = 3) -> list[str]:
    """ค้นหา Chunks ที่เกี่ยวข้องที่สุดด้วย Relevance Score (ไม่กิน RAM / ไม่ยิง API)"""
    if not chunks:
        return []
    
    query_tokens = tokenize(query)
    if not query_tokens:
        return chunks[:k]

    scores = []
    for chunk in chunks:
        chunk_text_lower = chunk.lower()
        chunk_tokens = tokenize(chunk)
        chunk_counts = Counter(chunk_tokens)
        
        score = 0
        for token in query_tokens:
            # คำตรงกันเป๊ะ
            if token in chunk_counts:
                score += chunk_counts[token] * 3
            # คำเป็นส่วนหนึ่งของข้อความ
            elif token in chunk_text_lower:
                score += 1.5
                
        scores.append(score)

    # จัดลำดับ Chunks จากคะแนนมากไปน้อย
    ranked = [c for _, c in sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)]
    return ranked[:k]

# ---------------------------------------------------------
# 3. Gemini Client & Chat State Management
# ---------------------------------------------------------
@st.cache_resource
def get_genai_client(api_key: str):
    return genai.Client(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "สวัสดีครับ! ยินดีต้อนรับสู่ MilkLab° สอบถามเมนู ราคา เวลาเปิด-ปิด หรือส่วนผสมกับน้องมิลค์ได้เลยครับ 🥛"}
    ]

for msg in st.session_state.messages:
    avatar = "🥛" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

if user_input := st.chat_input("สอบถามข้อมูลร้าน..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    # ดึง Context
    retrieved_context = retrieve_top_k(user_input, k=3)
    context_str = "\n---\n".join(retrieved_context) if retrieved_context else "ไม่มีข้อมูลใน Context"

    prompt = f"""คุณคือผู้ช่วย AI ประจำร้าน MilkLab° ตอบคำถามลูกค้าด้วยความสุภาพ เป็นกันเอง กระชับ และถูกต้อง
โปรดใช้ข้อมูลจาก "เอกสารอ้างอิง (Context)" ด้านล่างนี้ในการตอบคำถามเท่านั้น หากไม่มีข้อมูลใน Context ให้ตอบตามตรงว่าไม่พบข้อมูลดังกล่าวในระบบของร้าน MilkLab°

[เอกสารอ้างอิง (Context)]
{context_str}

[คำถามลูกค้า]
{user_input}
"""

    api_key = os.getenv("GOOGLE_API_KEY")

    with st.chat_message("assistant", avatar="🥛"):
        if not api_key:
            bot_response = "⚠️ ไม่พบ GOOGLE_API_KEY ในไฟล์ .env กรุณาตรวจสอบการตั้งค่าครับ"
            st.warning(bot_response)
        else:
            try:
                client = get_genai_client(api_key)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                bot_response = response.text
                st.write(bot_response)
            except Exception as e:
                bot_response = f"เกิดข้อผิดพลาดในการดึงคำตอบ: {str(e)}"
                st.error(bot_response)

    st.session_state.messages.append({"role": "assistant", "content": bot_response})