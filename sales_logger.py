import argparse
import base64
from datetime import datetime, timedelta
import json
import os
import sys
from dotenv import load_dotenv
import gspread
import requests

# โหลด Environment Variables จากไฟล์ .env
load_dotenv(override=True)


# ดึง GOOGLE_API_KEY จากไฟล์ .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def append_to_sheet(menu: str, qty: int, price: float) -> dict:
    """รองรับทั้งการอ่านไฟล์ JSON ในเครื่อง และการอ่านจาก Secret บน GitHub Actions"""
    sheet_id = os.getenv("GOOGLE_SHEETS_ID")

    # 1. ตรวจสอบว่ารันบน GitHub Actions หรือไม่ (ถ้ามี Secret B64)
    if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64"):
        creds_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
        creds_dict = json.loads(base64.b64decode(creds_b64))
        gc = gspread.service_account_from_dict(creds_dict)

    # 2. ถ้าไม่มี Secret ให้มองหาไฟล์ JSON ในเครื่อง
    elif os.path.exists("credentials/milk-lab-0df755c40bc9.json"):
        gc = gspread.service_account(
            filename="credentials/milk-lab-0df755c40bc9.json"
        )

    else:
        raise RuntimeError("ไม่พบ Credentials สำหรับเข้าถึง Google Sheets")

    sh = gc.open_by_key(sheet_id)
    worksheet = sh.sheet1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = qty * price
    row_data = [timestamp, menu, qty, price, total]

    worksheet.append_row(row_data)
    return {
        "timestamp": timestamp,
        "menu": menu,
        "qty": qty,
        "price": price,
        "total": total,
    }


def send_notification(message: str) -> str:
    """ส่ง message ไปยัง Telegram bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError(
            "ไม่ได้ตั้งค่า TELEGRAM_BOT_TOKEN หรือ TELEGRAM_CHAT_ID"
        )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Telegram API Error: {response.text}")

    return "telegram"


# 🚀 🌟 ฟังก์ชันเพิ่มเติมสำหรับคำนวณและสรุปยอดขายเมื่อวานจริงจาก Google Sheets
def get_yesterday_total_sales() -> str:
    """เปิดอ่าน Google Sheets และตรวจสอบข้อมูลเพื่อสรุปยอดขายของเมื่อวานย้อนหลัง 1 วัน"""
    try:
        sheet_id = os.getenv("GOOGLE_SHEETS_ID")

        if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64"):
            creds_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
            creds_dict = json.loads(base64.b64decode(creds_b64))
            gc = gspread.service_account_from_dict(creds_dict)
        elif os.path.exists("credentials/milk-lab-0df755c40bc9.json"):
            gc = gspread.service_account(
                filename="credentials/milk-lab-0df755c40bc9.json"
            )
        else:
            return "ไม่พบ Credentials สำหรับเข้าถึง Google Sheets"

        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1

        # ดึงแถวข้อมูลทั้งหมดในแผ่นงาน
        all_rows = worksheet.get_all_values()
        if len(all_rows) <= 1:
            return "ยังไม่มีข้อมูลบันทึกการขายใดๆ ในระบบตาราง"

        # หารูปแบบสตริงวันที่ของเมื่อวาน (ฟอร์แมต YYYY-MM-DD)
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )

        total_revenue = 0.0
        total_qty = 0

        # วนลูปตรวจสอบข้อมูลตั้งแต่แถวที่ 2 เป็นต้นไป (ข้ามหัวตาราง index 0)
        for row in all_rows[1:]:
            if len(row) >= 5:
                timestamp = row[0]  # คอลัมน์ที่ 1 คือวันเวลาที่บันทึก
                menu_name = row[1]  # คอลัมน์ที่ 2 คือชื่อเมนูสินค้า

                # 🎯 เพิ่ม Guardrail ป้องกันการดึงเอาแถว Summary Log เก่าของวันก่อนหน้ามาคำนวณซ้ำ
                if "[Summary Log]" in menu_name or "🔔" in menu_name:
                    continue

                if timestamp.startswith(yesterday_str):
                    try:
                        # คอลัมน์ที่ 3 คือจำนวนชิ้น
                        total_qty += int(row[2])
                        # คอลัมน์ที่ 5 คือราคารวมสุทธิของรายการนั้น
                        total_revenue += float(row[4])
                    except ValueError:
                        continue

        if total_qty == 0:
            return f"ยอดขายเมื่อวาน ({yesterday_str}) ยังไม่มีรายการบันทึกเข้ามาในระบบ"

        return f"สรุปยอดขายเมื่อวาน ({yesterday_str}) ขายได้รวม {total_qty} ชิ้น ยอดเงินสุทธิ {total_revenue} บาท"

    except Exception as e:
        return f"เกิดข้อผิดพลาดในการคำนวณรายงานยอดขาย: {str(e)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="MilkLab Sales Logger")
    parser.add_argument("--menu", required=True, help="ชื่อเมนู")
    parser.add_argument("--qty", type=int, required=True, help="จำนวนขวด")
    parser.add_argument(
        "--price", type=float, required=True, help="ราคาต่อขวด"
    )
    args = parser.parse_args()

    # เรียก append_to_sheet
    try:
        row = append_to_sheet(args.menu, args.qty, args.price)
        total = row["total"]
    except Exception as exc:
        print(f"[ERROR] บันทึก Sheet ล้มเหลว: {exc}", file=sys.stderr)
        return 1

    # เรียก send_notification
    try:
        provider = send_notification(
            f"บันทึก {args.menu} x{args.qty} = {total} บาท"
        )
        print(
            f"[OK] บันทึกและแจ้งเตือนผ่าน {provider} เรียบร้อย ยอด {total} บาท"
        )
    except Exception as exc:
        print(
            f"[WARN] บันทึก Sheet สำเร็จแต่ส่งแจ้งเตือนล้มเหลว: {exc}",
            file=sys.stderr,
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())