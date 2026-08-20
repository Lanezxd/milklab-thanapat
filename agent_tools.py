import os
from datetime import datetime
from dotenv import load_dotenv
import sales_logger

# โหลด Environment Variables จากไฟล์ .env
load_dotenv(override=True)

# ดึง GOOGLE_API_KEY จากไฟล์ .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def _validate_sale(item, qty, price):
    # 1. Validation: ตรวจสอบความถูกต้องของข้อมูลก่อนนำไปบันทึกจริง
    if qty <= 0:
        return 'qty > 0'
    if price < 0:
        return 'price >= 0'
    if qty > 500:
        return 'qty too large'

    # 🌟 เกราะป้องกันหลังบ้าน: ตรวจจับและสกัดคำโกง (Prompt Injection) ที่พยายามเข้ามาควบคุมระบบ
    invalid_keywords = [
        "ignore instruction",
        "ignore instructions",
        "override",
        "system prompt",
        "forget rules",
    ]
    if any(kw in str(item).lower() for kw in invalid_keywords):
        return 'malicious input detected in item name'

    return None


def log_sale(item, quantity, price):
    """บันทึกรายการเช่าบอร์ดเกม หรือค่าบริการ Day Pass นั่งเล่นในร้าน"""
    # 2. Wrapper: จัดการตรวจสอบความถูกต้องก่อนส่งไปทำ Action หลังบ้าน
    err = _validate_sale(item, quantity, price)
    if err:
        if err == 'qty > 0':
            return "ปฏิเสธการบันทึก: ตรวจพบข้อผิดพลาดด้านความถูกต้องของข้อมูล (qty > 0)"
        return f"ปฏิเสธการบันทึก: ตรวจพบข้อผิดพลาดด้านความถูกต้องของข้อมูล ({err})"

    try:
        # เรียกใช้งานฟังก์ชันหลักใน sales_logger.py เพื่อบันทึกลง Google Sheets
        res = sales_logger.append_to_sheet(
            item=item, qty=quantity, price=price
        )
        total_amount = quantity * price

        # 🌟 สั่งให้ยิงแจ้งเตือนเด้งเข้ากลุ่ม Telegram ทันทีหลังบันทึกสำเร็จ
        try:
            msg = f"🎲 [Agent] บันทึกรายการ: {item} x{quantity} รายการ รวมเป็นเงิน {total_amount:,.2f} บาท"
            sales_logger.send_notification(msg)
        except Exception as tele_err:
            # ครอบไว้เพื่อไม่ให้ระบบพังในกรณีที่โทเค็น Telegram ใน .env แอบหลุดหรือมีปัญหา
            print(
                f"[WARN] บันทึก Sheet สำเร็จแต่ส่ง Telegram พัง: {tele_err}"
            )

        # คืนค่ากลับไปในรูปแบบ Dict สมบูรณ์เพื่อให้แสดงผลในผลลัพธ์ของ Agent ได้ชัดเจน
        return {
            'ok': True,
            'tool': 'log_sale',
            'item': item,
            'qty': quantity,
            'price': price,
            'total': res.get('total', total_amount)
            if isinstance(res, dict)
            else total_amount,
        }
    except Exception as e:
        return {'ok': False, 'tool': 'log_sale', 'error': str(e)}


# 🚀 🌟 ฟังก์ชันจำลองสำหรับ RAG Knowledge Base ของร้านบอร์ดเกม
def search_kb(question: str) -> str:
    """ฟังก์ชันสืบค้นคลังข้อมูลความรู้เกี่ยวกับบอร์ดเกม กติกา และอัตราค่าบริการของ BoardGame Haven"""
    q = question.lower()
    if "catan" in q or "คาทาน" in q:
        return "ฐานข้อมูลระบุ: Catan ค่าเช่า 120 บาท/วัน (มัดจำ 500 บาท) เล่นได้ 3-4 คน แนววางแผนและเจรจาค้าขาย"
    elif "day pass" in q or "นั่งเล่น" in q or "ค่าบริการ" in q:
        return "ฐานข้อมูลระบุ: ค่าบริการนั่งเล่นในร้าน 50 บาท/ชม./คน หรือเหมาทั้งวัน Day Pass 150 บาท/คน"
    elif "2 คน" in q or "สองคน" in q:
        return "ฐานข้อมูลระบุ: บอร์ดเกมที่แนะนำสำหรับ 2 คน ได้แก่ Splendor, Exploding Kittens และ Coup"
    return f"ไม่พบข้อมูลจำเพาะสำหรับคำถาม '{question}' ในคลังระบบ แต่จากข้อมูลทั่วไป BoardGame Haven เปิดบริการ 16:00 - 00:00 น. (หยุดวันจันทร์) มี Game Master สอนฟรีครับ"


# 🚀 🌟 ฟังก์ชันดึงรายงานและเชื่อมโยงไปหาตัวสรุปยอดจากชีทของจริงใน sales_logger.py
def get_yesterday_summary() -> str:
    """เรียกใช้งานเครื่องมืออ่านข้อมูลชีทหลังบ้านเพื่อดึงรายงานสรุปรายได้ประจำวันเมื่อวาน"""
    return sales_logger.get_yesterday_total_sales()


# 3. Registry: ทะเบียนเปิดทางสัญญา (Contract) ให้กับ Harness
TOOL_REGISTRY = {
    'log_sale': {
        'fn': log_sale,
        'args': ('item', 'quantity', 'price'),
        'coerce': {'item': str, 'quantity': int, 'price': float},
    },
    'record_sale': {
        'fn': log_sale,
        'args': ('item', 'quantity', 'price'),
        'coerce': {'item': str, 'quantity': int, 'price': float},
    },
    'search_knowledge_base': {
        'fn': search_kb,
        'args': ('question',),
        'coerce': {'question': str},
    },
    'get_yesterday_summary': {
        'fn': get_yesterday_summary,
        'args': (),
        'coerce': {},
    },
}