"""ตัวอย่างที่รันได้จริงบนข้อมูลของรีโปนี้

เดินตามสถาปัตยกรรมในบทที่ 11 ทีละขั้น:

    ราคา → log return → หัก BTC beta → residual → PIT → copula → วินิจฉัย

และทำซ้ำอีกครั้งกับคู่ที่ข้อมูลชุดนี้ถนัดเป็นพิเศษ: **implied volatility**

    python3 book/copula/code/example_repo_data.py

หมายเหตุสำคัญ: รีโปนี้เก็บ snapshot วันละครั้ง ข้อมูลจึงสั้นมาก
ตัวอย่างนี้เป็นการสาธิต *ขั้นตอน* ไม่ใช่ข้อสรุปเชิงสถิติ —
และสคริปต์จะเตือนเรื่องนี้เองตามหลักในบทที่ 5 หัวข้อ 5.4
"""

import csv
import glob
import os
import sys
from datetime import date

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from copula_toolkit import (  # noqa: E402
    Clayton, Gumbel,
    effective_breadth, empirical_tail_dep, fit_tau_inversion,
    half_life, pseudo_obs, select_family,
)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
COINS = ["BTC", "ETH"]          # ที่มีอยู่จริงใน snapshot ปัจจุบัน
MIN_DAYS = 30


# ─────────────────────────────────────────────────────────────
# โหลดข้อมูล
# ─────────────────────────────────────────────────────────────

def load_daily(exchange="deribit"):
    """คืน (วัน, ราคา spot, ATM IV) รายวันของแต่ละเหรียญ

    ATM IV = ค่าเฉลี่ยของ mark_iv ของ call ที่ strike ใกล้ราคา spot ที่สุด
    ใน expiry ที่อยู่ห่างออกไป 20–45 วัน (เลี่ยง expiry สั้นที่ IV เต้นแรง)
    """
    spot = {c: {} for c in COINS}
    iv = {c: {} for c in COINS}

    for path in sorted(glob.glob(os.path.join(REPO, "data", exchange, "*", "*", "*.csv"))):
        day = os.path.basename(path)[:-4]
        d0 = date.fromisoformat(day)
        rows = {c: [] for c in COINS}

        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                c = row.get("underlying")
                if c not in COINS or not row.get("underlying_price"):
                    continue
                spot[c].setdefault(day, float(row["underlying_price"]))
                if row.get("type") != "call" or not row.get("mark_iv"):
                    continue
                try:
                    dte = (date.fromisoformat(row["expiry"]) - d0).days
                    if 20 <= dte <= 45:
                        rows[c].append((abs(float(row["strike"]) - float(row["underlying_price"])),
                                        float(row["mark_iv"])))
                except (ValueError, KeyError):
                    continue

        for c in COINS:
            if rows[c]:
                rows[c].sort()
                iv[c][day] = float(np.mean([v for _, v in rows[c][:3]]))

    days = sorted(set.intersection(*(set(spot[c]) for c in COINS),
                                   *(set(iv[c]) for c in COINS)))
    return (days,
            {c: np.array([spot[c][d] for d in days]) for c in COINS},
            {c: np.array([iv[c][d] for d in days]) for c in COINS})


# ─────────────────────────────────────────────────────────────
# การวิเคราะห์คู่หนึ่งคู่ (ใช้ซ้ำได้กับทั้ง return และ IV)
# ─────────────────────────────────────────────────────────────

def analyse_pair(x, y, label_x, label_y):
    print(f"\n  τ({label_x}, {label_y}) = {stats.kendalltau(x, y).statistic:6.3f}")

    u, v = pseudo_obs(x), pseudo_obs(y)

    print("\n  เลือก family ตาม AIC — อ่าน *ช่องว่าง* ไม่ใช่แค่ผู้ชนะ (บทที่ 5)")
    ranked = [r for r in select_family(u, v) if r["copula"] is not None]
    for row in ranked:
        print(f"    {row['family']:10s} θ={row['copula'].theta:8.3f}   "
              f"loglik={row['loglik']:7.2f}   AIC={row['aic']:7.2f}")
    if len(ranked) >= 2:
        gap = ranked[1]["aic"] - ranked[0]["aic"]
        verdict = "แยกได้ชัด" if gap > 6 else "แยกไม่ออก — อย่ายึดผู้ชนะ"
        print(f"    ΔAIC อันดับ 1→2 = {gap:.2f}  ({verdict})")

    cl = fit_tau_inversion(u, v, Clayton)
    gu = fit_tau_inversion(u, v, Gumbel)
    print(f"\n  tail dependence: Clayton λ_L = {cl.lambda_lower():.3f} | "
          f"Gumbel λ_U = {gu.lambda_upper():.3f}   (ตามทฤษฎี)")
    for q in (0.15, 0.25):
        print(f"    q={q:.2f}: λ̂_L={empirical_tail_dep(u, v, q, 'lower'):5.2f}  "
              f"λ̂_U={empirical_tail_dep(u, v, q, 'upper'):5.2f}   "
              f"(จากข้อมูลเพียง {int(np.sum(u <= q))} จุด)")


