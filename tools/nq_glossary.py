#!/usr/bin/env python3
"""สร้าง docs/nq-appendix-glossary.html จากกล่อง "ศัพท์ใหม่ในตอนนี้" ของทุกบท

ทำเป็นสคริปต์แทนการเขียนมือ เพราะภาคผนวกศัพท์ที่คัดลอกมาด้วยมือจะเพี้ยนจากบท
ทันทีที่มีการแก้บทใด ๆ — รันซ้ำหลังแก้บทได้ตลอด

    python3 tools/nq_glossary.py
"""

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

TITLES = {
    "0": "เส้นตัดกันแล้วไง",
    "1": "ภาษาของความไม่แน่นอน",
    "2": "ข้อความที่ผิดได้",
    "3": "ทำไมอินดิเคเตอร์ถึงหลอก",
    "4": "การกระจายและหาง",
    "5": "ต้นทุนและอีกฝั่งของดีล",
    "6": "โครงสร้างจ่ายผล",
    "7": "ขนาดและการอยู่รอด",
    "8": "บันทึก ทดสอบ ยอมผิด",
    "9": "30 วันของมิน",
}


def _strip(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def collect():
    """ดึงศัพท์จากทุกบท คืน [(part, tier, คำ, นิยาม)]"""
    rows = []
    for path in sorted(glob.glob(os.path.join(DOCS, "nq-part*.html"))):
        part = re.search(r"part(\d+)\.html", path).group(1)
        with open(path) as fh:
            html = fh.read()
        box = re.search(r"📖 ศัพท์ใหม่ในตอนนี้</div>(.*?)</div>\s*(?:<!--|$)", html, re.S)
        if not box:
            continue
        blk = box.group(1)

        must = re.search(r"<strong>3 คำที่ต้องจำก่อน</strong></p>\s*<ul>(.*?)</ul>", blk, re.S)
        if must:
            for term, desc in re.findall(r"<li><strong>(.*?)</strong>\s*=\s*(.*?)</li>", must.group(1), re.S):
                rows.append((part, 1, _strip(term), _strip(desc)))

        rest = re.search(r"<strong>ที่เหลือ</strong>(.*)", blk, re.S)
        if rest:
            for term, desc in re.findall(r"<strong>(.*?)</strong>\s*=\s*([^·<]*)", rest.group(1)):
                term = _strip(term)
                if term == "ที่เหลือ":
                    continue
                rows.append((part, 2, term, desc.strip().rstrip("·").strip()))
    return rows


def render(rows):
    source = os.path.join(DOCS, "nq-part1.html")
    with open(source) as fh:
        shell = fh.read()
    head = shell[:shell.index("<body>") + len("<body>")]
    head = re.sub(r"<title>.*?</title>", "<title>คิดแบบ Quant — ภาคผนวก B: ศัพท์ทั้งเล่ม</title>", head, count=1)
    script = shell[shell.rindex("<!-- ═══════════════ Thai line-break script"):]

    tier1 = [r for r in rows if r[1] == 1]
    tier2 = [r for r in rows if r[1] == 2]

    def block(items):
        out = []
        for part, _, term, desc in items:
            out.append(f'<tr><td class="nw"><strong>{term}</strong></td><td>{desc}</td>'
                       f'<td class="nw"><a href="nq-part{part}.html">Part {part}</a></td></tr>')
        return "\n".join(out)

    body = f'''
<div class="cover">
<h1>คิดแบบ Quant</h1>
<div class="sub">ภาคผนวก B — ศัพท์ทั้งเล่ม</div>
<div class="desc">{len(rows)} คำ จัดชั้นตามลำดับที่ควรจำ · แต่ละคำลิงก์กลับไปบทที่มันปรากฏครั้งแรก</div>
</div>

<div class="bx bb" style="font-size:.92em"><div class="bt">🧭 วิธีใช้หน้านี้</div>
<p>ตารางแรกคือคำที่ต้องจำให้ได้จริง ๆ ({len(tier1)} คำ) ส่วนตารางที่สองเปิดดูเมื่อสะดุดก็พอ
({len(tier2)} คำ) · หน้านี้สร้างจากกล่องศัพท์ในบทโดยตรง จึงตรงกับเนื้อหาเสมอ</p></div>

<h2>ชั้นที่ 1 — ต้องจำให้ได้</h2>
<div class="tw"><table>
<tr><th class="nw">คำ</th><th>ความหมาย</th><th class="nw">อยู่บทไหน</th></tr>
{block(tier1)}
</table></div>

<h2>ชั้นที่ 2 — เปิดดูเมื่อสะดุด</h2>
<div class="tw"><table>
<tr><th class="nw">คำ</th><th>ความหมาย</th><th class="nw">อยู่บทไหน</th></tr>
{block(tier2)}
</table></div>

<div class="bx ba"><div class="bt">📖 หมายเหตุ</div>
<p>หน้านี้สร้างด้วย <code>tools/nq_glossary.py</code> · ถ้าแก้กล่องศัพท์ในบทใด ให้รันสคริปต์ใหม่
เพื่อให้ภาคผนวกตรงกับบทเสมอ</p></div>
'''
    return head + body + script


if __name__ == "__main__":
    rows = collect()
    target = os.path.join(DOCS, "nq-appendix-glossary.html")
    with open(target, "w") as fh:
        fh.write(render(rows))
    print(f"เขียน docs/nq-appendix-glossary.html · {len(rows)} คำ "
          f"(ชั้น 1: {sum(1 for r in rows if r[1]==1)} · ชั้น 2: {sum(1 for r in rows if r[1]==2)})")
