import os
import streamlit as st
import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai

# โหลด Environment Variables
load_dotenv()

# ---------------------------------------------------------
# 1. ตั้งค่าหน้าตา Streamlit สไตล์ มินิมอล โทนสีฟ้า-ขาว
# ---------------------------------------------------------
st.set_page_config(
    page_title="MilkLab° RAG Chatbot",
    page_icon="🥛",
    layout="centered"
)

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; font-family: 'Kanit', sans-serif; }
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
    .title-container h1 { color: #0284C7; font-weight: 700; margin-bottom: 0.3rem; }
    .title-container p { color: #0369A1; font-size: 0.95rem; margin: 0; }
    .stChatMessage { border-radius: 16px !important; padding: 1rem !important; margin-bottom: 0.8rem !important; }
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
# 2. ดึง API Key
# ---------------------------------------------------------
api_key = (
    os.getenv("GEMINI_API_KEY") or 
    os.getenv("GOOGLE_API_KEY") or 
    st.secrets.get("GEMINI_API_KEY") or 
    st.secrets.get("GOOGLE_API_KEY")
)

# ---------------------------------------------------------
# 3. RAG Pipeline: Gemini Embedding (ประหยัด RAM) + FAISS
# ---------------------------------------------------------
@st.cache_resource
def init_rag_pipeline(key: str):
    kb_path = "menu_kb.md"
    if not os.path.exists(kb_path):
        st.error(f"⚠️ ไม่พบไฟล์คลังข้อมูล {kb_path}")
        return None, None, []

    with open(kb_path, "r", encoding="utf-8") as f:
        text = f.read()

    raw_chunks = text.split("\n\n")
    chunks = [c.strip() for c in raw_chunks if c.strip()]

    if not key:
        return None, None, chunks

    try:
        client = genai.Client(api_key=key)
        embeddings = []
        # แปลง Chunk เป็น Vector ผ่าน Gemini Embedding API (ไม่กิน RAM เครื่อง)
        for chunk in chunks:
            res = client.models.embed_content(
                model="text-embedding-004",
                contents=chunk
            )
            embeddings.append(res.embedding.values)

        embeddings_np = np.array(embeddings, dtype=np.float32)
        dimension = embeddings_np.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_np)

        return client, index, chunks
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด Embedding: {str(e)}")
        return None, None, chunks

client, index, chunks = init_rag_pipeline(api_key)

# ---------------------------------------------------------
# 4. Retrieval Function (ดึง top-k=3 Chunks)
# ---------------------------------------------------------
def retrieve_top_k(query: str, k: int = 3):
    if not client or not index or not chunks:
        return []
    
    res = client.models.embed_content(
        model="text-embedding-004",
        contents=query
    )
    query_vector = np.array([res.embedding.values], dtype=np.float32)
    distances, indices = index.search(query_vector, k)
    
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

for msg in st.session_state.messages:
    avatar = "🥛" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

if user_input := st.chat_input("สอบถามข้อมูลร้าน..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    retrieved_context = retrieve_top_k(user_input, k=3)
    context_str = "\n---\n".join(retrieved_context)

    prompt = f"""คุณคือผู้ช่วย AI ประจำร้าน MilkLab° ตอบคำถามลูกค้าด้วยความสุภาพ เป็นกันเอง กระชับ และถูกต้อง
โปรดใช้ข้อมูลจาก "เอกสารอ้างอิง (Context)" ด้านล่างนี้ในการตอบคำถามเท่านั้น หากไม่มีข้อมูลใน Context ให้ตอบตามตรงว่าไม่พบข้อมูลดังกล่าวในระบบของร้าน MilkLab°

[เอกสารอ้างอิง (Context)]
{context_str}

[คำถามลูกค้า]
{user_input}
"""

    with st.chat_message("assistant", avatar="🥛"):
        if not api_key:
            bot_response = "⚠️ ไม่พบ API Key ในระบบ กรุณาตรวจสอบการตั้งค่า Secret ครับ"
            st.warning(bot_response)
        else:
            try:
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