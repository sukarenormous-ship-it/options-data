#!/usr/bin/env python3
"""สร้าง docs/nq-appendix-drills.html จากกล่อง "ลองทำเอง" ของทุกบท

เหตุผลเดียวกับ nq_glossary.py — รวบรวมด้วยมือแล้วจะเพี้ยนจากบททันทีที่แก้บท

    python3 tools/nq_drills.py
"""

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

TITLES = {
    "0": "เส้นตัดกันแล้วไง", "1": "ภาษาของความไม่แน่นอน", "2": "ข้อความที่ผิดได้",
    "3": "ทำไมอินดิเคเตอร์ถึงหลอก", "4": "การกระจายและหาง", "5": "ต้นทุนและอีกฝั่งของดีล",
    "6": "โครงสร้างจ่ายผล", "7": "ขนาดและการอยู่รอด", "8": "บันทึก ทดสอบ ยอมผิด",
    "9": "30 วันของมิน",
}


def collect():
    chapters = []
    for path in sorted(glob.glob(os.path.join(DOCS, "nq-part*.html"))):
        part = re.search(r"part(\d+)\.html", path).group(1)
        with open(path) as fh:
            html = fh.read()
        box = re.search(r"✍️ ลองทำเอง[^<]*</div>\s*<ol>(.*?)</ol>", html, re.S)
        if not box:
            continue
        items = re.findall(r"<li>(.*?)</li>", box.group(1), re.S)
        chapters.append((part, [i.strip() for i in items]))
    return chapters


def render(chapters):
    with open(os.path.join(DOCS, "nq-part1.html")) as fh:
        shell = fh.read()
    head = shell[:shell.index("<body>") + len("<body>")]
    head = re.sub(r"<title>.*?</title>", "<title>คิดแบบ Quant — ภาคผนวก D: แบบฝึกหัดทั้งเล่ม</title>", head, count=1)
    script = shell[shell.rindex("<!-- ═══════════════ Thai line-break script"):]

    total = sum(len(items) for _, items in chapters)
    parts = []
    for part, items in chapters:
        lis = "\n".join(f"<li>{it}</li>" for it in items)
        parts.append(f'''
<h2>Part {part} — {TITLES.get(part, "")}</h2>
<p><a href="nq-part{part}.html">กลับไปอ่านบทนี้</a></p>
<ol>
{lis}
</ol>''')

    body = f'''
<div class="cover">
<h1>คิดแบบ Quant</h1>
<div class="sub">ภาคผนวก D — แบบฝึกหัดทั้งเล่ม</div>
<div class="desc">{total} ข้อจาก {len(chapters)} บท รวมไว้ที่เดียว · พิมพ์ออกมาทำได้</div>
</div>

<div class="bx bb" style="font-size:.92em"><div class="bt">🧭 วิธีใช้หน้านี้</div>
<p>แบบฝึกหัดในเล่มนี้ไม่มี "เฉลย" เพราะเกือบทุกข้อคำตอบขึ้นกับบัญชีและตลาดของคุณเอง
สิ่งที่มีคือ <strong>เกณฑ์ว่าทำข้อนั้นสำเร็จหรือยัง</strong> อยู่ท้ายหน้า</p>
<p>ทำตามลำดับก็ได้ หรือทำเฉพาะบทที่เพิ่งอ่านจบก็ได้ — แต่ข้อที่ให้ "จดไว้ก่อน"
ต้องทำก่อนเทรดจริงเสมอ ไม่ใช่ย้อนหลัง</p></div>
{"".join(parts)}

<h2>เกณฑ์ว่าทำสำเร็จแล้ว</h2>

<div class="bx bg"><div class="bt">✅ Monday-Morning Test ฉบับ non-quant</div>
<p>ถ้าทำแบบฝึกหัดครบแล้ว คุณควรผลิตของหกชิ้นนี้ได้ภายในหนึ่งชั่วโมง โดยไม่ต้องเปิดหนังสือ</p>
<ol>
<li><strong>ข้อความที่ผิดได้</strong> หนึ่งข้อ ครบห้าช่อง เกี่ยวกับตลาดที่คุณเทรดจริง</li>
<li><strong>ฐาน</strong> ของข้อความนั้น — ปกติเกิดบ่อยแค่ไหน และคุณหาตัวเลขนั้นมาจากไหน</li>
<li><strong>วิธีวัด</strong> ที่คุณอธิบายได้ว่ามันวัดอะไรจริง ๆ และพลาดตรงไหน</li>
<li><strong>ต้นทุนต่อรอบ</strong> ของตลาดคุณ พร้อมอัตราชนะขั้นต่ำที่ทำให้เสมอตัว</li>
<li><strong>ขนาดไม้</strong> ที่คำนวณจากเพดานความเสียหาย และ <strong>กฎหยุด</strong> หนึ่งข้อ</li>
<li><strong>บรรทัดในสมุด</strong> ที่เขียนไว้ก่อนเข้าไม้ ว่าอะไรจะพิสูจน์ว่าคุณผิด</li>
</ol>
<p>ข้อไหนทำไม่ได้ ให้กลับไปที่ Part ที่รับผิดชอบข้อนั้น</p></div>

<div class="bx ba"><div class="bt">📖 หมายเหตุ</div>
<p>หน้านี้สร้างด้วย <code>tools/nq_drills.py</code> ดึงจากกล่อง "ลองทำเอง" ในบทโดยตรง
ถ้าแก้บท ให้รันสคริปต์ใหม่</p></div>
'''
    return head + body + script


if __name__ == "__main__":
    chapters = collect()
    with open(os.path.join(DOCS, "nq-appendix-drills.html"), "w") as fh:
        fh.write(render(chapters))
    print(f"เขียน docs/nq-appendix-drills.html · {sum(len(i) for _, i in chapters)} ข้อ จาก {len(chapters)} บท")
