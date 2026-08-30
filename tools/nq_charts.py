#!/usr/bin/env python3
"""สร้างกราฟ inline SVG ของหนังสือ "คิดแบบ Quant" จาก docs/nq-figures.json

กราฟทุกอันในเล่มวาดจากตัวเลขในไฟล์เดียวกับที่บทใช้ จึงเป็นไปไม่ได้ที่กราฟกับ
ข้อความจะขัดกันเอง (จุดอ่อน W7) และแก้รูปแบบกราฟได้โดยไม่ต้องแตะ SVG ด้วยมือ

ในไฟล์บท คั่นตำแหน่งกราฟด้วย
    <!--CHART:ชื่อ--> ... <!--/CHART:ชื่อ-->
สคริปต์จะเขียนทับเฉพาะระหว่างคู่นี้ รันซ้ำได้ตลอด

    python3 tools/nq_charts.py
"""

import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
FONT = 'font-family="Sarabun,sans-serif"'


def chart_randomness(fig):
    """ฮิสโทแกรม: ความสุ่มสร้าง 'ขึ้น 3 วันติด' ได้กี่ครั้ง เทียบกับของจริง"""
    r = fig["ความสุ่ม"]
    dist = {int(k): v for k, v in r["การกระจาย"].items()}
    ks = sorted(dist)
    peak = max(dist.values())
    obs = r["ของจริง"]
    lo, hi = r["ช่วง90เปอร์เซ็นต์"]

    W, H, L, B, T = 760, 322, 52, 250, 48
    bw = (W - L - 24) / len(ks)
    out = [f'<line x1="{L-6}" y1="{B}" x2="{W-16}" y2="{B}" stroke="#d1d5db" stroke-width="1.5"/>']
    for i, k in enumerate(ks):
        h = (B - T) * dist[k] / peak
        x = L + i * bw
        fill = "#7c3aed" if k == obs else ("#93c5fd" if lo <= k <= hi else "#e5e7eb")
        out.append(f'<rect x="{x:.1f}" y="{B-h:.1f}" width="{bw-2:.1f}" height="{h:.1f}" rx="2" fill="{fill}"/>')
        if k % 2 == 0:
            out.append(f'<text x="{x+bw/2-1:.1f}" y="{B+16}" text-anchor="middle" font-size="11" fill="#9ca3af" {FONT}>{k}</text>')

    ox = L + ks.index(obs) * bw + bw / 2 - 1
    oy = B - (B - T) * dist[obs] / peak
    out.append(f'<line x1="{ox:.1f}" y1="{oy-8:.1f}" x2="{ox:.1f}" y2="{T-16}" stroke="#7c3aed" stroke-width="2"/>')
    out.append(f'<text x="{ox:.1f}" y="{T-22}" text-anchor="middle" font-size="13" font-weight="700" fill="#7c3aed" {FONT}>ตลาดจริง = {obs} ครั้ง</text>')
    out.append(f'<text x="{L-8}" y="{T+6}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>บ่อย</text>')
    out.append(f'<text x="{L-8}" y="{B-2}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>น้อย</text>')
    out.append(f'<text x="{(L+W-24)/2:.0f}" y="{B+38}" text-anchor="middle" font-size="12" fill="#6b7280" {FONT}>จำนวนครั้งที่เกิด "ขึ้น 3 วันติด" ใน 56 วัน</text>')
    lx, ly = W - 232, T + 4
    out.append(f'<rect x="{lx}" y="{ly-10}" width="216" height="46" rx="6" fill="#f9fafb" stroke="#e5e7eb"/>')
    out.append(f'<rect x="{lx+10}" y="{ly}" width="11" height="11" rx="2" fill="#93c5fd"/>')
    out.append(f'<text x="{lx+27}" y="{ly+10}" font-size="11.5" fill="#4b5563" {FONT}>ช่วงที่ความสุ่มสร้างได้ 90%</text>')
    out.append(f'<rect x="{lx+10}" y="{ly+17}" width="11" height="11" rx="2" fill="#7c3aed"/>')
    out.append(f'<text x="{lx+27}" y="{ly+27}" font-size="11.5" fill="#4b5563" {FONT}>ค่าที่วัดได้จากตลาดจริง</text>')

    alt = (f"การกระจายของจำนวนครั้งที่เกิด ขึ้น 3 วันติด จากการจำลองเหรียญสุ่ม "
           f"{r['จำนวนรอบจำลอง']:,} รอบ โดยค่าจริงของตลาดคือ {obs} ครั้ง ซึ่งอยู่กลางเนิน")
    cap = (f"จำลองเหรียญที่ออกหัวเท่าสัดส่วนวันขึ้นจริง {r['จำนวนรอบจำลอง']:,} รอบ · "
           f"ความสุ่มล้วน ๆ ให้ค่าเฉลี่ย {r['เฉลี่ยจากความสุ่ม']} ครั้ง "
           f"และอยู่ในช่วง {lo}–{hi} ครั้งถึง 90% ของเวลา")
    return _wrap(W, H, alt, out, cap)