def main():
    days, spot, iv = load_daily()
    if len(days) < MIN_DAYS:
        print(f"ข้อมูลน้อยเกินไป ({len(days)} วัน) — ต้องมีอย่างน้อย {MIN_DAYS}")
        return 1

    print("=" * 70)
    print(f"ข้อมูล {len(days)} วัน: {days[0]} ถึง {days[-1]}   |   เหรียญ: {', '.join(COINS)}")
    print("=" * 70)

    ret = {c: np.diff(np.log(spot[c])) for c in COINS}
    dvol = {c: np.diff(iv[c]) for c in COINS}
    n = len(ret["BTC"])

    # ── [1] หัก common factor — บทที่ 11 ────────────────────
    print("\n[1] หัก common factor (BTC เป็น factor)   — บทที่ 11 หัวข้อ 11.3")
    beta = np.polyfit(ret["BTC"], ret["ETH"], 1)[0]
    resid_eth = ret["ETH"] - beta * ret["BTC"]
    share = 1 - np.var(resid_eth) / np.var(ret["ETH"])
    print(f"    ETH beta ต่อ BTC = {beta:.2f}")
    print(f"    BTC อธิบายความแปรปรวนของ ETH ได้ {share:.1%}"
          f"  ← เหลือให้เทรดจริงแค่ {1 - share:.1%}")

    # ── [2] copula ของผลตอบแทน ──────────────────────────────
    print("\n[2] คู่ผลตอบแทน BTC ↔ ETH")
    analyse_pair(ret["BTC"], ret["ETH"], "r_BTC", "r_ETH")

    # ── [3] copula ของ implied volatility ───────────────────
    print("\n[3] คู่การเปลี่ยนแปลง ATM IV (20–45 วันถึงหมดอายุ)")
    print("    คำถาม: IV ของสองเหรียญพุ่งพร้อมกันไหม — upper tail สำคัญกว่า lower")
    analyse_pair(dvol["BTC"], dvol["ETH"], "ΔIV_BTC", "ΔIV_ETH")

    # ── [4] มี reversion ให้เทรดไหม — บทที่ 8 ───────────────
    print("\n[4] มี mean reversion จริงไหม   — บทที่ 8 (ทดสอบแยกจาก copula เสมอ)")
    hl_resid = half_life(np.cumsum(resid_eth))
    hl_iv = half_life(iv["BTC"] - iv["ETH"])
    fmt = lambda h: "ไม่พบ mean reversion" if not np.isfinite(h) else f"{h:.1f} วัน"  # noqa: E731
    print(f"    half-life ของ residual ETH สะสม  = {fmt(hl_resid)}")
    print(f"    half-life ของ spread IV (BTC−ETH) = {fmt(hl_iv)}")
    print("    ถ้าไม่พบ reversion ก็ไม่มีอะไรให้เทรด ไม่ว่า copula จะบอกอะไร")
    print(f"\n    ⚠ ที่ n={n} การประมาณ AR(1) มี bias ลงต่ำ (Dickey–Fuller)")
    print("      random walk แท้ ๆ ก็จะให้ half-life สั้น ๆ ออกมาได้เอง —")
    print("      ตัวเลขนี้จึงเป็นตัวอย่างการคำนวณ ไม่ใช่หลักฐานว่ามี reversion")

    # ── [5] effective breadth — บทที่ 10 ────────────────────
    print("\n[5] effective breadth ของพอร์ตสมมติ 3 ขา   — บทที่ 10")
    print("    ขา 1: ETH residual | ขา 2: ΔIV spread | ขา 3: long ETH / short BTC")
    legs = np.column_stack([resid_eth,
                            dvol["ETH"] - dvol["BTC"],
                            ret["ETH"] - ret["BTC"]])
    worst = ret["BTC"] <= np.quantile(ret["BTC"], 0.25)
    print(f"    N_eff (ทุกวัน)        = {effective_breadth(np.corrcoef(legs, rowvar=False)):.2f} จาก 3")
    print(f"    N_eff (วันแย่ที่สุด 25%) = "
          f"{effective_breadth(np.corrcoef(legs[worst], rowvar=False)):.2f}"
          f"   ← ใช้ตัวนี้ตั้ง risk limit")

    print("\n" + "=" * 70)
    print(f"⚠ ข้อมูลมีเพียง {n} วัน — พอสาธิตขั้นตอน ไม่พอสรุปอะไรทั้งสิ้น")
    print("  ตัวเลข tail ทุกตัวข้างบนมาจากข้อมูลไม่กี่จุด (บทที่ 5 หัวข้อ 5.4)")
    print("  อ่านบทที่ 12 ก่อนแปลงสิ่งนี้เป็นการทดสอบกลยุทธ์")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
