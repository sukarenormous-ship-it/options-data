#!/usr/bin/env python3
"""ตรวจคุณภาพหนังสือ "คิดแบบ Quant" ทั้งเล่มในคำสั่งเดียว

ตรวจสี่อย่างที่จุดอ่อนของเล่มเดิมในคลังเคยพลาด
  1. โครงสร้าง HTML สมดุล และไม่มี <br> ปลอมจำลองรายการ (W11)
  2. กล่องบังคับตามมาตรฐานงานฝีมือครบทุกบท
  3. ลิงก์ภายในทุกอันชี้ไปไฟล์ที่มีอยู่จริง (W8 — ห้ามอ้างถึงสิ่งที่เปิดดูไม่ได้)
  4. จำนวนศัพท์ใหม่ต่อบทไม่เกินเพดาน (W9 — กันหน้าผา)

    python3 tools/nq_qa.py
"""

import glob
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
TERM_CAP = 12

VOID = {"br", "hr", "img", "meta", "link", "input", "wbr", "source", "path", "rect",
        "line", "circle", "text", "stop", "marker", "use", "polygon", "polyline",
        "ellipse", "tspan"}

# กฎด้านล่างใช้กับ "บท" เท่านั้น — ภาคผนวกเป็นหน้าอ้างอิง มีหน้าที่ต่างกัน
REQUIRED_BOXES = [
    ("reading path", "🧭 เส้นทางอ่าน"),
    ("ประโยคทอง", 'class="pq"'),
    ("ศัพท์ใหม่", "📖 ศัพท์ใหม่ในตอนนี้"),
]
CHAPTER_BOXES = [
    ("🧠 มุมที่มองต่าง", 'class="qv"'),
    ("🎬 ฉากหน้าจอ", "🎬 ฉากหน้าจอ"),
    ("🧭 นิสัยคิด", "🧭 นิสัยคิด"),
    ("⚠️ ค่าเริ่มต้น", "⚠️ ค่าเริ่มต้น"),
    ("🧮 ตัวเลข", "🧮"),
    ("✍️ ลองทำเอง", "✍️ ลองทำเอง"),
    ("🎯 3 อย่างที่ต้องจำ", "🎯 3 อย่าง"),
    ("🔗 อยากลึกกว่านี้", "🔗"),
]


class Balance(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"ปิด </{tag}> เกินมาที่บรรทัด {self.getpos()[0]}")
            return
        top = self.stack.pop()
        if top[0] != tag:
            self.errors.append(f"คาด </{top[0]}> (เปิดบรรทัด {top[1][0]}) แต่เจอ </{tag}> บรรทัด {self.getpos()[0]}")


def main():
    files = sorted(glob.glob(os.path.join(DOCS, "nq-*.html")))
    if not files:
        print("ไม่พบไฟล์ nq-*.html")
        return 1
    existing = {os.path.basename(p) for p in glob.glob(os.path.join(DOCS, "*.html"))}
    problems = []

    for path in files:
        name = os.path.basename(path)
        is_chapter = re.match(r"nq-part\d+\.html$", name)
        with open(path) as fh:
            html = fh.read()

        parser = Balance()
        parser.feed(html)
        for e in parser.errors:
            problems.append(f"{name}: {e}")
        for tag, pos in parser.stack:
            problems.append(f"{name}: <{tag}> เปิดบรรทัด {pos[0]} แล้วไม่ได้ปิด")

        body = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S)
        # <br> ปลอมจำลองรายการ: <br> ที่ตามด้วย bullet หรือเลขข้อ
        for m in re.finditer(r"<br\s*/?>\s*(?:•|·\s|\d+\.\s)", body):
            problems.append(f"{name}: พบ <br> จำลองรายการ ควรใช้ <ul>/<ol> (ตำแหน่ง {m.start()})")

        if "data-thwbr" not in html:
            problems.append(f"{name}: ไม่มี Thai line-break script")

        if is_chapter:
            for label, needle in REQUIRED_BOXES:
                if needle not in html:
                    problems.append(f"{name}: ขาด {label}")
            for label, needle in CHAPTER_BOXES:
                if needle not in html:
                    problems.append(f"{name}: ขาดกล่อง {label}")
            box = re.search(r"📖 ศัพท์ใหม่ในตอนนี้</div>(.*?)</div>\s*(?:<!--|$)", html, re.S)
            if box:
                terms = re.findall(r"<strong>(.*?)</strong>", box.group(1))
                terms = [t for t in terms if not t.startswith(("3 คำ", "ที่เหลือ"))]
                if len(terms) > TERM_CAP:
                    problems.append(f"{name}: ศัพท์ใหม่ {len(terms)} คำ เกินเพดาน {TERM_CAP}")

        for href in set(re.findall(r'href="([^"#:]+\.html)"', html)):
            if href not in existing:
                problems.append(f"{name}: ลิงก์ไป {href} ซึ่งไม่มีไฟล์อยู่จริง")

    print(f"ตรวจ {len(files)} ไฟล์")
    if problems:
        print(f"พบปัญหา {len(problems)} ข้อ")
        for p in problems:
            print("  -", p)
        return 1
    print("ผ่านทุกข้อ ✓  (โครงสร้าง · กล่องบังคับ · ลิงก์ภายใน · เพดานศัพท์)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
