"""BoardGame Haven Caption Generator (S1 Pivot).

Usage:
    python caption_generator.py

Reads GOOGLE_API_KEY from .env. Generates a Thai caption for a board game or service.
"""

import os
import sys

from dotenv import load_dotenv
from google import genai

# โหลด Environment Variables
load_dotenv(override=True)

PROMPT_TEMPLATE = """\
คุณคือ social media manager ของร้าน BoardGame Haven° คาเฟ่และบริการเช่าบอร์ดเกม

จงเขียนแคปชั่นภาษาไทย 2 ถึง 3 ประโยคโปรโมตบอร์ดเกมหรือบริการ: {menu}

เงื่อนไข:
- โทนสนุกสนาน ชวนเพื่อนมาปาร์ตี้/เล่นเกมด้วยกัน ใส่ emoji เกี่ยวกับเกม🎲🃏 ได้
- ต้องมี call-to-action ปิดท้าย เช่น จองโต๊ะเลย, ทักแชตมาเช่าเกม, หรือ แวะมาปั่นเพื่อนได้เลย
- ห้ามใช้ em dash
"""

def generate_caption(game_item: str, api_key: str | None = None) -> str:
    """Generate a Thai caption for the given board game item or service."""
    key = api_key or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env or argument")
    
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT_TEMPLATE.format(menu=game_item),
    )
    return response.text or ""

def main() -> int:
    item = input("ชื่อบอร์ดเกม/บริการที่จะโปรโมต: ").strip()
    if not item:
        print("กรุณาใส่ชื่อบอร์ดเกมหรือบริการ")
        return 1
    caption = generate_caption(item)
    print()
    print(caption)
    return 0

if __name__ == "__main__":
    sys.exit(main())