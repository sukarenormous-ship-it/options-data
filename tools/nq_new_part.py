#!/usr/bin/env python3
"""สร้างไฟล์บทใหม่ของ "คิดแบบ Quant" จากเปลือกของบทที่มีอยู่แล้ว

ทุกบทต้องมี CSS · palette · reading-path banner · Thai line-break script ชุดเดียวกันเป๊ะ
สคริปต์นี้คัดเปลือกจาก docs/nq-part1.html แล้วใส่หัวเรื่องใหม่ให้ เพื่อไม่ให้เกิด
ความต่างเล็ก ๆ สะสมข้ามบท (และห้ามแก้ Thai line-break script ด้วยมือตามกฎ style guide)

    python3 tools/nq_new_part.py part2 "หัวข้อรอง" "คำโปรย" > /tmp/skeleton.html
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "docs", "nq-part1.html")
BODY_MARK = "<!--BODY-->"


def skeleton(slug, sub, desc, title_suffix):
    with open(SOURCE) as fh:
        html = fh.read()

    head = html[:html.index("<body>") + len("<body>")]
    head = re.sub(r"<title>.*?</title>", f"<title>คิดแบบ Quant — {title_suffix}</title>", head, count=1)

    script = html[html.rindex("<!-- ═══════════════ Thai line-break script"):]

    cover = f'''

<!-- ═══════════════ COVER ═══════════════ -->
<div class="cover">
<h1>คิดแบบ Quant</h1>
<div class="sub">{sub}</div>
<div class="desc">{desc}</div>
</div>

{BODY_MARK}

'''
    return head + cover + script


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    sys.stdout.write(skeleton(*sys.argv[1:]))