def chart_sample_size(fig):
    """เส้นโค้ง: ต้องเทรดกี่ไม้ถึงจะพิสูจน์ edge ได้"""
    ss = fig["ขนาดตัวอย่าง"]
    pts = sorted(((int(k), v) for k, v in ss["มีEdgeจริง"].items()))
    no_edge = ss["ไม่มีEdgeเลย"]["1000"]

    W, H, L, B, T = 760, 312, 56, 236, 46
    x0, x1 = math.log10(pts[0][0]), math.log10(pts[-1][0])
    X = lambda n: L + (math.log10(n) - x0) / (x1 - x0) * (W - L - 46)
    Y = lambda p: B - (p / 100) * (B - T)

    out = []
    for g in (0, 25, 50, 75, 100):
        out.append(f'<line x1="{L}" y1="{Y(g):.1f}" x2="{W-32}" y2="{Y(g):.1f}" stroke="#f3f4f6" stroke-width="1"/>')
        out.append(f'<text x="{L-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>{g}%</text>')

    line = " ".join(("M" if i == 0 else "L") + f"{X(n):.1f},{Y(p):.1f}" for i, (n, p) in enumerate(pts))
    out.append(f'<path d="{line} L{X(pts[-1][0]):.1f},{B} L{X(pts[0][0]):.1f},{B} Z" fill="url(#nqArea)"/>')
    out.append(f'<path d="{line}" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    out.append(f'<line x1="{L}" y1="{Y(no_edge):.1f}" x2="{W-32}" y2="{Y(no_edge):.1f}" stroke="#dc2626" stroke-width="2" stroke-dasharray="6 4"/>')
    out.append(f'<text x="{W-36}" y="{Y(no_edge)-9:.1f}" text-anchor="end" font-size="12" font-weight="700" fill="#dc2626" {FONT}>คนที่ไม่มี edge เลย ≈ {no_edge}%</text>')

    for i, (n, p) in enumerate(pts):
        anchor = "end" if i == len(pts) - 1 else "middle"
        out.append(f'<circle cx="{X(n):.1f}" cy="{Y(p):.1f}" r="4.5" fill="#fff" stroke="#2563eb" stroke-width="2.5"/>')
        out.append(f'<text x="{X(n):.1f}" y="{Y(p)-14:.1f}" text-anchor="{anchor}" font-size="12.5" font-weight="700" fill="#1e40af" {FONT}>{p}%</text>')
        out.append(f'<text x="{X(n):.1f}" y="{B+18}" text-anchor="middle" font-size="11.5" fill="#6b7280" {FONT}>{n:,}</text>')
    out.append(f'<text x="{(L+W-32)/2:.0f}" y="{B+40}" text-anchor="middle" font-size="12" fill="#6b7280" {FONT}>จำนวนไม้ที่เทรด (มาตราส่วนลอการิทึม)</text>')

    defs = ('<defs><linearGradient id="nqArea" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#2563eb" stop-opacity=".22"/>'
            '<stop offset="1" stop-color="#2563eb" stop-opacity="0"/></linearGradient></defs>')
    alt = ("กราฟแสดงว่าคนที่มี edge จริง 55% ต้องเทรดกี่ไม้ถึงจะพิสูจน์ตัวเองได้ "
           f"ที่ 100 ไม้ได้แค่ {ss['มีEdgeจริง']['100']}% ที่ 1000 ไม้ได้ {ss['มีEdgeจริง']['1000']}%")
    cap = (f"จำลอง {ss['จำนวนรอบจำลอง']:,} รอบต่อจุด · เส้นน้ำเงินคือคนที่เก่งจริง "
           "เส้นแดงคือคนที่ไม่มีฝีมือเลย — กว่าสองเส้นจะแยกออกจากกันชัดเจน ต้องใช้ถึงหลักพันไม้")
    return _wrap(W, H, alt, [defs] + out, cap)



def chart_indicator(fig):
    """ราคาจริงพร้อมจุดที่สัญญาณ EMA สั่งซื้อและสั่งขาย — ให้เห็นว่ามันสั่งช้าตรงไหน"""
    daily = fig["ราคารายวัน"]
    ind = fig["อินดิเคเตอร์"]
    start = ind["ช่วงที่ใช้"]["ตั้งแต่"]

    days = [d for d in sorted(daily) if d >= start]
    px = [daily[d] for d in days]
    lo, hi = min(px), max(px)
    pad = (hi - lo) * 0.16

    W, H, L, R, B, T = 780, 330, 62, 26, 250, 44
    X = lambda i: L + i / (len(days) - 1) * (W - L - R)
    Y = lambda v: B - (v - lo + pad / 2) / (hi - lo + pad) * (B - T)

    out = ['<defs><linearGradient id="nqPx" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0" stop-color="#2563eb" stop-opacity=".18"/>'
           '<stop offset="1" stop-color="#2563eb" stop-opacity="0"/></linearGradient></defs>']

    for v in (65000, 70000, 75000, 80000):
        if lo - pad <= v <= hi + pad:
            out.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W-R}" y2="{Y(v):.1f}" stroke="#f3f4f6" stroke-width="1"/>')
            out.append(f'<text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>{v//1000}k</text>')

    line = " ".join(("M" if i == 0 else "L") + f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(px))
    out.append(f'<path d="{line} L{X(len(px)-1):.1f},{B} L{X(0):.1f},{B} Z" fill="url(#nqPx)"/>')
    out.append(f'<path d="{line}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round"/>')

    for sig in ind["สัญญาณ"]:
        i = days.index(sig["วันที่"])
        buy = sig["สัญญาณ"] == "ซื้อ"
        color = "#16a34a" if buy else "#dc2626"
        y = Y(sig["ราคา"])
        out.append(f'<line x1="{X(i):.1f}" y1="{y:.1f}" x2="{X(i):.1f}" y2="{B}" stroke="{color}" stroke-width="1" stroke-dasharray="3 3" opacity=".55"/>')
        out.append(f'<circle cx="{X(i):.1f}" cy="{y:.1f}" r="6" fill="#fff" stroke="{color}" stroke-width="3"/>')
        dy = -22 if buy else 22
        out.append(f'<text x="{X(i):.1f}" y="{y+dy:.1f}" text-anchor="middle" font-size="12.5" font-weight="700" fill="{color}" {FONT}>{sig["สัญญาณ"]}</text>')
        out.append(f'<text x="{X(i):.1f}" y="{y+dy+(-16 if buy else 16):.1f}" text-anchor="middle" font-size="11" fill="{color}" {FONT}>{sig["ราคา"]:,}</text>')

    for i in (0, len(days) - 1):
        out.append(f'<text x="{X(i):.1f}" y="{B+20}" text-anchor="{"start" if i==0 else "end"}" font-size="11.5" fill="#6b7280" {FONT}>{days[i][5:]}</text>')

    out.append(f'<text x="{(L+W-R)/2:.0f}" y="{T-20}" text-anchor="middle" font-size="13" font-weight="700" fill="#374151" {FONT}>'
               f'สั่งขายที่จุดต่ำ แล้วสั่งซื้อคืนที่จุดสูงกว่า — สองครั้ง</text>')

    hold = ind["ผลถือเฉยเปอร์เซ็นต์"]
    sysr = ind["ผลระบบเปอร์เซ็นต์"]
    out.append(f'<rect x="{L}" y="{B+30}" width="{W-L-R}" height="34" rx="7" fill="#f9fafb" stroke="#e5e7eb"/>')
    out.append(f'<text x="{L+16}" y="{B+52}" font-size="12.5" fill="#4b5563" {FONT}>'
               f'เดินตามสัญญาณ <tspan font-weight="700" fill="#b45309">+{sysr}%</tspan>'
               f'   ·   ซื้อแล้วถือเฉย ๆ <tspan font-weight="700" fill="#16a34a">+{hold}%</tspan>'
               f'   ·   ตามหลังอยู่ <tspan font-weight="700" fill="#dc2626">{ind["ตามหลังอยู่จุดเปอร์เซ็นต์"]} จุด</tspan></text>')

    alt = ("กราฟราคา BTC จริงพร้อมจุดที่สัญญาณ EMA สั่งซื้อและสั่งขาย "
           "แสดงว่าระบบสั่งขายที่ราคาต่ำแล้วสั่งซื้อคืนที่ราคาสูงกว่าสองครั้ง")
    cap = (f'ราคา BTC จริง {ind["ช่วงที่ใช้"]["ตั้งแต่"]} ถึง {ind["ช่วงที่ใช้"]["ถึง"]} '
           f'({ind["ช่วงที่ใช้"]["จำนวนวัน"]} วัน) · จุดสัญญาณมาจาก EMA 12/26 ตัดกันบนข้อมูลชุดเดียวกัน')
    return _wrap(W, H, alt, out, cap)



