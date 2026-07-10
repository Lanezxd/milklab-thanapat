from datetime import datetime
import sales_logger


def _validate_sale(menu, qty, price):
    # 1. Validation: ตรวจสอบความถูกต้องของข้อมูลก่อนนำไปบันทึกจริง
    if qty <= 0:
        return 'qty > 0'
    if price < 0:
        return 'price >= 0'
    if qty > 500:
        return 'qty too large'

    # 🌟 เกราะป้องกันหลังบ้าน: ตรวจจับและสกัดคำโกง (Prompt Injection) ที่พยายามเข้ามาควบคุมระบบในชื่อเมนู
    invalid_keywords = ["ignore instruction", "ignore instructions",
                        "override", "system prompt", "forget rules"]
    if any(kw in str(menu).lower() for kw in invalid_keywords):
        return 'malicious input detected in menu name'

    return None


def log_sale(menu, quantity, price):
    # 2. Wrapper: จัดการตรวจสอบความถูกต้องก่อนส่งไปทำ Action หลังบ้าน
    err = _validate_sale(menu, quantity, price)
    if err:
        return {'ok': False, 'tool': 'log_sale', 'error': err}

    try:
        # เรียกใช้งานฟังก์ชันหลักใน sales_logger.py เพื่อบันทึกลง Google Sheets
        res = sales_logger.append_to_sheet(
            menu=menu, qty=quantity, price=price)
        total_amount = quantity * price

        # 🌟 จุดที่เพิ่ม: สั่งให้ยิงแจ้งเตือนเด้งเข้ากลุ่ม Telegram ทันทีหลังบันทึกสำเร็จ
        try:
            msg = f"🔔 [Agent] บันทึกขาย: {menu} x{quantity} ขวด รวมเป็นเงิน {total_amount} บาท"
            sales_logger.send_notification(msg)
        except Exception as tele_err:
            # ครอบไว้เพื่อไม่ให้ระบบพังในกรณีที่โทเค็น Telegram ใน .env แอบหลุดหรือมีปัญหา
            print(f"[WARN] บันทึก Sheet สำเร็จแต่ส่ง Telegram พัง: {tele_err}")

        # คืนค่ากลับไปในรูปแบบ Dict สมบูรณ์เพื่อให้แสดงผลในผลลัพธ์ของ Agent ได้ชัดเจน
        return {
            'ok': True,
            'tool': 'log_sale',
            'menu': menu,
            'qty': quantity,
            'price': price,
            'total': res.get('total', total_amount) if isinstance(res, dict) else total_amount
        }
    except Exception as e:
        return {'ok': False, 'tool': 'log_sale', 'error': str(e)}


# 🚀 🌟 ฟังก์ชันจำลองสำหรับ Session 3: RAG Knowledge Base (ตรงตามโจทย์ภาพสไลด์)
def search_kb(question: str) -> str:
    """ฟังก์ชันสืบค้นคลังข้อมูลความรู้เกี่ยวกับวัตถุดิบและผลิตภัณฑ์ของร้าน MilkLab"""
    q = question.lower()
    if "ชาเขียว" in q and ("caffeine" in q or "คาเฟอีน" in q):
        return "ฐานข้อมูลระบุ: เมนูชาเขียวมัทฉะของ MilkLab มีคาเฟอีนธรรมชาติประมาณ 35mg ต่อแก้วครับ"
    elif "ลาเต้น้ำผึ้ง" in q or "ส่วนผสม" in q:
        return "ฐานข้อมูลระบุ: ลาเต้น้ำผึ้ง ประกอบด้วย นมสดสูตรพิเศษ MilkLab, เอสเพรสโซ่ 2 ช็อต และน้ำผึ้งป่าแท้ 100% หวานธรรมชาติ"
    return f"ไม่พบข้อมูลจำเพาะสำหรับคำถาม '{question}' ในคลังระบบ แต่จากข้อมูลทั่วไป สินค้าของ MilkLab ใช้วัตถุดิบสดใหม่ทุกวันครับ"


# 🚀 🌟 ฟังก์ชันดึงรายงานและเชื่อมโยงไปหาตัวสรุปยอดขายจากชีทของจริงใน sales_logger.py
def get_yesterday_summary() -> str:
    """เรียกใช้งานเครื่องมืออ่านข้อมูลชีทหลังบ้านเพื่อดึงรายงานประจำวันเมื่อวาน"""
    return sales_logger.get_yesterday_total_sales()


# 3. Registry: ทะเบียนเปิดทางสัญญา (Contract) ให้กับ Harness
TOOL_REGISTRY = {
    'log_sale': {
        'fn': log_sale,
        'args': ('menu', 'quantity', 'price'),
        'coerce': {
            'menu': str,
            'quantity': int,
            'price': float
        }
    },
    'record_sale': {
        'fn': log_sale,
        'args': ('menu', 'quantity', 'price'),
        'coerce': {
            'menu': str,
            'quantity': int,
            'price': float
        }
    },
    # 🚀 🌟 เพิ่มคีย์คู่สัญญาสำหรับเครื่องมือค้นหาข้อมูล RAG จาก S3
    'search_knowledge_base': {
        'fn': search_kb,
        'args': ('question',),
        'coerce': {
            'question': str
        }
    },
    # 🚀 🌟 เพิ่มบล็อกนี้ตามสไลด์เพื่อเปิดทางสัญญาให้เอเจนท์สามารถเรียกใช้ทูลดึงรายงานจากชีทจริง
    'get_yesterday_summary': {
        'fn': get_yesterday_summary,
        'args': (),
        'coerce': {}
    }
}
