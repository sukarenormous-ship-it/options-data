#!/usr/bin/env python3
"""สร้าง docs/nq-figures.json — ตัวเลขทุกตัวที่หนังสือ "คิดแบบ Quant" ใช้

กฎเหล็กข้อ 5 ของแผน: ห้ามพิมพ์ตัวเลขลอย ๆ ลงในบท ทุกตัวเลขต้องมาจากไฟล์นี้
และไฟล์นี้ต้องคำนวณจากข้อมูลจริงใน data/ ได้ซ้ำเสมอ

    python3 tools/nq_figures.py            # เขียนทับ docs/nq-figures.json
    python3 tools/nq_figures.py --check    # เทียบกับไฟล์เดิม ไม่เขียน (ใช้ใน CI)
"""

import csv
import glob
import random
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
    "ไม้ต่อสัปดาห์": 2,
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


# ── Part 1: ตัวเลขจากการจำลอง ────────────────────────────────────────────────
# ทุกฟังก์ชันตรึงเมล็ดสุ่มไว้ ผลจึงสร้างซ้ำได้เหมือนเดิมทุกครั้ง
# (ตรวจแล้วว่าค่าที่รายงานนิ่งข้ามเมล็ด ไม่ใช่ผลของเมล็ดใดเมล็ดหนึ่ง)
SEED = 20260830


def _runs_of_three(seq):
    return sum(1 for i in range(2, len(seq)) if seq[i] and seq[i - 1] and seq[i - 2])