def chart_returns(fig):
    """ฮิสโทแกรมผลตอบแทนรายวันจริง พร้อมชี้วันที่หลุดกรอบ"""
    d = fig["การกระจายผลตอบแทน"]
    bins = {int(k): v for k, v in d["ฮิสโทแกรมช่องละหนึ่งเปอร์เซ็นต์"].items()}
    ks = list(range(min(bins), max(bins) + 1))
    peak = max(bins.values())
    sd = d["ส่วนเบี่ยงเบนต่อวันเปอร์เซ็นต์"]
    best = d["วันดีสุด"]["เปอร์เซ็นต์"]

    W, H, L, R, B, T = 760, 300, 54, 26, 224, 52
    bw = (W - L - R) / len(ks)
    out = [f'<line x1="{L-6}" y1="{B}" x2="{W-R}" y2="{B}" stroke="#d1d5db" stroke-width="1.5"/>']

    for i, k in enumerate(ks):
        c = bins.get(k, 0)
        h = (B - T) * c / peak
        x = L + i * bw
        far = abs(k) >= 2 * sd
        fill = "#dc2626" if (far and k > 0) else ("#f97316" if far else "#93c5fd")
        if c:
            out.append(f'<rect x="{x+1:.1f}" y="{B-h:.1f}" width="{bw-3:.1f}" height="{h:.1f}" rx="2" fill="{fill}"/>')
            out.append(f'<text x="{x+bw/2:.1f}" y="{B-h-6:.1f}" text-anchor="middle" font-size="10.5" fill="#6b7280" {FONT}>{c}</text>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{B+17}" text-anchor="middle" font-size="10.5" fill="#9ca3af" {FONT}>{k:+d}</text>')

    # เส้นกรอบ ±2 sd
    for sign in (1, -1):
        v = sign * 2 * sd
        i = (v - min(ks)) / len(ks) * len(ks)
        xx = L + (v - min(ks)) / (max(ks) + 1 - min(ks)) * (W - L - R)
        out.append(f'<line x1="{xx:.1f}" y1="{T-4}" x2="{xx:.1f}" y2="{B}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="5 4"/>')
    out.append(f'<text x="{L + (2*sd - min(ks))/(max(ks)+1-min(ks))*(W-L-R) + 6:.1f}" y="{T+6}" font-size="11.5" fill="#64748b" {FONT}>กรอบ ±2 เท่าของส่วนเบี่ยงเบน</text>')

    xb = L + (best - min(ks)) / (max(ks) + 1 - min(ks)) * (W - L - R)
    out.append(f'<text x="{W-R}" y="{T-24}" text-anchor="end" font-size="13" font-weight="700" fill="#dc2626" {FONT}>วันเดียวที่ {best}% = {d["วันดีสุด"]["กี่เท่าของสวนเบี่ยงเบน"]} เท่าของส่วนเบี่ยงเบน</text>')
    out.append(f'<path d="M{W-R-40} {T-18} Q {xb+34:.1f} {T+6} {xb+bw/2:.1f} {B-40:.1f}" stroke="#dc2626" stroke-width="1.5" fill="none" marker-end="url(#nqAr)"/>')
    out.append('<defs><marker id="nqAr" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#dc2626"/></marker></defs>')
    out.append(f'<text x="{(L+W-R)/2:.0f}" y="{B+40}" text-anchor="middle" font-size="12" fill="#6b7280" {FONT}>ผลตอบแทนรายวัน (%) · ตัวเลขบนแท่งคือจำนวนวัน</text>')

    alt = ("ฮิสโทแกรมผลตอบแทนรายวันของ BTC จำนวน 56 วัน แสดงว่าวันส่วนใหญ่ขยับเล็กน้อย "
           f"แต่มีหนึ่งวันที่ขยับ {best}% ซึ่งหลุดกรอบไปไกล")
    cap = (f'ผลตอบแทนรายวันจริง {d["จำนวนวัน"]} วัน · แต่ละช่องกว้าง 1% ป้ายบอกขอบล่างของช่อง · '
           f'ส่วนเบี่ยงเบน {sd}% ต่อวัน · มี {d["วันที่ขยับเกินสองเท่าของส่วนเบี่ยงเบน"]} วันที่ขยับเกิน 2 เท่าของส่วนเบี่ยงเบน')
    return _wrap(W, H, alt, out, cap)



