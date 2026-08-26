"""
วัดว่า "เลือกโมเดล" กับ "ประมาณค่าพารามิเตอร์" อันไหนคือคอขวดจริง
บน window สั้นแบบที่ engine ใช้อยู่ (FACTOR_WINDOW = 42)
"""
import warnings
import numpy as np
from statsmodels.tsa.stattools import adfuller
from signals import ResidualReversionSignal

warnings.filterwarnings("ignore")
rng = np.random.default_rng(0)
fit_ou = ResidualReversionSignal.fit_ou


def simulate_ou(theta, n, sigma=0.01):
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = x[t - 1] * (1 - theta) + rng.normal(0, sigma)
    return x


print("=" * 78)
print("  1) AR(1) small-sample bias -> half-life ที่ประมาณได้สั้นกว่าความจริง")
print("=" * 78)
print(f"{'true HL':>9} {'T':>6} {'HL ประมาณ (median)':>20} {'อคติ':>10} {'ติดลบ/ไม่ลู่':>13}")
print("-" * 78)
for true_hl in [6.0, 12.0, 24.0]:
    theta = np.log(2) / true_hl
    for T in [42, 100, 250, 1000]:
        hls, bad = [], 0
        for _ in range(3000):
            th, _, _ = fit_ou(simulate_ou(theta, T))
            if th <= 0:
                bad += 1
            else:
                hls.append(np.log(2) / th)
        med = np.median(hls) if hls else float('nan')
        print(f"{true_hl:9.1f} {T:6d} {med:20.1f} {med/true_hl-1:+9.0%} {bad/3000:12.0%}")

print()
print("=" * 78)
print("  2) พลังของ ADF test: แยก mean-reverting ออกจาก random walk ได้แค่ไหน")
print("=" * 78)
print(f"{'T':>6} {'ปฏิเสธ unit root เมื่อ HL=12 (power)':>38} {'false positive เมื่อเป็น RW':>28}")
print("-" * 78)
for T in [42, 100, 250, 1000]:
    theta = np.log(2) / 12.0
    power = np.mean([adfuller(simulate_ou(theta, T), autolag=None, maxlag=1)[1] < 0.05
                     for _ in range(600)])
    fp = np.mean([adfuller(np.cumsum(rng.normal(0, 0.01, T)), autolag=None, maxlag=1)[1] < 0.05
                  for _ in range(600)])
    print(f"{T:6d} {power:37.0%} {fp:27.0%}")
