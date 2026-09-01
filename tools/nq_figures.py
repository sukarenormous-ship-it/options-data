#!/usr/bin/env python3
"""สร้าง docs/nq-figures.json — ตัวเลขทุกตัวที่หนังสือ "คิดแบบ Quant" ใช้

กฎเหล็กข้อ 5 ของแผน: ห้ามพิมพ์ตัวเลขลอย ๆ ลงในบท ทุกตัวเลขต้องมาจากไฟล์นี้
และไฟล์นี้ต้องคำนวณจากข้อมูลจริงใน data/ ได้ซ้ำเสมอ

    python3 tools/nq_figures.py            # เขียนทับ docs/nq-figures.json
    python3 tools/nq_figures.py --check    # เทียบกับไฟล์เดิม ไม่เขียน (ใช้ใน CI)
"""

import csv
import datetime
import glob
import math
import random
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "nq-figures.json")
# ที่อยู่ของสแนปช็อตดิบ (data/deribit/, data/okx/) — ค่าเริ่มต้นมองหาข้าง ๆ repo นี้
# เพราะไฟล์เหล่านี้อาจถูกย้ายไปอยู่คนละ repo กับข้อมูลดิบ (repo หนังสือ vs repo ข้อมูล)
# แก้ได้ด้วย --data-dir หรือตัวแปรแวดล้อม NQ_DATA_DIR โดยไม่ต้องแก้โค้ด
DATA_DIR = os.environ.get(
    "NQ_DATA_DIR",
    os.path.join(ROOT, "data") if os.path.isdir(os.path.join(ROOT, "data"))
    else os.path.join(ROOT, "..", "options-data", "data"),
)

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
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "deribit", "*", "*", "*.csv"))):
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
    path = os.path.join(DATA_DIR, "deribit", day[:4], day[5:7], day + ".csv")
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
        path = os.path.join(DATA_DIR, "deribit", day[:4], day[5:7], day + ".csv")
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


# ── Part 4: การกระจายและหาง ─────────────────────────────────────────────────
def _distribution_study(prices):
    """หน้าตาจริงของผลตอบแทนรายวัน — ค่ากลาง ความกว้าง และหาง"""
    days = sorted(prices)
    px = [prices[d] for d in days]
    r = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]
    n = len(r)
    sd = statistics.pstdev(r)
    arith = statistics.mean(r)
    geo = (px[-1] / px[0]) ** (1 / n) - 1
    best, worst = max(r), min(r)

    # ความถี่ที่คาดหวังของวันแรงที่สุด ถ้าโลกเป็นการแจกแจงปกติ
    z = best / sd
    p_tail = 0.5 * math.erfc(z / math.sqrt(2))

    # ฮิสโทแกรมช่องละ 1%
    bins = {}
    for x in r:
        k = math.floor(x * 100)
        bins[k] = bins.get(k, 0) + 1

    return {
        "จำนวนวัน": n,
        "ผลรวมทั้งช่วงเปอร์เซ็นต์": round(100 * (px[-1] / px[0] - 1), 2),
        "เฉลี่ยเลขคณิตต่อวันเปอร์เซ็นต์": round(100 * arith, 3),
        "เฉลี่ยเชิงเรขาคณิตต่อวันเปอร์เซ็นต์": round(100 * geo, 3),
        "ช่องว่างต่อวันจุดเปอร์เซ็นต์": round(100 * (arith - geo), 3),
        "ครึ่งหนึ่งของความแปรปรวนจุดเปอร์เซ็นต์": round(100 * sd * sd / 2, 3),
        "ส่วนเบี่ยงเบนต่อวันเปอร์เซ็นต์": round(100 * sd, 2),
        "วันดีสุด": {"เปอร์เซ็นต์": round(100 * best, 2), "กี่เท่าของสวนเบี่ยงเบน": round(z, 2)},
        "วันแย่สุด": {"เปอร์เซ็นต์": round(100 * worst, 2), "กี่เท่าของสวนเบี่ยงเบน": round(worst / sd, 2)},
        "ถ้าโลกเป็นการแจกแจงปกติ": {
            "วันแรงขนาดนี้ควรเกิดทุกกี่วัน": round(1 / p_tail),
            "คิดเป็นกี่ปี": round(1 / p_tail / 365),
        },
        "วันที่ขยับเกินสองเท่าของส่วนเบี่ยงเบน": sum(1 for x in r if abs(x) > 2 * sd),
        "ฮิสโทแกรมช่องละหนึ่งเปอร์เซ็นต์": {str(k): v for k, v in sorted(bins.items())},
    }