def chart_cost(fig):
    """ต้นทุนส่วนต่างราคาซื้อ-ขาย แยกตามอายุคงเหลือ เทียบสองตลาด"""
    c = fig["ต้นทุนตามอายุ"]
    order = ["0-2 วัน", "3-7 วัน", "8-30 วัน", "31-120 วัน", "เกิน 120 วัน"]
    venues = [(v, c["ตลาด"][v]["ตามอายุคงเหลือ"]) for v in ("deribit", "okx") if v in c["ตลาด"]]
    colors = {"deribit": "#7c3aed", "okx": "#0891b2"}

    peak = max(g[k]["ส่วนต่างกลางเปอร์เซ็นต์"] for _, g in venues for k in g)
    W, H, L, R, B, T = 760, 320, 56, 24, 236, 56
    gw = (W - L - R) / len(order)
    bw = min(30, (gw - 22) / len(venues))

    out = []
    for g in (0, 5, 10, 15, 20, 25):
        if g <= peak * 1.12:
            y = B - g / (peak * 1.12) * (B - T)
            out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#f3f4f6" stroke-width="1"/>')
            out.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>{g}%</text>')

    for i, key in enumerate(order):
        cx = L + i * gw + gw / 2
        for j, (venue, g) in enumerate(venues):
            if key not in g:
                continue
            val = g[key]["ส่วนต่างกลางเปอร์เซ็นต์"]
            h = val / (peak * 1.12) * (B - T)
            x = cx - (len(venues) * bw + 6) / 2 + j * (bw + 6)
            out.append(f'<rect x="{x:.1f}" y="{B-h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="{colors[venue]}"/>')
            out.append(f'<text x="{x+bw/2:.1f}" y="{B-h-7:.1f}" text-anchor="middle" font-size="11.5" font-weight="700" fill="{colors[venue]}" {FONT}>{val}</text>')
        out.append(f'<text x="{cx:.1f}" y="{B+18}" text-anchor="middle" font-size="11.5" fill="#6b7280" {FONT}>{key}</text>')

    out.append(f'<line x1="{L}" y1="{B}" x2="{W-R}" y2="{B}" stroke="#d1d5db" stroke-width="1.5"/>')
    out.append(f'<text x="{(L+W-R)/2:.0f}" y="{B+40}" text-anchor="middle" font-size="12" fill="#6b7280" {FONT}>อายุคงเหลือของสัญญา</text>')
    out.append(f'<text x="{L}" y="{T-26}" font-size="13" font-weight="700" fill="#374151" {FONT}>ยิ่งใกล้หมดอายุ ค่าผ่านทางยิ่งแพง — ต่างกันเกือบสิบเท่า</text>')

    lx = W - R - 190
    for j, (venue, _) in enumerate(venues):
        out.append(f'<rect x="{lx + j*95}" y="{T-14}" width="11" height="11" rx="2" fill="{colors[venue]}"/>')
        out.append(f'<text x="{lx + j*95 + 16}" y="{T-4}" font-size="11.5" fill="#4b5563" {FONT}>{venue}</text>')

    alt = ("กราฟแท่งเปรียบเทียบส่วนต่างราคาซื้อ-ขายของสัญญาใกล้ราคาปัจจุบัน แยกตามอายุคงเหลือ "
           "แสดงว่าสัญญาที่ใกล้หมดอายุมีต้นทุนสูงกว่าหลายเท่า")
    cap = (f'ข้อมูลจริงวันที่ {c["วันที่"]} · นับเฉพาะสัญญาที่ห่างจากราคาปัจจุบันไม่เกิน '
           f'{c["นับเฉพาะสัญญาใกล้ราคาปัจจุบันภายในเปอร์เซ็นต์"]}% และมีทั้งราคาเสนอซื้อและเสนอขาย · '
           'ตัวเลขข้ามตลาดเทียบกันแบบหยาบ เพราะสเปกสัญญาและเวลาสแนปช็อตไม่ตรงกันเป๊ะ')
    return _wrap(W, H, alt, out, cap)



