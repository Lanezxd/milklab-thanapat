import os
import re
from collections import Counter
import streamlit as st
from dotenv import load_dotenv
from google import genai

# โหลด Environment Variables
load_dotenv(override=True)

# ---------------------------------------------------------
# 1. ตั้งค่าหน้าตา Streamlit & โทนสีตามโจทย์
# ---------------------------------------------------------
st.set_page_config(
    page_title="BoardGame Haven Assistant",
    page_icon="🎲",
    layout="centered"
)

# ไอคอน SVG รูป Meeple / บอร์ดเกม สำหรับ Avatar ผู้ช่วย (ไม่ใช้ Emoji)
BOT_AVATAR_SVG = """data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="22" r="14" fill="%23d4a373"/><path d="M 32 40 C 40 36, 60 36, 68 40 C 72 45, 84 58, 88 70 C 80 72, 74 68, 68 62 L 74 92 C 60 94, 56 82, 50 82 C 44 82, 40 94, 26 92 L 32 62 C 26 68, 20 72, 12 70 C 16 58, 28 45, 32 40 Z" fill="%23d4a373"/></svg>"""
USER_AVATAR_SVG = """data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23718096"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>"""

st.markdown("""
    <style>
    /* สีพื้นหลังหน้าเว็บ (Background: #ffffff) */
    .stApp {
        background-color: #ffffff;
        font-family: 'Kanit', sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Header Card โทนสีหลัก #faedcd และขอบเน้น #d4a373 */
    .title-container {
        background-color: #faedcd;
        border: 2px solid #d4a373;
        padding: 1.8rem;
        border-radius: 18px;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(212, 163, 115, 0.2);
    }
    .title-container h1 {
        color: #7f4f24;
        font-weight: 700;
        font-size: 1.9rem;
        margin-bottom: 0.2rem;
    }
    .title-container p {
        color: #936639;
        font-size: 0.95rem;
        margin: 0;
    }
    
    /* กล่องข้อความแชต (Chat Bubble: #d9d9d9) */
    .stChatMessage {
        background-color: #d9d9d9 !important;
        border-radius: 14px !important;
        padding: 0.9rem !important;
        margin-bottom: 0.7rem !important;
        color: #2b2b2b !important;
    }
    
    /* กล่องข้อความฝั่งผู้ช่วยใช้โทนสีอ่อนเพื่อความคมชัด */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #f4ece1 !important;
        border: 1px solid #e7d8c9 !important;
    }
    
    /* ช่อง Input Box ด้านล่าง */
    .stChatInputContainer > div {
        border-radius: 22px !important;
        border: 1.5px solid #d4a373 !important;
        background-color: #ffffff !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    }
    .stChatInputContainer > div:focus-within {
        border-color: #b07d4b !important;
        box-shadow: 0 0 8px rgba(212, 163, 115, 0.4) !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #faedcd;
        border-right: 1.5px solid #d4a373;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ส่วน Sidebar (แถบข้อมูลด้านข้าง)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎲 BoardGame Haven")
    st.markdown("*คาเฟ่และบริการเช่าบอร์ดเกม*")
    st.divider()
    
    st.markdown("### 📍 ข้อมูลเวลาและสถานที่")
    st.markdown("⏰ **เวลาเปิดบริการ:** 10:00 - 20:00 น. *(หยุดทุกวันจันทร์)*")
    st.markdown("📌 **พิกัดร้าน:** หน้ามหาวิทยาลัยราชมงคลอีสาน วิทยาเขตขอนแก่น")
    
    st.divider()
    st.markdown("### 💰 ตารางราคาด่วน (Quick Pricing)")
    st.markdown("""
    - **ค่าบริการนั่งเล่น:** 50.- / ชม.  
      *(เหมาวัน Day Pass 150.- / คน)*
    - **ค่าเช่าเกมรายวัน:** เริ่มต้น 50 - 120.- / วัน  
      *(มีเงินมัดจำตามประเภทเกม)*
    """)
    st.info("💡 มี Game Master คอยสอนกติกาและแนะนำการเล่นฟรีทุกโต๊ะ!")

# ---------------------------------------------------------
# 3. Main Header & Subtitle
# ---------------------------------------------------------
st.markdown("""
    <div class="title-container">
        <h1>🎲 BoardGame Haven Assistant</h1>
        <p>ระบบผู้ช่วย AI แนะนำบอร์ดเกม เช็กราคาค่าบริการ และกติกาการเช่า-เล่นที่ร้าน</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. RAG Pipeline: Lightweight Chunking & Retrieval
# ---------------------------------------------------------
@st.cache_resource
def load_knowledge_chunks():
    kb_path = "boardgame_kb.md"
    if not os.path.exists(kb_path):
        kb_path = "menu_kb.md"  # Fallback
        if not os.path.exists(kb_path):
            st.error("⚠️ ไม่พบไฟล์คลังข้อมูล boardgame_kb.md")
            return []

    with open(kb_path, "r", encoding="utf-8") as f:
        text = f.read()

    raw_chunks = text.split("\n## ")
    chunks = []
    for idx, c in enumerate(raw_chunks):
        if c.strip():
            formatted_chunk = c.strip() if idx == 0 else f"## {c.strip()}"
            chunks.append(formatted_chunk)

    return chunks

chunks = load_knowledge_chunks()

def tokenize(text: str) -> list[str]:
    """แยกคำไทยและอังกฤษอย่างง่าย"""
    return re.findall(r'[\u0E00-\u0E7F]+|[a-zA-Z0-9]+', text.lower())

def retrieve_top_k(query: str, k: int = 5) -> list[str]:
    """ค้นหา Chunks ที่เกี่ยวข้องด้วย Relevance Score (ดึง top-5 ให้ครอบคลุมทุกหมวด)"""
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
            if token in chunk_counts:
                score += chunk_counts[token] * 3
            elif token in chunk_text_lower:
                score += 1.5
                
        scores.append(score)

    ranked = [c for _, c in sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)]
    return ranked[:k]

