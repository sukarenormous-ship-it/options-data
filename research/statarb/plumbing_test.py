"""
PLUMBING TEST — ไม่ใช่หลักฐานว่ามี edge

จุดประสงค์เดียว: พิสูจน์ว่าท่อ signal -> optimizer -> accounting ต่อถูก
วิธีคือ "ฝัง" edge ที่รู้คำตอบอยู่แล้วลงในข้อมูลสังเคราะห์ แล้วดูว่า
signal generator ที่ตรงกับ edge นั้นจับได้ไหม และตัวที่ไม่ตรงต้องไม่ได้อะไร

ข้อควรระวังที่สำคัญที่สุด:
    ผลลัพธ์ในไฟล์นี้บอกได้แค่ว่า "โค้ดทำงานถูก" เท่านั้น
    มันไม่ได้บอกเลยว่ากลยุทธ์ทำเงินได้ในตลาดจริง
    เพราะ edge ถูกใส่เข้าไปเองด้วยมือ นี่คือความผิดพลาดเดียวกับที่
    ไฟล์เวอร์ชันเดิมทำ (Sharpe 21.87 จากข้อมูลที่สร้างเอง)
    ต้องรันกับข้อมูล Binance จริงเท่านั้นถึงจะตอบคำถามเรื่อง edge ได้
"""

import numpy as np
import pandas as pd

from engine import BacktestEngine, Config, summarize
from signals import (CarrySignal, CompositeSignal, MomentumSignal,
                     ResidualReversionSignal)

SYMBOLS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'LINK', 'NEAR', 'SUI']
BETAS = np.array([[1.00, -0.35], [1.12, -0.15], [1.40, 0.55], [0.92, -0.25], [1.02, -0.08],
                  [1.20, 0.28], [1.32, 0.40], [1.18, 0.12], [1.38, 0.48], [1.48, 0.60]])


def make_data(edge: str, n_bars: int = 3000, seed: int = 7):
    """
    edge = 'none'      -> ไม่มี edge ใดๆ (ทุกกลยุทธ์ควรขาดทุนเท่าค่าธรรมเนียม)
           'reversion' -> cumulative residual เป็น OU ตามสเปก Avellaneda-Lee จริง
           'carry'     -> funding สูงต่อเนื่อง โดยราคาไม่มี drift ชดเชย
           'momentum'  -> แต่ละเหรียญมี alpha drift ที่คงอยู่นานหลายสัปดาห์
    """
    rng = np.random.default_rng(seed)
    N = len(SYMBOLS)
    idx = pd.date_range('2024-01-01', periods=n_bars, freq='4h', tz='UTC')

    macro = np.sin(np.linspace(0, 5 * np.pi, n_bars)) * 0.0025
    F = np.column_stack([rng.normal(macro, 0.016), rng.normal(0.0, 0.011, n_bars)])
    systematic = F @ BETAS.T

    idio = rng.normal(0.0, 0.012, (n_bars, N))
    funding = rng.normal(0.0001, 0.00012, (n_bars, N))

    if edge == 'reversion':
        # ระดับสะสม (ไม่ใช่ผลตอบแทน) เป็น OU -> ผลตอบแทน residual = ผลต่างของ OU
        level = np.zeros((n_bars, N))
        for i in range(N):
            th, sig = 0.06, 0.012
            for t in range(1, n_bars):
                level[t, i] = level[t - 1, i] * (1 - th) + rng.normal(0, sig)
        idio = np.vstack([level[0], np.diff(level, axis=0)])

    elif edge == 'carry':
        # funding แพงติดตัวเหรียญ (persistent) และราคาไม่ได้ชดเชยกลับ
        # -> short เหรียญ funding สูงแล้วเก็บเงินได้จริง
        base = rng.normal(0.0001, 0.00025, N)
        for t in range(n_bars):
            funding[t] = base + rng.normal(0, 0.00008, N)

    elif edge == 'momentum':
        # alpha drift ที่ persistent มาก (half-life ~ 40 วัน) -> ผลตอบแทน 30 วันที่ผ่านมา
        # เป็นตัวประมาณ drift ปัจจุบัน ซึ่งยังคงอยู่ในอนาคต
        drift = np.zeros((n_bars, N))
        for i in range(N):
            for t in range(1, n_bars):
                drift[t, i] = drift[t - 1, i] * 0.997 + rng.normal(0, 0.00025)
        idio = idio + drift

    returns = pd.DataFrame(systematic + idio, index=idx, columns=SYMBOLS)
    return returns, pd.DataFrame(funding, index=idx, columns=SYMBOLS)


def build_signals():
    return [
        ResidualReversionSignal(),
        CarrySignal(),
        MomentumSignal(),
        CompositeSignal([(CarrySignal(), 0.5), (MomentumSignal(), 0.5)]),
    ]


if __name__ == '__main__':
    print("=" * 96)
    print("  PLUMBING TEST — ตรวจว่าท่อต่อถูก ไม่ใช่การพิสูจน์ว่ามี edge")
    print("=" * 96)

    for edge in ['none', 'reversion', 'carry', 'momentum']:
        rets, fund = make_data(edge)
        print(f"\n### ข้อมูลที่ฝัง edge แบบ: {edge.upper()}")
        print(f"{'signal':28s} {'net%':>10s} {'Sharpe':>8s} {'maxDD%':>9s} "
              f"{'turn/day%':>10s} {'gross':>7s}")
        print("-" * 96)
        for gen in build_signals():
            pnl, st = BacktestEngine(rets, fund, SYMBOLS, gen).run()
            m = summarize(pnl)
            flag = " <-- ตรงกับ edge ที่ฝัง" if gen.name.startswith(edge) else ""
            print(f"{gen.name:28s} {m['net_return_pct']:10.1f} {m['sharpe']:8.2f} "
                  f"{m['max_dd_pct']:9.2f} {m['turnover_daily_pct']:10.1f} "
                  f"{m['avg_gross_exposure']:7.2f}{flag}")

    print("\n" + "=" * 96)
    print("  อ่านผลยังไง: แต่ละบล็อก signal ที่ตรงกับ edge ที่ฝังควรเป็นตัวที่ดีที่สุด")
    print("  และในบล็อก NONE ทุกตัวควรติดลบ (= ค่าธรรมเนียมล้วน ไม่มีใครเสก alpha ได้)")
    print("=" * 96)