def chart_payoff(fig):
    """กราฟการจ่ายผลของสามโครงสร้าง สร้างจากราคาจริงในกระดาน"""
    st = fig["โครงสร้าง"]
    spot = st["ราคาปัจจุบัน"]
    kb, ks = st["ราคาใช้สิทธิ์ที่ซื้อ"], st["ราคาใช้สิทธิ์ที่ขาย"]
    long_cost, net = st["ราคาที่จ่ายซื้อสิทธิ์"], st["ต้นทุนสุทธิแบบมีเพดาน"]

    x0, x1 = round(spot * 0.88), round(spot * 1.22)
    series = [
        ("ซื้อของจริง", "#64748b", lambda f: f - spot),
        ("ซื้อสิทธิ์", "#2563eb", lambda f: max(f - kb, 0) - long_cost),
        ("ซื้อสิทธิ์แบบมีเพดาน", "#7c3aed", lambda f: min(max(f - kb, 0), ks - kb) - net),
    ]
    ys = [fn(x) for _, _, fn in series for x in (x0, x1, kb, ks, spot)]
    ylo, yhi = min(ys), max(ys)
    pad = (yhi - ylo) * 0.12

    W, H, L, R, B, T = 780, 350, 66, 150, 250, 40
    X = lambda v: L + (v - x0) / (x1 - x0) * (W - L - R)
    Y = lambda v: B - (v - ylo + pad) / (yhi - ylo + 2 * pad) * (B - T)

    out = []
    for v in range(0, yhi + 1, 5000):
        out.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W-R}" y2="{Y(v):.1f}" stroke="#f8fafc" stroke-width="1"/>')
    for v in range(-10000, 1, 5000):
        out.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W-R}" y2="{Y(v):.1f}" stroke="#f8fafc" stroke-width="1"/>')
    for v in range(-10000, yhi + 1, 5000):
        if ylo - pad <= v <= yhi + pad:
            out.append(f'<text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>{v:+,}</text>')

    out.append(f'<line x1="{L}" y1="{Y(0):.1f}" x2="{W-R}" y2="{Y(0):.1f}" stroke="#cbd5e1" stroke-width="1.5"/>')
    out.append(f'<line x1="{X(spot):.1f}" y1="{T}" x2="{X(spot):.1f}" y2="{B}" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="4 4"/>')
    out.append(f'<text x="{X(spot):.1f}" y="{T-6}" text-anchor="middle" font-size="11" fill="#94a3b8" {FONT}>วันนี้ {spot:,}</text>')

    for name, color, fn in series:
        pts = [x0, kb, ks, x1]
        d = " ".join(("M" if i == 0 else "L") + f"{X(x):.1f},{Y(fn(x)):.1f}" for i, x in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
        out.append(f'<text x="{W-R+10}" y="{Y(fn(x1))+4:.1f}" font-size="12" font-weight="700" fill="{color}" {FONT}>{name}</text>')

    for label, v in (("80,000", kb), ("86,000", ks)):
        out.append(f'<text x="{X(v):.1f}" y="{B+18}" text-anchor="middle" font-size="11" fill="#94a3b8" {FONT}>{label}</text>')

    out.append(f'<text x="{(L+W-R)/2:.0f}" y="{B+40}" text-anchor="middle" font-size="12" fill="#6b7280" {FONT}>ราคา BTC ณ วันหมดอายุ (ดอลลาร์)</text>')
    out.append(f'<text x="{L-56}" y="{T+2}" font-size="11.5" fill="#6b7280" {FONT}>กำไร/ขาดทุน ($)</text>')

    alt = ("กราฟการจ่ายผลของสามโครงสร้างบนความเชื่อเดียวกัน: ซื้อของจริงเป็นเส้นตรง "
           "ซื้อสิทธิ์มีขาดทุนจำกัดแต่กำไรไม่จำกัด และแบบมีเพดานถูกกว่าแต่กำไรตัน")
    cap = (f'สร้างจากราคาเสนอซื้อ-เสนอขายจริงวันที่ {st["วันที่"]} สัญญาหมดอายุ {st["หมดอายุ"]} '
           f'(อีก {st["จำนวนวันคงเหลือ"]} วัน) · คิดราคาแบบที่รายย่อยได้จริง คือจ่ายราคาเสนอขายเวลาซื้อ '
           'และได้ราคาเสนอซื้อเวลาขาย')
    return _wrap(W, H, alt, out, cap)



def chart_survival(fig):
    """เทียบผลจำลองสองชุด: ชุดที่อบตลาดขาขึ้นไว้ กับชุดที่ตัดแนวโน้มออก"""
    sv = fig["การอยู่รอด"]
    levs = ["0.5", "1", "2", "3"]
    sets = [("ใช้ผลตอบแทนจริง", "ใช้ผลตอบแทนจริง (ช่วงขาขึ้น)", "#94a3b8"),
            ("ตัดแนวโน้มออก", "ตัดแนวโน้มออก (สมมติไม่มี edge)", "#dc2626")]

    W, H, L, R, B, T = 760, 344, 60, 24, 232, 62
    gw = (W - L - R) / len(levs)
    bw = min(34, (gw - 26) / 2)

    out = []
    for g in (0, 25, 50, 75, 100):
        y = B - g / 100 * (B - T)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#f3f4f6" stroke-width="1"/>')
        out.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>{g}%</text>')

    for i, lev in enumerate(levs):
        cx = L + i * gw + gw / 2
        for j, (key, _, color) in enumerate(sets):
            val = sv[key][lev]["เคยลึกสามสิบเปอร์เซ็นต์"]
            h = val / 100 * (B - T)
            x = cx - (2 * bw + 8) / 2 + j * (bw + 8)
            out.append(f'<rect x="{x:.1f}" y="{B-h:.1f}" width="{bw:.1f}" height="{max(h,1.5):.1f}" rx="3" fill="{color}"/>')
            out.append(f'<text x="{x+bw/2:.1f}" y="{B-h-7:.1f}" text-anchor="middle" font-size="11.5" font-weight="700" fill="{color}" {FONT}>{val}%</text>')
        label = "ครึ่งทุน" if lev == "0.5" else f"{lev} เท่า"
        out.append(f'<text x="{cx:.1f}" y="{B+18}" text-anchor="middle" font-size="11.5" fill="#6b7280" {FONT}>{label}</text>')

    out.append(f'<line x1="{L}" y1="{B}" x2="{W-R}" y2="{B}" stroke="#d1d5db" stroke-width="1.5"/>')
    out.append(f'<text x="{(L+W-R)/2:.0f}" y="{B+40}" text-anchor="middle" font-size="12" fill="#6b7280" {FONT}>ขนาดไม้ (สัดส่วนต่อทุน)</text>')
    out.append(f'<text x="{L}" y="{T-34}" font-size="13.5" font-weight="700" fill="#374151" {FONT}>โอกาสที่พอร์ตจะเคยติดลบลึกถึง 30% ภายในหนึ่งปี</text>')
    out.append(f'<text x="{L}" y="{T-16}" font-size="12" fill="#6b7280" {FONT}>ข้อมูลชุดเดียวกัน ต่างกันแค่ว่าอบตลาดขาขึ้นไว้ในสมมติฐานหรือไม่</text>')

    # คำอธิบายสัญลักษณ์วางไว้ใต้แกน เพื่อไม่ให้ทับป้ายของแท่งที่สูงเกือบ 100%
    ly = B + 62
    for j, (_, name, color) in enumerate(sets):
        lx = L + j * 330
        out.append(f'<rect x="{lx}" y="{ly-10}" width="11" height="11" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx+16}" y="{ly}" font-size="11.5" fill="#4b5563" {FONT}>{name}</text>')

    alt = ("กราฟแท่งเทียบโอกาสที่พอร์ตจะติดลบลึก 30% ภายในหนึ่งปี ระหว่างการจำลองที่ใช้ผลตอบแทน "
           "ช่วงตลาดขาขึ้น กับการจำลองที่ตัดแนวโน้มออก ซึ่งให้คำตอบต่างกันมาก")
    cap = (f'{sv["คำอธิบาย"]} · ชุดสีเทาอบแนวโน้มขาขึ้น {sv["แนวโน้มที่ตัดออกต่อวันเปอร์เซ็นต์"]}% ต่อวัน '
           'ไว้ในสมมติฐาน ส่วนชุดสีแดงตัดออก เหลือเฉพาะรูปร่างความผันผวนและหางอ้วน')
    return _wrap(W, H, alt, out, cap)



def chart_search(fig):
    """การค้นหาสร้างผลงานปลอมได้เท่าไร — เทียบสี่กรณีบนแกนเดียวกัน"""
    sc = fig["การค้นหา"]
    real, noise = sc["บนข้อมูลจริง"], sc["บนข้อมูลที่ไม่มีโครงสร้าง"]
    n = sc["จำนวนชุดที่ลอง"]

    bars = [
        (f"หยิบมาชุดเดียว ไม่ค้นหา", "ข้อมูลสุ่ม", noise["ผลของการหยิบชุดเดียวโดยไม่ค้นหากลางเปอร์เซ็นต์"], "#cbd5e1"),
        (f"ค้นหา {n} ชุด เอาที่ดีที่สุด", "ข้อมูลสุ่ม", noise["ผลของชุดที่ดีที่สุดกลางเปอร์เซ็นต์"], "#f97316"),
        (f"ค้นหา {n} ชุด เอาที่ดีที่สุด", "ข้อมูลจริง", real["ผลของชุดที่ดีที่สุดเปอร์เซ็นต์"], "#2563eb"),
        ("ไม่ทำอะไรเลย ถือเฉย ๆ", "ข้อมูลจริง", real["ผลของการถือเฉยๆเปอร์เซ็นต์"], "#16a34a"),
    ]

    W, H, L, R, T = 780, 258, 250, 60, 46
    rowh = 46
    lo = min(v for _, _, v, _ in bars)
    hi = max(v for _, _, v, _ in bars)
    zero = L + (0 - lo) / (hi - lo) * (W - L - R) if lo < 0 else L
    X = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)

    out = [f'<line x1="{zero:.1f}" y1="{T-10}" x2="{zero:.1f}" y2="{T + len(bars)*rowh - 8}" stroke="#cbd5e1" stroke-width="1.5"/>']
    for i, (label, src, val, color) in enumerate(bars):
        y = T + i * rowh
        x0, x1 = (zero, X(val)) if val >= 0 else (X(val), zero)
        out.append(f'<rect x="{x0:.1f}" y="{y:.1f}" width="{max(x1-x0,2):.1f}" height="24" rx="4" fill="{color}"/>')
        out.append(f'<text x="{L-12}" y="{y+12:.1f}" text-anchor="end" font-size="12.5" fill="#374151" {FONT}>{label}</text>')
        out.append(f'<text x="{L-12}" y="{y+27:.1f}" text-anchor="end" font-size="11" fill="#9ca3af" {FONT}>{src}</text>')
        # ค่าติดลบวางป้ายไว้ขวาของเส้นศูนย์ เพื่อไม่ให้ทับคอลัมน์ชื่อรายการ
        tx = x1 + 8 if val >= 0 else zero + 8
        out.append(f'<text x="{tx:.1f}" y="{y+17:.1f}" text-anchor="start" font-size="12.5" font-weight="700" fill="{color}" {FONT}>{val:+.2f}%</text>')

    y0, y1 = T + 12, T + rowh + 12
    bx = max(X(noise["ผลของชุดที่ดีที่สุดกลางเปอร์เซ็นต์"]), X(noise["ผลของการหยิบชุดเดียวโดยไม่ค้นหากลางเปอร์เซ็นต์"])) + 84
    out.append(f'<path d="M{bx} {y0} L{bx+14} {y0} L{bx+14} {y1} L{bx} {y1}" stroke="#f97316" stroke-width="1.5" fill="none"/>')
    out.append(f'<text x="{bx+22}" y="{(y0+y1)/2+4:.1f}" font-size="12" font-weight="700" fill="#c2410c" {FONT}>+{noise["ส่วนที่การค้นหาสร้างขึ้นจุดเปอร์เซ็นต์"]} จุด</text>')
    out.append(f'<text x="{bx+22}" y="{(y0+y1)/2+20:.1f}" font-size="11" fill="#9a3412" {FONT}>เกิดจากการค้นหาล้วน ๆ</text>')
    out.append(f'<text x="{L-12}" y="{T-20}" text-anchor="end" font-size="13" font-weight="700" fill="#374151" {FONT}>ผลตอบแทนตลอดช่วง</text>')

    alt = ("กราฟแท่งเทียบสี่กรณี แสดงว่าการค้นหาพารามิเตอร์จำนวนมากแล้วรายงานอันที่ดีที่สุด "
           "สร้างผลงานที่ดูดีขึ้นได้แม้บนข้อมูลที่ไม่มีโครงสร้างอะไรเลย")
    cap = (f'ลองพารามิเตอร์ {n} ชุด · ฝั่งข้อมูลสุ่มจำลอง {sc["จำนวนรอบจำลอง"]} รอบแล้วรายงานค่ากลาง · '
           f'บนข้อมูลจริง ไม่มีชุดไหนเลยจาก {n} ชุดที่ชนะการถือเฉย ๆ')
    return _wrap(W, H, alt, out, cap)


