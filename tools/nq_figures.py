#!/usr/bin/env python3
"""สร้าง docs/nq-figures.json — ตัวเลขทุกตัวที่หนังสือ "คิดแบบ Quant" ใช้

กฎเหล็กข้อ 5 ของแผน: ห้ามพิมพ์ตัวเลขลอย ๆ ลงในบท ทุกตัวเลขต้องมาจากไฟล์นี้
และไฟล์นี้ต้องคำนวณจากข้อมูลจริงใน data/ ได้ซ้ำเสมอ

    python3 tools/nq_figures.py            # เขียนทับ docs/nq-figures.json
    python3 tools/nq_figures.py --check    # เทียบกับไฟล์เดิม ไม่เขียน (ใช้ใน CI)
"""

import csv
import glob
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "nq-figures.json")

# ── บัญชีของ "มิน" (golden thread) ────────────────────────────────────────────
# ตัวเลขสมมติที่ประกาศตรง ๆ ว่าสมมติ — ทุกบทต้องใช้ชุดนี้ ห้ามเปลี่ยนกลางเล่ม
MIN_ACCOUNT = {
    "ทุนเริ่มต้นบาท": 50000,
    "ค่าธรรมเนียมต่อข้างเปอร์เซ็นต์": 0.1,   # taker ทั่วไปของ exchange คริปโตรายย่อย
    "ระบบเดิม": "EMA 12/26 ตัดกัน + RSI 30/70",
}


def _daily_btc_prices():
    """ราคา BTC รายวันจากสแนปช็อต Deribit — median ของ underlying_price ในไฟล์วันนั้น"""
    prices = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "deribit", "*", "*", "*.csv"))):
        day = os.path.basename(path)[:-4]
        vals = []
        with open(path) as fh:
            for row in csv.DictReader(fh):
                if row["underlying"] == "BTC" and row["underlying_price"]:
                    vals.append(float(row["underlying_price"]))
        if vals:
            prices[day] = round(statistics.median(vals), 2)
    return prices


def _streak_study(prices):
    """ฐาน (base rate) ของ "ขึ้น 3 วันติด" และสิ่งที่เกิดขึ้นในวันถัดไป"""
    days = sorted(prices)
    px = [prices[d] for d in days]
    rets = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]
    up = [r > 0 for r in rets]

    windows = len(up) - 2                       # จำนวนวันที่ "มองย้อนหลัง 3 วัน" ได้
    hits = [i for i in range(2, len(up)) if up[i] and up[i - 1] and up[i - 2]]
    # วันถัดจากวันที่ครบ 3 วันติด (ตัดกรณีที่ไม่มีวันถัดไปในข้อมูล)
    nxt = [rets[i + 1] for i in hits if i + 1 < len(rets)]

    return {
        "ช่วงข้อมูล": {"ตั้งแต่": days[0], "ถึง": days[-1], "จำนวนวัน": len(days)},
        "ราคาเริ่ม": px[0],
        "ราคาจบ": px[-1],
        "จำนวนวันที่มีผลตอบแทน": len(rets),
        "วันที่ขึ้น": sum(up),
        "สัดส่วนวันที่ขึ้นเปอร์เซ็นต์": round(100 * sum(up) / len(up), 1),
        "ผลตอบแทนเฉลี่ยต่อวันเปอร์เซ็นต์": round(100 * statistics.mean(rets), 3),
        "ส่วนเบี่ยงเบนต่อวันเปอร์เซ็นต์": round(100 * statistics.pstdev(rets), 2),
        "วันแย่สุดเปอร์เซ็นต์": round(100 * min(rets), 2),
        "วันดีสุดเปอร์เซ็นต์": round(100 * max(rets), 2),
        "ขึ้น3วันติด": {
            "จำนวนครั้ง": len(hits),
            "จากทั้งหมด": windows,
            "สัดส่วนเปอร์เซ็นต์": round(100 * len(hits) / windows, 1),
        },
        "วันถัดจากขึ้น3วันติด": {
            "จำนวนตัวอย่าง": len(nxt),
            "วันที่ขึ้น": sum(1 for r in nxt if r > 0),
            "สัดส่วนที่ขึ้นเปอร์เซ็นต์": round(100 * sum(1 for r in nxt if r > 0) / len(nxt), 1),
            # ความเปราะของข้อสรุป: ถ้าผลพลิกไปหนึ่งครั้ง ตัวเลขขยับไปเท่าไร
            "ถ้าพลิกหนึ่งครั้งเปอร์เซ็นต์": round(100 * (sum(1 for r in nxt if r > 0) + 1) / len(nxt), 1),
        },
    }


def _spread_study(day="2026-08-29", expiry="2026-09-25", moneyness=0.05):
    """ต้นทุนจริง: bid/ask ของ option ใกล้ ATM ในสแนปช็อตวันหนึ่ง"""
    path = os.path.join(ROOT, "data", "deribit", day[:4], day[5:7], day + ".csv")
    quotes = []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            if row["underlying"] != "BTC" or row["expiry"] != expiry:
                continue
            try:
                bid, ask = float(row["bid"]), float(row["ask"])
                spot, strike = float(row["underlying_price"]), float(row["strike"])
            except ValueError:
                continue
            if bid <= 0 or ask <= 0 or abs(strike / spot - 1) > moneyness:
                continue
            quotes.append({
                "สัญญา": row["instrument"],
                "ส่วนต่างเปอร์เซ็นต์": round(100 * (ask - bid) / ((ask + bid) / 2), 1),
                "bidดอลลาร์": round(bid * spot),
                "askดอลลาร์": round(ask * spot),
            })
    quotes.sort(key=lambda q: q["ส่วนต่างเปอร์เซ็นต์"])
    return {
        "วันที่": day,
        "หมดอายุ": expiry,
        "จำนวนสัญญาที่นับ": len(quotes),
        "ส่วนต่างกลางเปอร์เซ็นต์": round(statistics.median(q["ส่วนต่างเปอร์เซ็นต์"] for q in quotes), 1),
        "สัญญาที่แคบสุด": quotes[0],
        "สัญญาที่กว้างสุด": quotes[-1],
    }


def build():
    prices = _daily_btc_prices()
    streaks = _streak_study(prices)
    fee = MIN_ACCOUNT["ค่าธรรมเนียมต่อข้างเปอร์เซ็นต์"]
    return {
        "_อ่านก่อน": "สร้างด้วย tools/nq_figures.py — ห้ามแก้ด้วยมือ",
        "มิน": {
            **MIN_ACCOUNT,
            "ค่าธรรมเนียมต่อรอบเปอร์เซ็นต์": round(2 * fee, 2),
            # เสมอตัวเมื่อกำไรเท่าขาดทุน: p·g = (1−p)·g + ต้นทุน  →  p = 0.5 + ต้นทุน/(2g)
            "อัตราชนะขั้นต่ำที่กำไรเป้า2เปอร์เซ็นต์": round(50 + (2 * fee) / (2 * 2.0) * 100, 1),
        },
        "btc": streaks,
        "ต้นทุนจริง": _spread_study(),
    }


if __name__ == "__main__":
    data = build()
    if "--check" in sys.argv:
        with open(OUT) as fh:
            old = json.load(fh)
        if old != data:
            print("nq-figures.json ไม่ตรงกับข้อมูลปัจจุบัน — รัน tools/nq_figures.py ใหม่")
            sys.exit(1)
        print("nq-figures.json ตรงกับข้อมูล ✓")
    else:
        with open(OUT, "w") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("เขียน", os.path.relpath(OUT, ROOT))