def _path_study(prices, stop=0.08, rounds=20000):
    """ลำดับสำคัญไหม — ตอบสองชั้น: ไม่สำคัญถ้าถือเฉย ๆ แต่สำคัญมากทันทีที่มีกฎ"""
    days = sorted(prices)
    px = [prices[d] for d in days]
    r = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]

    def run(seq, use_stop):
        v, peak = 1.0, 1.0
        for x in seq:
            v *= 1 + x
            peak = max(peak, v)
            if use_stop and v / peak - 1 <= -stop:
                return v - 1, True
        return v - 1, False

    random.seed(SEED + 11)
    finals, stopped = [], 0
    plain = set()
    for _ in range(rounds):
        q = r[:]
        random.shuffle(q)
        plain.add(round(run(q, False)[0], 9))
        val, hit = run(q, True)
        finals.append(val)
        stopped += hit
    finals.sort()
    actual, actual_stop = run(r, True)

    return {
        "คำอธิบาย": f"สลับลำดับผลตอบแทนชุดเดิม {rounds:,} แบบ",
        "ถือเฉยๆผลต่างกันกี่ค่า": len(plain),
        "ผลถือเฉยๆเปอร์เซ็นต์": round(100 * (px[-1] / px[0] - 1), 2),
        "กฎตัดขาดทุนที่": round(100 * stop),
        "โดนตัดขาดทุนกี่เปอร์เซ็นต์ของลำดับ": round(100 * stopped / rounds, 1),
        "ผลแย่สุดเปอร์เซ็นต์": round(100 * finals[0], 1),
        "ผลกลางเปอร์เซ็นต์": round(100 * finals[rounds // 2], 1),
        "ผลดีสุดเปอร์เซ็นต์": round(100 * finals[-1], 1),
        "ลำดับจริงเปอร์เซ็นต์": round(100 * actual, 1),
        "ลำดับจริงโดนตัดไหม": actual_stop,
    }


# ── Part 5: ต้นทุนและอีกฝั่งของดีล ──────────────────────────────────────────
def _cost_study(day="2026-08-29", band=0.05):
    """ส่วนต่างราคาซื้อ-ขายจริง แยกตามอายุคงเหลือ และเทียบข้ามตลาด

    นับเฉพาะสัญญาที่มีทั้งราคาเสนอซื้อและเสนอขาย และอยู่ใกล้ราคาปัจจุบันภายใน band
    ตัวเลขข้ามตลาดเทียบกันแบบหยาบ ๆ เท่านั้น เพราะสเปกสัญญาและเวลาสแนปช็อตไม่ตรงกันเป๊ะ
    """
    y0, m0, d0 = map(int, day.split("-"))
    today = datetime.date(y0, m0, d0)
    buckets = [("0-2 วัน", 2), ("3-7 วัน", 7), ("8-30 วัน", 30),
               ("31-120 วัน", 120), ("เกิน 120 วัน", 10**6)]

    result = {"วันที่": day, "นับเฉพาะสัญญาใกล้ราคาปัจจุบันภายในเปอร์เซ็นต์": round(100 * band), "ตลาด": {}}
    for venue in ("deribit", "okx"):
        path = os.path.join(DATA_DIR, venue, day[:4], day[5:7], day + ".csv")
        if not os.path.exists(path):
            continue
        groups = {name: [] for name, _ in buckets}
        no_bid = total = 0
        with open(path) as fh:
            for row in csv.DictReader(fh):
                if row["underlying"] != "BTC":
                    continue
                total += 1
                try:
                    bid, ask = float(row["bid"] or 0), float(row["ask"] or 0)
                    spot, strike = float(row["underlying_price"]), float(row["strike"])
                except ValueError:
                    continue
                if bid <= 0:
                    no_bid += 1
                    continue
                if ask <= 0 or abs(strike / spot - 1) > band:
                    continue
                ey, em, ed = map(int, row["expiry"].split("-"))
                dte = (datetime.date(ey, em, ed) - today).days
                for name, cap in buckets:
                    if dte <= cap:
                        groups[name].append(100 * (ask - bid) / ((ask + bid) / 2))
                        break
        result["ตลาด"][venue] = {
            "ตามอายุคงเหลือ": {name: {"จำนวนสัญญา": len(v), "ส่วนต่างกลางเปอร์เซ็นต์": round(statistics.median(v), 1)}
                                for name, v in groups.items() if v},
            "สัญญาที่ไม่มีราคาเสนอซื้อ": no_bid,
            "สัญญาทั้งหมด": total,
            "สัดส่วนที่ขายออกไม่ได้เปอร์เซ็นต์": round(100 * no_bid / total) if total else None,
        }
    return result


# ── Part 6: ความเชื่อเดียวกัน สามรูปทรง ─────────────────────────────────────
def _structure_study(prices, day="2026-08-29", expiry="2026-09-25", buy_k=80000, sell_k=86000):
    """สร้างสามโครงสร้างจากราคาจริงในกระดาน เพื่อเทียบ "รูป" ของการจ่ายผล

    ใช้ราคาที่ผู้ซื้อรายย่อยได้จริง — จ่ายราคาเสนอขายเวลาซื้อ และได้ราคาเสนอซื้อเวลาขาย
    """
    path = os.path.join(DATA_DIR, "deribit", day[:4], day[5:7], day + ".csv")
    spot = prices[day]          # ใช้ค่าเดียวกับ "ราคารายวัน" ทั้งเล่ม
    quotes = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            if row["underlying"] != "BTC" or row["expiry"] != expiry or row["type"] != "call":
                continue
            try:
                bid, ask = float(row["bid"] or 0), float(row["ask"] or 0)
            except ValueError:
                continue
            if bid > 0 and ask > 0:
                quotes[int(float(row["strike"]))] = {"bid": round(bid * spot), "ask": round(ask * spot)}

    long_cost = quotes[buy_k]["ask"]
    short_credit = quotes[sell_k]["bid"]
    net = long_cost - short_credit

    def payoff(final):
        return {
            "ซื้อของจริง": round(final - spot),
            "ซื้อสิทธิ์": round(max(final - buy_k, 0) - long_cost),
            "ซื้อสิทธิ์แบบมีเพดาน": round(min(max(final - buy_k, 0), sell_k - buy_k) - net),
        }

    scenarios = [round(spot * m) for m in (0.90, 1.0, 1.05, 1.10, 1.15, 1.25)]
    return {
        "วันที่": day,
        "หมดอายุ": expiry,
        "จำนวนวันคงเหลือ": 27,
        "ราคาปัจจุบัน": round(spot),
        "ราคาใช้สิทธิ์ที่ซื้อ": buy_k,
        "ราคาใช้สิทธิ์ที่ขาย": sell_k,
        "ราคาที่จ่ายซื้อสิทธิ์": long_cost,
        "ราคาที่ได้จากการขายสิทธิ์": short_credit,
        "ต้นทุนสุทธิแบบมีเพดาน": net,
        "จุดคุ้มทุน": {
            "ซื้อของจริง": round(spot),
            "ซื้อสิทธิ์": buy_k + long_cost,
            "ซื้อสิทธิ์แบบมีเพดาน": buy_k + net,
        },
        "ขาดทุนมากสุด": {
            "ซื้อของจริง": "ได้ถึงศูนย์",
            "ซื้อสิทธิ์": long_cost,
            "ซื้อสิทธิ์แบบมีเพดาน": net,
        },
        "กำไรมากสุด": {
            "ซื้อของจริง": "ไม่จำกัด",
            "ซื้อสิทธิ์": "ไม่จำกัด",
            "ซื้อสิทธิ์แบบมีเพดาน": (sell_k - buy_k) - net,
        },
        "ผลที่ราคาต่าง ๆ": {str(f): payoff(f) for f in scenarios},
    }


# ── Part 7: ขนาดไม้และการอยู่รอด ────────────────────────────────────────────
def _survival_study(prices, horizon=252, rounds=20000):
    """สุ่มผลตอบแทนจริงคืนกลับเพื่อดูว่าขนาดไม้เปลี่ยนโอกาสอยู่รอดยังไง

    ทำสองชุดโดยตั้งใจ
      ก) ใช้ผลตอบแทนจริงทั้งดุ้น ซึ่งมาจากช่วงตลาดขาขึ้น — เป็นชุดที่ *หลอก*
      ข) ตัดค่าเฉลี่ยออก เหลือเฉพาะรูปร่างความผันผวนและหางอ้วน — เป็นชุดที่ใช้ตัดสินใจ
    ความต่างของสองชุดนี้คือบทเรียนหลักของบท ไม่ใช่ผลข้างเคียง
    """
    days = sorted(prices)
    px = [prices[d] for d in days]
    r = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]
    drift = statistics.mean(r)
    flat = [x - drift for x in r]

    def run(source, lev):
        random.seed(SEED + int(lev * 100))
        ends, d30, d50, below = [], 0, 0, 0
        for _ in range(rounds):
            v, peak, h30, h50 = 1.0, 1.0, False, False
            for _ in range(horizon):
                v *= 1 + lev * random.choice(source)
                if v <= 0:
                    v, h30, h50 = 1e-9, True, True
                    break
                peak = max(peak, v)
                dd = v / peak - 1
                h30 = h30 or dd <= -0.30
                h50 = h50 or dd <= -0.50
            ends.append(v - 1)
            d30 += h30
            d50 += h50
            below += v < 1
        ends.sort()
        return {
            "ผลกลางเปอร์เซ็นต์": round(100 * ends[rounds // 2], 1),
            "เคยลึกสามสิบเปอร์เซ็นต์": round(100 * d30 / rounds, 1),
            "เคยลึกห้าสิบเปอร์เซ็นต์": round(100 * d50 / rounds, 1),
            "จบต่ำกว่าทุนเปอร์เซ็นต์": round(100 * below / rounds, 1),
        }

    levs = [0.5, 1, 2, 3]
    return {
        "คำอธิบาย": f"สุ่มผลตอบแทนจริงคืนกลับ {horizon} วันทำการ × {rounds:,} เส้นทาง",
        "แนวโน้มที่ตัดออกต่อวันเปอร์เซ็นต์": round(100 * drift, 3),
        "ใช้ผลตอบแทนจริง": {str(l): run(r, l) for l in levs},
        "ตัดแนวโน้มออก": {str(l): run(flat, l) for l in levs},
    }


def _drawdown_table(levels=(10, 20, 30, 50, 70, 90)):
    """ขาดทุนแล้วต้องได้กี่เปอร์เซ็นต์ถึงกลับที่เดิม"""
    return {str(d): round(100 * (1 / (1 - d / 100) - 1)) for d in levels}


# ── Part 8: การค้นหาสร้างผลงานปลอมได้เท่าไร ─────────────────────────────────
def _ema_series(vals, n):
    k = 2 / (n + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _run_crossover(px, fast, slow, fee=0.001):
    """เดินตามสัญญาณ EMA ตัดกันหนึ่งชุดพารามิเตอร์ คืนผลตอบแทนรวม"""
    ef, es = _ema_series(px, fast), _ema_series(px, slow)
    cash, units = 1.0, 0.0
    for i in range(slow, len(px)):
        up = ef[i - 1] <= es[i - 1] and ef[i] > es[i]
        down = ef[i - 1] >= es[i - 1] and ef[i] < es[i]
        if up and units == 0:
            units, cash = cash * (1 - fee) / px[i], 0.0
        elif down and units > 0:
            cash, units = units * px[i] * (1 - fee), 0.0
    return (cash if units == 0 else units * px[-1] * (1 - fee)) - 1


def _search_study(prices, rounds=200):
    """ค้นหาพารามิเตอร์ที่ดีที่สุด แล้ววัดว่าตัวเลขที่ได้เป็นของจริงเท่าไร

    ทำสองรอบ
      ก) ค้นบนข้อมูลจริง — ได้ "ชุดที่ดีที่สุด" มาหนึ่งชุด
      ข) ค้นแบบเดียวกันบนข้อมูลที่ไม่มีโครงสร้างอะไรเลย หลายรอบ
         เพื่อดูว่าแค่ *การค้นหา* สร้างผลงานปลอมได้เท่าไร
    """
    days = sorted(prices)
    px = [prices[d] for d in days]
    r = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]
    flat = [x - statistics.mean(r) for x in r]
    combos = [(a, b) for a in range(3, 26) for b in range(a + 1, 51)]

    real = sorted(((_run_crossover(px, a, b), a, b) for a, b in combos), reverse=True)
    hold = px[-1] / px[0] - 1
    beat = sum(1 for v, _, _ in real if v > hold)

    random.seed(SEED + 23)
    bests, singles = [], []
    for _ in range(rounds):
        q = flat[:]
        random.shuffle(q)
        path = [px[0]]
        for x in q:
            path.append(path[-1] * (1 + x))
        vals = [_run_crossover(path, a, b) for a, b in combos]
        bests.append(max(vals))
        singles.append(vals[0])
    bests.sort()

    best_noise = bests[rounds // 2]
    single_noise = statistics.median(singles)
    return {
        "คำอธิบาย": f"ค้นหาพารามิเตอร์ {len(combos)} ชุด แล้ววัดว่าการค้นหาสร้างผลงานปลอมได้เท่าไร",
        "จำนวนชุดที่ลอง": len(combos),
        "จำนวนรอบจำลอง": rounds,
        "บนข้อมูลจริง": {
            "ชุดที่ดีที่สุด": f"EMA {real[0][1]}/{real[0][2]}",
            "ผลของชุดที่ดีที่สุดเปอร์เซ็นต์": round(100 * real[0][0], 2),
            "ผลกลางของทุกชุดเปอร์เซ็นต์": round(100 * statistics.median(v for v, _, _ in real), 2),
            "ผลของการถือเฉยๆเปอร์เซ็นต์": round(100 * hold, 2),
            "จำนวนชุดที่ชนะการถือเฉยๆ": beat,
        },
        "บนข้อมูลที่ไม่มีโครงสร้าง": {
            "ผลของชุดที่ดีที่สุดกลางเปอร์เซ็นต์": round(100 * best_noise, 2),
            "ชุดที่ดีที่สุดช่วง90เปอร์เซ็นต์": [round(100 * bests[rounds // 20], 2),
                                                  round(100 * bests[rounds - rounds // 20 - 1], 2)],
            "ผลของการหยิบชุดเดียวโดยไม่ค้นหากลางเปอร์เซ็นต์": round(100 * single_noise, 2),
            "ส่วนที่การค้นหาสร้างขึ้นจุดเปอร์เซ็นต์": round(100 * (best_noise - single_noise), 2),
        },
        "เปอร์เซ็นไทล์ของผลจริงเทียบกับความสุ่ม": round(
            100 * sum(1 for b in bests if b <= real[0][0]) / rounds),
    }


# ── Part 9: บทสรุป 30 วันของมิน ─────────────────────────────────────────────
def _capstone_study(prices, start="2026-07-31", capital_thb=50000):
    """หน้าต่าง 30 วันสุดท้ายของข้อมูล ใช้เดินเรื่องบทปิดเล่ม

    เลือกหน้าต่างนี้เพราะมันเล่าเรื่องทั้งเล่มได้ในตัวเอง — เงียบยาว แล้วหางมาเยือน
    """
    days = [d for d in sorted(prices) if d >= start]
    px = [prices[d] for d in days]
    rets = [(days[i], px[i] / px[i - 1] - 1) for i in range(1, len(px))]
    total = px[-1] / px[0] - 1

    big = sorted(rets, key=lambda kv: -kv[1])[:2]
    without = total + 1
    for _, r in big:
        without /= 1 + r
    without -= 1

    quiet = [d for d, _ in rets if d < big[-1][0] and d < big[0][0]]
    return {
        "ช่วง": {"ตั้งแต่": days[0], "ถึง": days[-1], "จำนวนวัน": len(days)},
        "ราคาเริ่ม": round(px[0]),
        "ราคาจบ": round(px[-1]),
        "ผลรวมเปอร์เซ็นต์": round(100 * total, 2),
        "สองวันที่ใหญ่ที่สุด": [{"วันที่": d, "เปอร์เซ็นต์": round(100 * r, 2)} for d, r in big],
        "ถ้าตัดสองวันนั้นออกเปอร์เซ็นต์": round(100 * without, 2),
        "จำนวนวันก่อนสองวันนั้น": len(quiet),
        "ราคาก่อนสองวันนั้น": round(prices[quiet[-1]]) if quiet else None,
        "เปลี่ยนแปลงในช่วงเงียบเปอร์เซ็นต์": round(100 * (prices[quiet[-1]] / px[0] - 1), 2) if quiet else None,
        "ทุนบาท": capital_thb,
        "ทุนปลายทางถ้าถือทั้งหมด": round(capital_thb * (1 + total)),
        "ทุนปลายทางถ้าพลาดสองวัน": round(capital_thb * (1 + without)),
        "ราคาสูงสุดในช่วง": round(max(px)),
        "วันที่ราคาสูงสุด": days[px.index(max(px))],
        "ไม้แรกของมิน": _first_trade(prices, capital_thb),
    }


def _first_trade(prices, capital_thb, entry_day="2026-08-01", target=66000, stop=62000,
                 risk_pct=1.0, horizon=5):
    """ไม้แรกของมินในบทสรุป — คำนวณขนาดไม้จากเพดานความเสียหายตามกฎใน Part 7"""
    days = sorted(prices)
    i = days.index(entry_day)
    entry = prices[entry_day]
    window = [prices[d] for d in days[i + 1:i + 1 + horizon]]
    risk_baht = capital_thb * risk_pct / 100
    stop_distance = (entry - stop) / entry
    size = risk_baht / stop_distance
    return {
        "วันเข้า": entry_day,
        "ราคาเข้า": round(entry),
        "เป้าหมาย": target,
        "จุดที่ยอมรับว่าผิด": stop,
        "เพดานความเสียหายบาท": round(risk_baht),
        "ระยะถึงจุดที่ผิดเปอร์เซ็นต์": round(100 * stop_distance, 2),
        "ขนาดไม้บาท": round(size / 100) * 100,
        "ราคาสูงสุดในห้าวัน": round(max(window)),
        "ถึงเป้าหมายไหม": max(window) >= target,
    }


def build():
    prices = _daily_btc_prices()
    streaks = _streak_study(prices)
    # ชุดราคารายวันเต็ม — ใช้วาดกราฟในบท (tools/nq_charts.py อ่านจากตรงนี้)
    days_sorted = sorted(prices)
    daily = {d: prices[d] for d in days_sorted}
    # ผลตอบแทนรายวัน เพื่อให้ทุกตัวเลข "วันนั้นขยับกี่ %" ในบทมาจากแหล่งเดียว
    daily_ret = {days_sorted[i]: round(100 * (prices[days_sorted[i]] / prices[days_sorted[i - 1]] - 1), 2)
                 for i in range(1, len(days_sorted))}
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
            # ถ้าใส่เงินเต็มทุกไม้ ค่าธรรมเนียมล้วน ๆ กินทุนไปกี่เปอร์เซ็นต์ต่อปี
            "ค่าธรรมเนียมต่อปีเปอร์เซ็นต์": round(MIN_ACCOUNT["ไม้ต่อสัปดาห์"] * 52 * 2 * fee, 1),
        },
        "btc": streaks,
        "ราคารายวัน": daily,
        "ผลตอบแทนรายวันเปอร์เซ็นต์": daily_ret,
        "ต้นทุนจริง": _spread_study(),
        "ความสุ่ม": _randomness_study(streaks),
        "ขนาดตัวอย่าง": _sample_size_study(),
        "ดาวเด่น": _star_trader_study(),
        "ผู้รอดชีวิต": _survivorship_study(prices),
        "เงื่อนไข": _conditional_study(),
        "อินดิเคเตอร์": _indicator_study(prices),
        "ข้อความ": _claim_study(prices),
        "การกระจายผลตอบแทน": _distribution_study(prices),
        "ลำดับ": _path_study(prices),
        "ต้นทุนตามอายุ": _cost_study(),
        "โครงสร้าง": _structure_study(prices),
        "การอยู่รอด": _survival_study(prices),
        "กลับทุน": _drawdown_table(),
        "การค้นหา": _search_study(prices),
        "บทสรุป": _capstone_study(prices),
    }


if __name__ == "__main__":
    _args = sys.argv[1:]
    if "--data-dir" in _args:
        _i = _args.index("--data-dir")
        DATA_DIR = _args[_i + 1]
        _args = _args[:_i] + _args[_i + 2:]
    if not os.path.isdir(DATA_DIR):
        sys.exit(f"ไม่พบโฟลเดอร์ข้อมูล: {DATA_DIR}\n"
                 f"ระบุตำแหน่งด้วย --data-dir <path> หรือตัวแปรแวดล้อม NQ_DATA_DIR "
                 f"(ต้องมี deribit/ และ okx/ อยู่ข้างใน)")
    data = build()
    if "--check" in _args:
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