# ---------------------------------------------------------
# 5. Gemini Client & Chat State Management
# ---------------------------------------------------------
@st.cache_resource
def get_genai_client(api_key: str):
    return genai.Client(api_key=api_key)

# Welcome Message เริ่มต้น
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "สวัสดีครับ ยินดีต้อนรับสู่ BoardGame Haven ครับ! ผมสามารถช่วยแนะนำบอร์ดเกมตามจำนวนผู้เล่นหรือแนวที่ชอบ เช็กราคาค่าบริการนั่งเล่น/ค่าเช่า และตอบคำถามกติการ้านได้เลยครับ มีอะไรให้ผมช่วยดูแลสอบถามได้เลยครับ 🎲✨"
        }
    ]

# แสดง Chat Feed ย้อนหลัง
for msg in st.session_state.messages:
    avatar = BOT_AVATAR_SVG if msg["role"] == "assistant" else USER_AVATAR_SVG
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# Chat Input Box
if user_input := st.chat_input("พิมพ์สอบถามบอร์ดเกม กติกา หรืออัตราค่าบริการ..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar=USER_AVATAR_SVG):
        st.write(user_input)

    # ดึง Context จาก RAG (ใช้ k=5 ครอบคลุมกฎและ FAQ)
    retrieved_context = retrieve_top_k(user_input, k=5)
    context_str = "\n---\n".join(retrieved_context) if retrieved_context else "ไม่มีข้อมูลใน Context"

    prompt = f"""คุณคือผู้ช่วย AI ประจำร้าน BoardGame Haven ตอบคำถามลูกค้าด้วยความสุภาพ เป็นกันเอง ชัดเจน และถูกต้อง
โปรดใช้ข้อมูลจาก "เอกสารอ้างอิง (Context)" ด้านล่างนี้ในการตอบคำถามเท่านั้น หากไม่มีข้อมูลใน Context ให้ตอบตามตรงว่าไม่พบข้อมูลดังกล่าวในระบบของร้าน BoardGame Haven ครับ

กฎการตอบ:
- แนะนำบอร์ดเกม กติกา อัตราค่าบริการเช่า และ Day Pass ให้ตรงตามข้อมูลจริง
- สื่อสารอย่างกระชับและเป็นมิตร
- สามารถใช้ Emoji 1-2 ตัวปิดท้ายประโยคเพื่อความมีชีวิตชีวาได้ เช่น 🎲, 🃏, ✨

[เอกสารอ้างอิง (Context)]
{context_str}

[คำถามลูกค้า]
{user_input}
"""

    api_key = os.getenv("GOOGLE_API_KEY")

    with st.chat_message("assistant", avatar=BOT_AVATAR_SVG):
        if not api_key:
            bot_response = "⚠️ ไม่พบ GOOGLE_API_KEY ในไฟล์ .env กรุณาตรวจสอบการตั้งค่าครับ"
            st.warning(bot_response)
        else:
            try:
                client = get_genai_client(api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                bot_response = response.text
                st.write(bot_response)
            except Exception:
                bot_response = "ขออภัยครับ ขณะนี้ระบบมีผู้ใช้งานหนาแน่นชั่วคราว กรุณาลองใหม่อีกครั้ง หรือสอบถามข้อมูลบอร์ดเกมได้เลยครับ 🎲"
                st.warning(bot_response)

    st.session_state.messages.append({"role": "assistant", "content": bot_response})