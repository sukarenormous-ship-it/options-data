#!/usr/bin/env python3
"""สร้าง docs/copula-figures.json — ตัวเลขทั้งหมดของบท "Copula ในทางปฏิบัติ"

fit copula กับผลตอบแทน BTC/ETH จริงในคลังนี้ แล้ววัดสามอย่างที่บทต้องใช้
  1. พารามิเตอร์และ tail dependence ของแต่ละ family เมื่อ fit ข้อมูลชุดเดียวกัน
  2. ความไม่นิ่งของค่าที่ได้ (bootstrap + tail เชิงประจักษ์)
  3. สัญญาณ Mispricing Index เทียบกับ z-score ของสาย cointegration

ต้องมี numpy + scipy:  pip install numpy scipy
    python3 tools/copula_figures.py
"""

import collections
import csv
import glob
import json
import math
import os
import statistics

import numpy as np
from scipy import optimize, stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "copula-figures.json")
SEED = 20260830


def daily_prices():
    """ราคารายวันของแต่ละเหรียญ = median ของ underlying_price ในไฟล์วันนั้น"""
    per = collections.defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "*", "*", "*", "*.csv"))):
        day = os.path.basename(path)[:-4]
        buckets = collections.defaultdict(list)
        with open(path) as fh:
            for row in csv.DictReader(fh):
                if row.get("underlying_price"):
                    buckets[row["underlying"]].append(float(row["underlying_price"]))
        for sym, vals in buckets.items():
            per[sym].setdefault(day, statistics.median(vals))
    return per


# ── log-likelihood ของ copula แต่ละตระกูล (บน pseudo-observations) ──────────
def ll_gaussian(rho, u, v):
    if abs(rho) >= 0.999:
        return -1e9
    x, y = stats.norm.ppf(u), stats.norm.ppf(v)
    return float(np.sum(-0.5 * np.log(1 - rho ** 2)
                        - (rho ** 2 * (x ** 2 + y ** 2) - 2 * rho * x * y) / (2 * (1 - rho ** 2))))


def ll_student(params, u, v):
    rho, df = params
    if abs(rho) >= 0.999 or df < 2.1 or df > 60:
        return -1e9
    x, y = stats.t.ppf(u, df), stats.t.ppf(v, df)
    d = 1 - rho ** 2
    q = (x ** 2 - 2 * rho * x * y + y ** 2) / d
    term = (math.lgamma((df + 2) / 2) + math.lgamma(df / 2) - 2 * math.lgamma((df + 1) / 2)
            - 0.5 * math.log(d) - (df + 2) / 2 * np.log(1 + q / df)
            + (df + 1) / 2 * (np.log(1 + x ** 2 / df) + np.log(1 + y ** 2 / df)))
    return float(np.sum(term))


def ll_clayton(theta, u, v):
    if theta <= 0.01 or theta > 30:
        return -1e9
    return float(np.sum(np.log(1 + theta) - (1 + theta) * (np.log(u) + np.log(v))
                        - (2 + 1 / theta) * np.log(u ** -theta + v ** -theta - 1)))


def ll_gumbel(theta, u, v):
    if theta < 1.001 or theta > 30:
        return -1e9
    lu, lv = -np.log(u), -np.log(v)
    s = (lu ** theta + lv ** theta) ** (1 / theta)
    return float(np.sum(-s + np.log((lu * lv) ** (theta - 1)) + np.log(s + theta - 1)
                        - np.log(u) - np.log(v)
                        + (1 - 2 * theta) / theta * np.log(lu ** theta + lv ** theta)))


def fit_families(u, v):
    out = {}
    r = optimize.minimize_scalar(lambda x: -ll_gaussian(x, u, v), bounds=(-0.98, 0.98), method="bounded")
    out["Gaussian"] = {"logL": -r.fun, "k": 1, "พารามิเตอร์": {"rho": round(float(r.x), 3)},
                       "tailล่าง": 0.0, "tailบน": 0.0}
    r = optimize.minimize(lambda p: -ll_student(p, u, v), [0.85, 6], method="Nelder-Mead")
    rho, df = float(r.x[0]), float(r.x[1])
    lam = float(2 * stats.t.cdf(-math.sqrt((df + 1) * (1 - rho) / (1 + rho)), df + 1))
    out["Student-t"] = {"logL": -r.fun, "k": 2,
                        "พารามิเตอร์": {"rho": round(rho, 3), "df": round(df, 1)},
                        "tailล่าง": round(lam, 3), "tailบน": round(lam, 3)}
    r = optimize.minimize_scalar(lambda x: -ll_clayton(x, u, v), bounds=(0.05, 25), method="bounded")
    th = float(r.x)
    out["Clayton"] = {"logL": -r.fun, "k": 1, "พารามิเตอร์": {"theta": round(th, 3)},
                      "tailล่าง": round(2 ** (-1 / th), 3), "tailบน": 0.0}
    r = optimize.minimize_scalar(lambda x: -ll_gumbel(x, u, v), bounds=(1.01, 25), method="bounded")
    th = float(r.x)
    out["Gumbel"] = {"logL": -r.fun, "k": 1, "พารามิเตอร์": {"theta": round(th, 3)},
                     "tailล่าง": 0.0, "tailบน": round(2 - 2 ** (1 / th), 3)}
    for name, d in out.items():
        d["AIC"] = round(2 * d["k"] - 2 * d["logL"], 2)
        d["logL"] = round(d["logL"], 2)
    return out


