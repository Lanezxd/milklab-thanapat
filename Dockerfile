# ใช้ Python 3.10-slim เพื่อขนาด Image ที่เล็กและประหยัดทรัพยากร
FROM python:3.10-slim

# ป้องกัน Python เขียนไฟล์ .pyc และสั่งให้ Log แสดงผลทันที
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# กำหนดโฟลเดอร์ทำงานใน Container
WORKDIR /app

# ติดตั้ง C++ Build tools และ curl สำหรับ Health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# คัดลอกไฟล์ทั้งหมดในโปรเจกต์
COPY . .

# เปิด Port มาตรฐาน
EXPOSE 8501

# รองรับทั้ง Local (8501) และ Render ($PORT)
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false"]