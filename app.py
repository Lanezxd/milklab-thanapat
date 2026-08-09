import os
import streamlit as st

# ---------------------------------------------------------
# 0. ประหยัด RAM: จำกัด Thread ของ PyTorch/OpenMP ป้องกัน Memory Spike บน Render
# ---------------------------------------------------------
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import faiss
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from google import genai

# โหลด Environment Variables จากไฟล์ .env
load_dotenv(override=True)

# ---------------------------------------------------------
# 1. ตั้งค่าหน้าตา Streamlit และตกแต่งสไตล์ มินิมอล โทนสีฟ้า-ขาว
# ---------------------------------------------------------
st.set_page_config(
    page_title="MilkLab° RAG Chatbot",
    page_icon="🥛",
    layout="centered"
)

# Custom CSS ตกแต่งธีม มินิมอล (Soft Blue & Pure White)
st.markdown("""
    <style>
    /* พื้นหลังรวมและฟอนต์ */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Kanit', sans-serif;
    }
    
    /* ซ่อน Header / Menu ส่วนเกินเพื่อความมินิมอล */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* การ์ดหัวข้อ Title */
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
    
    /* กล่องข้อความแชท */
    .stChatMessage {
        border-radius: 16px !important;
        padding: 1rem !important;
        margin-bottom: 0.8rem !important;
    }
    
    /* ปรับแต่งกล่อง Input พิมพ์ข้อความ */
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

# ส่วนหัวของแอป (Minimal Blue Header)
st.markdown("""
    <div class="title-container">
        <h1>🥛 MilkLab° </h1>
        <p>ถามตอบเมนู ราคา และข้อมูลร้าน</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. RAG Pipeline: Chunking, Embedding, Vector Store (FAISS)
# ---------------------------------------------------------
@st.cache_resource(show_spinner="กำลังโหลดคลังข้อมูลและโมเดล...")
def init_rag_pipeline():
    kb_path = "menu_kb.md"
    if not os.path.exists(kb_path):
        st.error(f"⚠️ ไม่พบไฟล์คลังข้อมูล {kb_path} กรุณาตรวจสอบโฟลเดอร์หลัก")
        return None, None, []

    # 2.1 Chunking: อ่านไฟล์ menu_kb.md และแยกเป็น Chunk เล็กๆ
    with open(kb_path, "r", encoding="utf-8") as f:
        text = f.read()

    # แยก Chunk ด้วยบรรทัดว่าง (\n\n)
    raw_chunks = text.split("\n\n")
    chunks = [c.strip() for c in raw_chunks if c.strip()]

    # 2.2 Embedding: แปลง Chunk เป็น Vector ด้วย sentence-transformers
    embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    embeddings = embedder.encode(chunks, convert_to_numpy=True)

    # 2.3 Vector Store: สร้าง FAISS Index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype(np.float32))

    return embedder, index, chunks

embedder, index, chunks = init_rag_pipeline()

# ---------------------------------------------------------
# 3. Cache Gemini Client (ประหยัด RAM จากการสร้าง Object ใหม่ซ้ำๆ)
# ---------------------------------------------------------
@st.cache_resource
def get_genai_client(api_key: str):
    return genai.Client(api_key=api_key)

# ---------------------------------------------------------
# 4. Retrieval Function (ดึง top-k=3 Chunks)
# ---------------------------------------------------------
def retrieve_top_k(query: str, k: int = 3):
    if not embedder or not index or not chunks:
        return []
    
    query_vector = embedder.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_vector.astype(np.float32), k)
    
    retrieved_chunks = []
    for idx in indices[0]:
        if idx < len(chunks):
            retrieved_chunks.append(chunks[idx])
            
    return retrieved_chunks

# ---------------------------------------------------------
# 5. Chat State Management & UI โต้ตอบ
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "สวัสดีครับ! ยินดีต้อนรับสู่ MilkLab° สอบถามเมนู ราคา เวลาเปิด-ปิด หรือส่วนผสมกับน้องมิลค์ได้เลยครับ 🥛"}
    ]

# แสดงประวัติการสนทนา
for msg in st.session_state.messages:
    avatar = "🥛" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# ส่วนรับคำถามจากผู้ใช้
if user_input := st.chat_input("สอบถามข้อมูลร้าน..."):
    # บันทึกและแสดงคำถามผู้ใช้
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    # 5.1 Retrieval: ดึง top-k=3 chunks
    retrieved_context = retrieve_top_k(user_input, k=3)
    context_str = "\n---\n".join(retrieved_context) if retrieved_context else "ไม่มีข้อมูลใน Context"

    # 5.2 สร้าง Gemini Prompt พร้อม Context
    prompt = f"""คุณคือผู้ช่วย AI ประจำร้าน MilkLab° ตอบคำถามลูกค้าด้วยความสุภาพ เป็นกันเอง กระชับ และถูกต้อง
โปรดใช้ข้อมูลจาก "เอกสารอ้างอิง (Context)" ด้านล่างนี้ในการตอบคำถามเท่านั้น หากไม่มีข้อมูลใน Context ให้ตอบตามตรงว่าไม่พบข้อมูลดังกล่าวในระบบของร้าน MilkLab°

[เอกสารอ้างอิง (Context)]
{context_str}

[คำถามลูกค้า]
{user_input}
"""

    # 5.3 ดึง GOOGLE_API_KEY จากไฟล์ .env
    api_key = os.getenv("GOOGLE_API_KEY")

    with st.chat_message("assistant", avatar="🥛"):
        if not api_key:
            bot_response = "⚠️ ไม่พบ GOOGLE_API_KEY ในไฟล์ .env กรุณาตรวจสอบการตั้งค่าครับ"
            st.warning(bot_response)
        else:
            try:
                # เรียกใช้งาน Cached Gemini Client
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

    # บันทึกคำตอบลง Session State
    st.session_state.messages.append({"role": "assistant", "content": bot_response})