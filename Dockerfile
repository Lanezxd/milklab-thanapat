# ใช้ Python 3.10-slim เพื่อขนาด Image ที่เล็กและประหยัดทรัพยากร
FROM python:3.10-slim

# ป้องกัน Python เขียนไฟล์ .pyc และสั่งให้ Log แสดงผลทันที
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# กำหนดโฟลเดอร์ทำงานใน Container
WORKDIR /app

# ติดตั้ง C++ Build tools ที่จำเป็นสำหรับ FAISS
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกไฟล์ทั้งหมดในโปรเจกต์
COPY . .

# เปิด Port สำหรับ Streamlit
EXPOSE 8501

# คำสั่งสำหรับรัน Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]