def build():
    per = daily_prices()
    days = sorted(set(per["BTC"]) & set(per["ETH"]))
    b = np.array([per["BTC"][d] for d in days])
    e = np.array([per["ETH"][d] for d in days])
    rb, re = np.diff(np.log(b)), np.diff(np.log(e))
    n = len(rb)
    u = stats.rankdata(rb) / (n + 1)
    v = stats.rankdata(re) / (n + 1)

    tau = float(stats.kendalltau(rb, re).statistic)
    fams = fit_families(u, v)
    best = min(fams.items(), key=lambda kv: kv[1]["AIC"])
    second = sorted(fams.items(), key=lambda kv: kv[1]["AIC"])[1]

    # tail dependence ที่ได้ถ้า "สมมติ family ไว้ก่อน" แล้วใช้ tau หาพารามิเตอร์
    assumed = {
        "Gaussian": 0.0,
        "Clayton": round(2 ** (-1 / (2 * tau / (1 - tau))), 3),
        "Gumbel": round(2 - 2 ** (1 / (1 / (1 - tau))), 3),
    }
    rho_tau = math.sin(math.pi * tau / 2)
    for df in (3, 5, 8):
        assumed[f"Student-t (df={df})"] = round(
            float(2 * stats.t.cdf(-math.sqrt((df + 1) * (1 - rho_tau) / (1 + rho_tau)), df + 1)), 3)

    # ความไม่นิ่ง
    rng = np.random.default_rng(SEED)
    taus, lams = [], []
    for _ in range(2000):
        i = rng.integers(0, n, n)
        t = float(stats.kendalltau(rb[i], re[i]).statistic)
        taus.append(t)
        lams.append(2 ** (-1 / (2 * t / (1 - t))) if t < 0.999 else np.nan)
    taus, lams = np.array(taus), np.array(lams)

    emp = {}
    for q in (0.05, 0.10, 0.20):
        emp[f"{int(q*100)}%"] = {
            "จำนวนจุดในหาง": int(round(q * n)),
            "หางล่าง": round(float(np.mean((u <= q) & (v <= q)) / q), 2),
            "หางบน": round(float(np.mean((u >= 1 - q) & (v >= 1 - q)) / q), 2),
        }

    # สัญญาณ: z-score (สาย cointegration) เทียบกับ Mispricing Index (สาย copula)
    lb, le = np.cumsum(rb), np.cumsum(re)
    beta = float(np.polyfit(lb, le, 1)[0])
    spread = le - beta * lb
    z = (spread - spread.mean()) / spread.std(ddof=1)
    rho_g = fams["Gaussian"]["พารามิเตอร์"]["rho"]
    x, y = stats.norm.ppf(u), stats.norm.ppf(v)
    mi = stats.norm.cdf((y - rho_g * x) / math.sqrt(1 - rho_g ** 2)) - 0.5

    z_hit = np.abs(z) > 1.5
    mi_hit = np.abs(mi) > 0.35
    both = int(np.sum(z_hit & mi_hit))
    same_dir = int(np.sum(z_hit & mi_hit & (np.sign(z) == np.sign(mi))))

    return {
        "_อ่านก่อน": "สร้างด้วย tools/copula_figures.py — ห้ามแก้ด้วยมือ",
        "ข้อมูล": {"คู่": "BTC / ETH", "ตั้งแต่": days[0], "ถึง": days[-1],
                   "จำนวนวันผลตอบแทน": n,
                   "sdBTCเปอร์เซ็นต์": round(float(rb.std(ddof=1)) * 100, 2),
                   "sdETHเปอร์เซ็นต์": round(float(re.std(ddof=1)) * 100, 2)},
        "ความสัมพันธ์": {
            "Pearson": round(float(stats.pearsonr(rb, re).statistic), 3),
            "Spearman": round(float(stats.spearmanr(rb, re).statistic), 3),
            "Kendall": round(tau, 3),
        },
        "tailถ้าสมมติfamilyไว้ก่อน": assumed,
        "fitด้วยML": fams,
        "familyที่ดีที่สุด": {"ชื่อ": best[0], "AIC": best[1]["AIC"],
                              "ห่างจากอันดับสอง": round(second[1]["AIC"] - best[1]["AIC"], 2),
                              "อันดับสอง": second[0]},
        "ความไม่นิ่ง": {
            "จำนวนรอบbootstrap": 2000,
            "tauกลาง": round(float(np.median(taus)), 3),
            "tauช่วง90": [round(float(np.percentile(taus, 5)), 3), round(float(np.percentile(taus, 95)), 3)],
            "claytonTailกลาง": round(float(np.nanmedian(lams)), 3),
            "claytonTailช่วง90": [round(float(np.nanpercentile(lams, 5)), 3),
                                   round(float(np.nanpercentile(lams, 95)), 3)],
        },
        "tailเชิงประจักษ์": emp,
        "สัญญาณ": {
            "beta": round(beta, 3),
            "เกณฑ์z": 1.5, "เกณฑ์MI": 0.35,
            "วันที่zเข้าเกณฑ์": int(np.sum(z_hit)),
            "วันที่MIเข้าเกณฑ์": int(np.sum(mi_hit)),
            "วันที่เข้าเกณฑ์ทั้งคู่": both,
            "และตรงทิศกัน": same_dir,
            "สหสัมพันธ์zกับMI": round(float(np.corrcoef(z, mi)[0, 1]), 3),
            "สหสัมพันธ์MIกับการเปลี่ยนแปลงของz": round(float(np.corrcoef(mi[1:], np.diff(z))[0, 1]), 3),
        },
    }


if __name__ == "__main__":
    with open(OUT, "w") as fh:
        json.dump(build(), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("เขียน", os.path.relpath(OUT, ROOT))