def _randomness_study(streaks, rounds=100000):
    """เหรียญที่ออกหัวเท่ากับสัดส่วนวันที่ราคาขึ้นจริง จะสร้าง "ขึ้น 3 วันติด" กี่ครั้ง"""
    n_days = streaks["จำนวนวันที่มีผลตอบแทน"]
    p_up = streaks["วันที่ขึ้น"] / n_days
    random.seed(SEED)
    vals = sorted(_runs_of_three([random.random() < p_up for _ in range(n_days)])
                  for _ in range(rounds))
    observed = streaks["ขึ้น3วันติด"]["จำนวนครั้ง"]
    return {
        "คำอธิบาย": "จำลองเหรียญที่ออกหัวเท่าสัดส่วนวันขึ้นจริง แล้วนับ 'ขึ้น 3 วันติด'",
        "จำนวนรอบจำลอง": rounds,
        "เฉลี่ยจากความสุ่ม": round(statistics.mean(vals), 1),
        "ช่วง90เปอร์เซ็นต์": [vals[rounds // 20], vals[rounds - rounds // 20 - 1]],
        "ของจริง": observed,
        "เปอร์เซ็นไทล์ของค่าจริง": round(100 * sum(1 for v in vals if v <= observed) / rounds),
        # การกระจายเต็ม (ใช้วาดกราฟในบท) — คีย์คือจำนวนครั้ง ค่าคือสัดส่วนเปอร์เซ็นต์
        "การกระจาย": {str(k): round(100 * vals.count(k) / rounds, 2)
                       for k in range(0, max(vals) + 1) if vals.count(k) / rounds >= 0.001},
    }


def _sample_size_study(edge=0.55, trials=20000):
    """ถ้ามี edge จริง 55% ต้องเทรดกี่ไม้ถึงจะ *พิสูจน์* ได้ว่าไม่ใช่ดวง"""
    def rate(true_p, n):
        random.seed(SEED + n)
        hit = 0
        for _ in range(trials):
            wins = sum(1 for _ in range(n) if random.random() < true_p)
            # เกณฑ์: ชนะเกินครึ่งอย่างน้อย 2 เท่าของความคลาดเคลื่อนมาตรฐาน
            if wins / n - 0.5 >= 2 * (0.25 / n) ** 0.5:
                hit += 1
        return round(100 * hit / trials, 1)

    sizes = [20, 100, 300, 1000, 2000]
    return {
        "คำอธิบาย": f"โอกาสที่คนซึ่งมี edge จริง {edge:.0%} จะแสดงหลักฐานได้ว่าตัวเองไม่ได้ฟลุก",
        "จำนวนรอบจำลอง": trials,
        "มีEdgeจริง": {str(n): rate(edge, n) for n in sizes},
        "ไม่มีEdgeเลย": {str(n): rate(0.50, n) for n in (20, 100, 1000)},
    }


def _star_trader_study(traders=2000, per_period=20, top=100):
    """เทรดเดอร์ฝีมือเท่ากันหมด — ดาวเด่นของรอบแรกทำผลงานรอบสองยังไง"""
    random.seed(SEED + 7)
    p1 = [sum(1 for _ in range(per_period) if random.random() < 0.5) for _ in range(traders)]
    p2 = [sum(1 for _ in range(per_period) if random.random() < 0.5) for _ in range(traders)]
    stars = sorted(range(traders), key=lambda i: -p1[i])[:top]
    return {
        "คำอธิบาย": "เทรดเดอร์ทุกคนฝีมือเท่ากันเป๊ะ (โอกาสชนะ 50%) ผลต่างมาจากดวงล้วน",
        "จำนวนเทรดเดอร์": traders,
        "ไม้ต่อรอบ": per_period,
        "จำนวนดาวเด่นที่คัด": top,
        "ดาวเด่นชนะเฉลี่ยรอบแรก": round(statistics.mean(p1[i] for i in stars), 1),
        "ดาวเด่นชนะเฉลี่ยรอบสอง": round(statistics.mean(p2[i] for i in stars), 1),
        "ทุกคนชนะเฉลี่ย": round(statistics.mean(p1), 1),
    }


def _survivorship_study(prices):
    """สัญญาที่มีอยู่วันแรก เหลืออยู่ถึงวันสุดท้ายกี่ตัว"""
    days = sorted(prices)

    def names(day):
        path = os.path.join(ROOT, "data", "deribit", day[:4], day[5:7], day + ".csv")
        with open(path) as fh:
            return {r["instrument"] for r in csv.DictReader(fh) if r["underlying"] == "BTC"}

    first, last = names(days[0]), names(days[-1])
    stay = first & last
    return {
        "คำอธิบาย": "สัญญา BTC ที่ยังอยู่ทั้งวันแรกและวันสุดท้ายของช่วงข้อมูล",
        "วันแรก": days[0],
        "วันสุดท้าย": days[-1],
        "จำนวนวันแรก": len(first),
        "จำนวนวันสุดท้าย": len(last),
        "อยู่ครบทั้งสองวัน": len(stay),
        "สัดส่วนที่รอดเปอร์เซ็นต์": round(100 * len(stay) / len(first)),
    }


def _conditional_study(prevalence=0.01, sensitivity=0.99, false_positive=0.05):
    """กับดักความน่าจะเป็นแบบมีเงื่อนไข — เลขสมมติ แต่เลขคณิตตรวจได้เอง"""
    true_pos = prevalence * sensitivity
    false_pos = (1 - prevalence) * false_positive
    return {
        "คำอธิบาย": "ตัวอย่างสมมติเรื่องการตรวจโรค ใช้สอนว่า 'แม่น 99%' ไม่ได้แปลว่าเชื่อได้ 99%",
        "อัตราการเป็นโรคเปอร์เซ็นต์": round(100 * prevalence, 1),
        "ความไวของชุดตรวจเปอร์เซ็นต์": round(100 * sensitivity),
        "อัตราผลบวกลวงเปอร์เซ็นต์": round(100 * false_positive),
        "ต่อคนหนึ่งหมื่นคน": {
            "เป็นโรคจริงและตรวจเจอ": round(10000 * true_pos),
            "ไม่ได้เป็นแต่ตรวจว่าเป็น": round(10000 * false_pos),
        },
        "ผลบวกแล้วเป็นโรคจริงเปอร์เซ็นต์": round(100 * true_pos / (true_pos + false_pos), 1),
    }


# ── Part 2-3: อินดิเคเตอร์บนข้อมูลจริง ───────────────────────────────────────
def _ema(vals, n):
    k = 2 / (n + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _indicator_study(prices, fast=12, slow=26, fee=0.001):
    """เดินตามสัญญาณ EMA ตัดกันบนข้อมูลจริง เทียบกับการถือเฉย ๆ

    ตัด `slow` วันแรกทิ้งเป็นช่วงอุ่นเครื่อง เพราะค่า EMA ช่วงต้นยังไม่นิ่ง
    ผลที่ได้มาจากไม้เพียงไม่กี่ไม้ จึงใช้เป็น *ภาพประกอบกลไก* ไม่ใช่หลักฐานทางสถิติ
    """
    days = sorted(prices)
    px = [prices[d] for d in days]
    ef, es = _ema(px, fast), _ema(px, slow)

    signals = []
    for i in range(slow, len(px)):
        if ef[i - 1] <= es[i - 1] and ef[i] > es[i]:
            signals.append((i, "ซื้อ"))
        elif ef[i - 1] >= es[i - 1] and ef[i] < es[i]:
            signals.append((i, "ขาย"))

    def walk(cost):
        cash, units, entry, trades = 1.0, 0.0, None, []
        for i, side in signals:
            if side == "ซื้อ" and units == 0:
                units, cash, entry = cash * (1 - cost) / px[i], 0.0, i
            elif side == "ขาย" and units > 0:
                cash, units = units * px[i] * (1 - cost), 0.0
                trades.append((entry, i))
                entry = None
        if units > 0:
            cash = units * px[-1] * (1 - cost)
            trades.append((entry, len(px) - 1))
        return cash - 1, trades

    net, trades = walk(fee)
    gross, _ = walk(0.0)
    hold = px[-1] / px[slow] - 1

    return {
        "คำอธิบาย": f"เดินตาม EMA {fast}/{slow} ตัดกันบนราคาจริง หักค่าธรรมเนียม {fee:.1%} ต่อข้าง",
        "เตือน": "มาจากไม้เพียงไม่กี่ไม้ — ใช้ดูกลไก ไม่ใช่หลักฐานว่าระบบดีหรือแย่",
        "ช่วงที่ใช้": {"ตั้งแต่": days[slow], "ถึง": days[-1], "จำนวนวัน": len(px) - slow},
        "จำนวนสัญญาณ": len(signals),
        "สัญญาณ": [{"วันที่": days[i], "สัญญาณ": side, "ราคา": round(px[i])} for i, side in signals],
        "จำนวนไม้": len(trades),
        "ไม้": [{"เข้า": days[a], "ราคาเข้า": round(px[a]),
                 "ออก": days[b], "ราคาออก": round(px[b]),
                 "ผลเปอร์เซ็นต์": round(100 * (px[b] / px[a] - 1), 2)} for a, b in trades],
        "ผลระบบเปอร์เซ็นต์": round(100 * net, 2),
        "ผลระบบไม่มีค่าธรรมเนียมเปอร์เซ็นต์": round(100 * gross, 2),
        "ผลถือเฉยเปอร์เซ็นต์": round(100 * hold, 2),
        "ตามหลังอยู่จุดเปอร์เซ็นต์": round(100 * (hold - net), 1),
        "ส่วนที่เสียไปกับค่าธรรมเนียมจุดเปอร์เซ็นต์": round(100 * (gross - net), 2),
    }


def _claim_study(prices, start="2026-08-20", level=72000):
    """ข้อความที่ผิดได้ ตรวจได้จริงจากข้อมูล — ใช้เป็นตัวอย่างเดินเรื่องใน Part 2"""
    days = sorted(prices)
    i = days.index(start)
    path = [(d, prices[d]) for d in days[i:]]
    hit = next((d for d, v in path if v >= level), None)
    lowest = min(v for _, v in path)
    return {
        "วันตั้งข้อความ": start,
        "ราคาวันตั้ง": round(prices[start]),
        "เส้นระดับ": level,
        "วันที่แตะระดับ": hit,
        "จำนวนวันที่ใช้": days.index(hit) - i if hit else None,
        "ราคาสูงสุดในช่วง": round(max(v for _, v in path)),
        "ราคาต่ำสุดในช่วง": round(lowest),
        "ย่อลึกสุดจากจุดตั้งเปอร์เซ็นต์": round(100 * (lowest / prices[start] - 1), 2),
        "ราคาวันสุดท้าย": round(path[-1][1]),
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
            "ไม้ต่อปี": MIN_ACCOUNT["ไม้ต่อสัปดาห์"] * 52,
            # ต้องเทรดกี่ปีถึงจะสะสมครบ 1,000 ไม้ ซึ่งเป็นจุดที่พิสูจน์ edge ได้ (ดู "ขนาดตัวอย่าง")
            "ปีที่ต้องใช้เพื่อครบพันไม้": round(1000 / (MIN_ACCOUNT["ไม้ต่อสัปดาห์"] * 52), 1),
        },
        "btc": streaks,
        "ต้นทุนจริง": _spread_study(),
        "ความสุ่ม": _randomness_study(streaks),
        "ขนาดตัวอย่าง": _sample_size_study(),
        "ดาวเด่น": _star_trader_study(),
        "ผู้รอดชีวิต": _survivorship_study(prices),
        "เงื่อนไข": _conditional_study(),
        "อินดิเคเตอร์": _indicator_study(prices),
        "ข้อความ": _claim_study(prices),
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
