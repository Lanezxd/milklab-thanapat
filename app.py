import os
import streamlit as st
import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai

# โหลด Environment Variables
load_dotenv(override=True)

# ---------------------------------------------------------
# 1. ตั้งค่าหน้าตา Streamlit
# ---------------------------------------------------------
st.set_page_config(
    page_title="MilkLab° RAG Chatbot",
    page_icon="🥛",
    layout="centered"
)

# Custom CSS ตกแต่งธีม มินิมอล
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
# 2. Helper Functions & Cache Gemini Client
# ---------------------------------------------------------
@st.cache_resource
def get_genai_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def get_embedding(client, text_list: list[str]) -> np.ndarray:
    """ส่งข้อความไปทำ Vector Embedding ผ่าน Gemini API (ไม่กิน RAM เครื่อง)"""
    embeddings = []
    for item in text_list:
        res = client.models.embed_content(
            model="text-embedding-004",
            contents=item
        )
        embeddings.append(res.embeddings[0].values)
    return np.array(embeddings, dtype=np.float32)

# ---------------------------------------------------------
# 3. RAG Pipeline: Chunking & FAISS Vector Store
# ---------------------------------------------------------
@st.cache_resource(show_spinner="กำลังจัดเตรียมคลังข้อมูล RAG...")
def init_rag_pipeline():
    kb_path = "menu_kb.md"
    if not os.path.exists(kb_path):
        st.error(f"⚠️ ไม่พบไฟล์คลังข้อมูล {kb_path}")
        return None, []

    client = get_genai_client()
    if not client:
        return None, []

    with open(kb_path, "r", encoding="utf-8") as f:
        text = f.read()

    raw_chunks = text.split("\n\n")
    chunks = [c.strip() for c in raw_chunks if c.strip()]

    # แปลง Chunk เป็น Vector ด้วย Gemini Embedding API
    embeddings = get_embedding(client, chunks)

    # สร้าง FAISS Index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index, chunks

index, chunks = init_rag_pipeline()

# ---------------------------------------------------------
# 4. Retrieval Function
# ---------------------------------------------------------
def retrieve_top_k(query: str, k: int = 3):
    client = get_genai_client()
    if not client or index is None or not chunks:
        return []
    
    query_vector = get_embedding(client, [query])
    distances, indices = index.search(query_vector, k)
    
    retrieved_chunks = []
    for idx in indices[0]:
        if idx < len(chunks):
            retrieved_chunks.append(chunks[idx])
            
    return retrieved_chunks

# ---------------------------------------------------------
# 5. UI & Chat Management
# ---------------------------------------------------------
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
                client = get_genai_client()
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