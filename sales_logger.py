import argparse
import os
import sys
import requests
import gspread
import base64
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


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
            filename="credentials/milk-lab-0df755c40bc9.json")

    else:
        raise RuntimeError("ไม่พบ Credentials สำหรับเข้าถึง Google Sheets")

    sh = gc.open_by_key(sheet_id)
    worksheet = sh.sheet1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = qty * price
    row_data = [timestamp, menu, qty, price, total]

    worksheet.append_row(row_data)
    return {"timestamp": timestamp, "menu": menu, "qty": qty, "price": price, "total": total}


def send_notification(message: str) -> str:
    """TODO 2: ส่ง message ไปยัง Telegram bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError(
            "ไม่ได้ตั้งค่า TELEGRAM_BOT_TOKEN หรือ TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Telegram API Error: {response.text}")

    return "telegram"


def main() -> int:
    parser = argparse.ArgumentParser(description="MilkLab Sales Logger")
    parser.add_argument("--menu", required=True, help="ชื่อเมนู")
    parser.add_argument("--qty", type=int, required=True, help="จำนวนขวด")
    parser.add_argument("--price", type=float,
                        required=True, help="ราคาต่อขวด")
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
            f"บันทึก {args.menu} x{args.qty} = {total} บาท")
        print(
            f"[OK] บันทึกและแจ้งเตือนผ่าน {provider} เรียบร้อย ยอด {total} บาท")
    except Exception as exc:
        print(
            f"[WARN] บันทึก Sheet สำเร็จแต่ส่งแจ้งเตือนล้มเหลว: {exc}", file=sys.stderr)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
