# 🎲 BoardGame Haven — AI for Solopreneur (Session 4 Pivot)

ระบบ AI Assistant และ Automation สำหรับคาเฟ่และบริการเช่าบอร์ดเกม **BoardGame Haven** (พัฒนาต่อยอดจาก MilkLab° Starter)

---

## 📌 ภาพรวมโปรเจกต์ (Project Overview)

- **Domain ธุรกิจ:** บริการเช่าบอร์ดเกมรายวัน นั่งเล่นที่ร้าน (Day Pass) และขายบอร์ดเกม
- **พิกัดร้าน:** หน้ามหาวิทยาลัยราชมงคลอีสาน วิทยาเขตขอนแก่น
- **เวลาเปิดบริการ:** 10:00 - 20:00 น. (หยุดทุกวันจันทร์)

---

## 📁 โครงสร้างไฟล์หลัก (Core Files)

| ไฟล์ | Session | คำอธิบายการทำงาน |
|---|---|---|
| `PIVOT.md` | S4 | สรุปบริบทธุรกิจ ปัญหา Solopreneur และรายละเอียดการ Pivot |
| `boardgame_kb.md` | S4 | คลังข้อมูลความรู้ (Knowledge Base) กติกา อัตราค่าบริการ และเกมแนะนำ |
| `caption_generator.py` | S1 | เจนแคปชั่นภาษาไทยสำหรับโปรโมตบอร์ดเกมและบริการผ่าน Gemini API |
| `sales_logger.py` | S2 | บันทึกการเช่า/บริการลง Google Sheets และยิงแจ้งเตือนผ่าน Telegram Bot |
| `agent_tools.py` | S2 | ทะเบียนฟังก์ชันและ Tool Guardrails (Validation / Injection Defense) |
| `agent_harness.py` | S2/S3 | Agent Router แปลงคำสั่งภาษาไทยเป็น Function Calls พร้อม Trace Log |
| `app.py` | S3/S4 | Streamlit Web App ระบบ RAG Chatbot ผู้ช่วยแนะนำบอร์ดเกม |

---

## 🛠️ เครื่องมือและเทคโนโลยี (Tech Stack)

- **Language & Runtime:** Python 3.10 / 3.11
- **LLM & Embeddings:** Gemini 2.5 Flash (`google-genai`)
- **Frontend / UI:** Streamlit
- **Data Integration:** `gspread` (Google Sheets API), `requests` (Telegram Bot API)
- **CI/CD & Deployment:** GitHub Actions, Docker, Render / Hugging Face Spaces

---

## 🚀 การเริ่มต้นใช้งาน (Quickstart)

1. ติดตั้ง Dependencies:
   ```bash
   pip install -r requirements.txt