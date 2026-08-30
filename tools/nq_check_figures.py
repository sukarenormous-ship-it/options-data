#!/usr/bin/env python3
"""ตรวจว่าตัวเลขในบท docs/nq-*.html ตรงกับ docs/nq-figures.json

กันจุดอ่อน W7 ของแผน: เล่มเดิมเจอตัวเลขขัดกันเอง 40-50 จุด เพราะพิมพ์เลขด้วยมือคนละที่
ตัวตรวจนี้ทำสองอย่าง
  1. ยืนยันว่าตัวเลขสำคัญทุกตัวใน figures.json ปรากฏในบทอย่างน้อยหนึ่งครั้ง (ไม่ได้พิมพ์เพี้ยน)
  2. เตือนเมื่อบทมีตัวเลขที่ "หน้าตาเหมือนสถิติ" แต่ไม่มีใน figures.json (อาจเป็นเลขที่แต่งขึ้น)

    python3 tools/nq_check_figures.py
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "docs", "nq-figures.json")

# ตัวเลขที่ต้องปรากฏในเล่ม พร้อมวิธีอ่านค่าจาก figures.json
REQUIRED = {
    "ฐานวันที่ขึ้น": lambda f: f["btc"]["สัดส่วนวันที่ขึ้นเปอร์เซ็นต์"],
    "ขึ้น3วันติดสัดส่วน": lambda f: f["btc"]["ขึ้น3วันติด"]["สัดส่วนเปอร์เซ็นต์"],
    "วันถัดไปขึ้น": lambda f: f["btc"]["วันถัดจากขึ้น3วันติด"]["สัดส่วนที่ขึ้นเปอร์เซ็นต์"],
    "จำนวนวัน": lambda f: f["btc"]["ช่วงข้อมูล"]["จำนวนวัน"],
    "ค่าธรรมเนียมต่อรอบ": lambda f: f["มิน"]["ค่าธรรมเนียมต่อรอบเปอร์เซ็นต์"],
    "เส้นเสมอตัว": lambda f: f["มิน"]["อัตราชนะขั้นต่ำที่กำไรเป้า2เปอร์เซ็นต์"],
    "ส่วนต่างแคบสุด": lambda f: f["ต้นทุนจริง"]["สัญญาที่แคบสุด"]["ส่วนต่างเปอร์เซ็นต์"],
    "ส่วนต่างกลาง": lambda f: f["ต้นทุนจริง"]["ส่วนต่างกลางเปอร์เซ็นต์"],
    "ส่วนต่างกว้างสุด": lambda f: f["ต้นทุนจริง"]["สัญญาที่กว้างสุด"]["ส่วนต่างเปอร์เซ็นต์"],
    # Part 1
    "ความสุ่มเฉลี่ย": lambda f: f["ความสุ่ม"]["เฉลี่ยจากความสุ่ม"],
    "เปอร์เซ็นไทล์ค่าจริง": lambda f: f["ความสุ่ม"]["เปอร์เซ็นไทล์ของค่าจริง"],
    "พิสูจน์ได้ที่ร้อยไม้": lambda f: f["ขนาดตัวอย่าง"]["มีEdgeจริง"]["100"],
    "พิสูจน์ได้ที่พันไม้": lambda f: f["ขนาดตัวอย่าง"]["มีEdgeจริง"]["1000"],
    "ดาวเด่นรอบแรก": lambda f: f["ดาวเด่น"]["ดาวเด่นชนะเฉลี่ยรอบแรก"],
    "สัดส่วนที่รอด": lambda f: f["ผู้รอดชีวิต"]["สัดส่วนที่รอดเปอร์เซ็นต์"],
    "ผลบวกแล้วเป็นจริง": lambda f: f["เงื่อนไข"]["ผลบวกแล้วเป็นโรคจริงเปอร์เซ็นต์"],
    "ปีที่ต้องใช้": lambda f: f["มิน"]["ปีที่ต้องใช้เพื่อครบพันไม้"],
}


def _texts():
    out = {}
    docs = os.path.join(ROOT, "docs")
    for name in sorted(os.listdir(docs)):
        if name.startswith("nq-") and name.endswith(".html"):
            with open(os.path.join(docs, name)) as fh:
                out[name] = fh.read()
    return out


def main():
    with open(FIG) as fh:
        fig = json.load(fh)
    docs = _texts()
    if not docs:
        print("ยังไม่มีไฟล์ docs/nq-*.html ให้ตรวจ")
        return 0

    blob = "\n".join(docs.values())
    problems = []

    for label, get in REQUIRED.items():
        want = get(fig)
        # ยอมรับทั้ง "58.9" และ "58.9%" — แต่ต้องเป็นตัวเลขเดียวกันเป๊ะ
        if not re.search(r"(?<![\d.])" + re.escape(str(want)) + r"(?![\d])", blob):
            problems.append(f"ไม่พบค่า {label} = {want} ในบทใด ๆ")

    # เลขที่หน้าตาเป็นเปอร์เซ็นต์ในบท แต่ไม่มีใน figures.json
    known = set()
    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)):
            known.add(str(o))
            known.add(str(abs(o)))   # ในบทอาจเขียน "−1.85%" ขณะที่แหล่งเก็บเป็น -1.85
    walk(fig)
    # ตัวเลขที่อธิบายได้เองในบท (คณิตพื้นฐาน/ค่าคงที่ที่ไม่ใช่สถิติจากข้อมูล)
    allowed = {"50", "100", "2", "3", "1", "0", "8", "12", "26", "62", "5", "1.8", "0.5"}
    for name, html in docs.items():
        body = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S)
        body = re.sub(r"<[^>]+>", " ", body)
        for m in re.finditer(r"(\d+\.\d+)\s*%", body):
            v = m.group(1)
            if v not in known and v not in allowed:
                problems.append(f"{name}: พบ {v}% ที่ไม่มีใน nq-figures.json — อาจเป็นเลขที่แต่งขึ้น")

    if problems:
        print("พบปัญหา", len(problems), "ข้อ")
        for p in problems:
            print("  -", p)
        return 1
    print(f"ตรวจ {len(docs)} ไฟล์ · ตัวเลขบังคับ {len(REQUIRED)} ค่า · ตรงกับ nq-figures.json ทั้งหมด ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