def _wrap(w, h, alt, parts, cap):
    body = "\n".join(parts)
    return (f'<svg class="fig" viewBox="0 0 {w} {h}" role="img" aria-label="{alt}">\n'
            f'{body}\n</svg>\n<div class="cap">{cap}</div>')


CHARTS = {
    "randomness": chart_randomness,
    "sample-size": chart_sample_size,
    "indicator": chart_indicator,
    "returns": chart_returns,
    "cost": chart_cost,
    "payoff": chart_payoff,
    "survival": chart_survival,
    "search": chart_search,
}


def main():
    with open(os.path.join(DOCS, "nq-figures.json")) as fh:
        fig = json.load(fh)

    written = 0
    for name in sorted(os.listdir(DOCS)):
        if not (name.startswith("nq-") and name.endswith(".html")):
            continue
        path = os.path.join(DOCS, name)
        with open(path) as fh:
            html = fh.read()
        original = html
        for key, build in CHARTS.items():
            pattern = re.compile(
                r"(<!--CHART:" + re.escape(key) + r"-->).*?(<!--/CHART:" + re.escape(key) + r"-->)",
                re.S)
            if pattern.search(html):
                html = pattern.sub(lambda m: m.group(1) + "\n" + build(fig) + "\n" + m.group(2), html)
        if html != original:
            with open(path, "w") as fh:
                fh.write(html)
            written += 1
            print("อัปเดตกราฟใน", name)
    if not written:
        print("ไม่มีไฟล์ไหนมีตัวคั่น <!--CHART:ชื่อ--> ให้เขียน")


if __name__ == "__main__":
    main()
