"""ตรวจสอบว่าสูตรทุกตัวใน copula_toolkit ถูกต้อง

วิธีตรวจคือเทียบกับผลต่างเชิงตัวเลข (finite difference) ของ CDF
ซึ่งจับความผิดพลาดของการอนุพันธ์ด้วยมือได้เกือบทั้งหมด

    python3 book/copula/code/test_toolkit.py
"""

import sys
import numpy as np
from scipy import stats

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from copula_toolkit import (  # noqa: E402
    Clayton, Frank, Gaussian, Gumbel, StudentT,
    bucket_forward_return, effective_breadth, empirical_tail_dep,
    fit_cml, fit_tau_inversion, half_life, mispricing_index,
    pseudo_obs, rolling_pseudo_obs, select_family,
)

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")


GRID = np.array([0.08, 0.23, 0.41, 0.57, 0.72, 0.91])
UU, VV = np.meshgrid(GRID, GRID)
UU, VV = UU.ravel(), VV.ravel()


def numeric_h(cop, u, v, eps=1e-6):
    """h(u|v) = ∂C(u,v)/∂v ประมาณด้วยผลต่างกลาง"""
    return (cop.cdf(u, v + eps) - cop.cdf(u, v - eps)) / (2 * eps)


def numeric_pdf(cop, u, v, eps=1e-5):
    """c(u,v) = ∂²C/∂u∂v"""
    return (cop.cdf(u + eps, v + eps) - cop.cdf(u + eps, v - eps)
            - cop.cdf(u - eps, v + eps) + cop.cdf(u - eps, v - eps)) / (4 * eps ** 2)


print("\n[1] h-function ตรงกับอนุพันธ์เชิงตัวเลขของ CDF")
for cop in [Clayton(2.0), Clayton(0.5), Gumbel(1.8), Gumbel(3.0),
            Frank(5.0), Frank(-3.0), Gaussian(0.7), Gaussian(-0.4)]:
    got = cop.h(UU, VV)
    want = numeric_h(cop, UU, VV)
    err = np.max(np.abs(got - want))
    check(f"{cop!r}", err < 1e-4, f"max err = {err:.2e}")


print("\n[2] density ตรงกับอนุพันธ์อันดับสองเชิงตัวเลข")
for cop in [Clayton(2.0), Gumbel(1.8), Frank(5.0), Frank(-3.0), Gaussian(0.7)]:
    got = np.exp(cop.logpdf(UU, VV))
    want = numeric_pdf(cop, UU, VV)
    err = np.max(np.abs(got - want) / np.maximum(want, 1e-3))
    check(f"{cop!r}", err < 1e-3, f"max rel err = {err:.2e}")


print("\n[3] Student-t: h ตรงกับอนุพันธ์ของ CDF ที่สร้างจากการอินทิเกรต density")
# t copula ไม่มี cdf ในโค้ด จึงตรวจอีกทาง: ∫ h ตาม u ต้องได้ 1 และ h ต้องเพิ่ม
tcop = StudentT(0.6, nu=5)
uu = np.linspace(0.001, 0.999, 4000)
for v in (0.15, 0.5, 0.85):
    hv = tcop.h(uu, np.full_like(uu, v))
    check(f"StudentT h เพิ่มตาม u (v={v})", np.all(np.diff(hv) >= -1e-9))
    check(f"StudentT h(1|v)≈1 (v={v})", abs(hv[-1] - 1.0) < 1e-3, f"got {hv[-1]:.5f}")

# density ของ t copula ต้องอินทิเกรตได้ 1 บน unit square
n = 400
g = (np.arange(n) + 0.5) / n
U, V = np.meshgrid(g, g)
integral = np.mean(np.exp(tcop.logpdf(U.ravel(), V.ravel())))
check("StudentT density อินทิเกรตได้ ≈ 1", abs(integral - 1) < 0.02, f"got {integral:.4f}")


print("\n[4] h เป็น CDF ที่ถูกต้อง: อยู่ใน [0,1] และเพิ่มตาม u")
for cop in [Clayton(2.0), Gumbel(2.5), Frank(6.0), Gaussian(0.5), StudentT(0.5, 4)]:
    uu = np.linspace(0.002, 0.998, 500)
    hv = cop.h(uu, np.full_like(uu, 0.37))
    ok = np.all(hv >= -1e-9) and np.all(hv <= 1 + 1e-9) and np.all(np.diff(hv) >= -1e-9)
    check(f"{cop.name}", ok)


print("\n[5] independence limit: dependence → 0 ⟹ h(u|v) → u")
for cop in [Clayton(1e-4), Gumbel(1.0 + 1e-9), Frank(1e-6), Gaussian(0.0)]:
    err = np.max(np.abs(cop.h(UU, VV) - UU))
    check(f"{cop.name}", err < 1e-3, f"max err = {err:.2e}")


print("\n[6] h_inv กลับด้าน h ได้จริง")
for cop in [Clayton(2.0), Gumbel(2.0), Frank(5.0), Gaussian(0.6)]:
    w = np.array([0.05, 0.3, 0.5, 0.77, 0.95])
    v = np.array([0.2, 0.4, 0.5, 0.6, 0.8])
    u_back = cop.h_inv(w, v)
    err = np.max(np.abs(cop.h(u_back, v) - w))
    check(f"{cop.name}", err < 1e-6, f"max err = {err:.2e}")


print("\n[7] tail dependence ตามทฤษฎี ตรงกับที่วัดจากตัวอย่างสุ่ม")
rng = np.random.default_rng(7)
for cop, side in [(Clayton(3.0), "lower"), (Gumbel(2.5), "upper")]:
    u, v = cop.sample(200_000, rng)
    theory = cop.lambda_lower() if side == "lower" else cop.lambda_upper()
    emp = empirical_tail_dep(u, v, 0.005, side=side)
    check(f"{cop!r} λ_{side}", abs(emp - theory) < 0.05,
          f"theory {theory:.3f} vs empirical {emp:.3f}")

# Gaussian ต้องไม่มี tail dependence — λ̂ ต้องลดลงเมื่อ q เล็กลง
gc = Gaussian(0.7)
u, v = gc.sample(200_000, rng)
lam_big = empirical_tail_dep(u, v, 0.10, "lower")
lam_small = empirical_tail_dep(u, v, 0.005, "lower")
check("Gaussian λ̂ ลดลงเมื่อ q → 0", lam_small < lam_big - 0.05,
      f"{lam_big:.3f} → {lam_small:.3f}")


print("\n[8] τ-inversion กลับไปกลับมาได้")
for fam in [Clayton, Gumbel, Frank, Gaussian]:
    for tau in (0.15, 0.35, 0.6):
        cop = fam(fam.tau_to_theta(tau))
        u, v = cop.sample(60_000, rng)
        tau_hat = stats.kendalltau(u, v).statistic
        check(f"{fam.name} τ={tau}", abs(tau_hat - tau) < 0.02,
              f"got {tau_hat:.3f}")


print("\n[9] การประมาณค่ากู้พารามิเตอร์คืนได้")
for cop in [Clayton(2.0), Gumbel(2.2), Frank(6.0), Gaussian(0.65)]:
    u, v = cop.sample(20_000, rng)
    mle = fit_cml(u, v, type(cop))
    tau_fit = fit_tau_inversion(u, v, type(cop))
    check(f"{cop.name} CML", abs(mle.theta - cop.theta) < 0.12 * max(1, abs(cop.theta)),
          f"true {cop.theta:.3f} → {mle.theta:.3f}")
    check(f"{cop.name} τ-inv", abs(tau_fit.theta - cop.theta) < 0.15 * max(1, abs(cop.theta)),
          f"true {cop.theta:.3f} → {tau_fit.theta:.3f}")


print("\n[10] select_family เลือกถูกเมื่อข้อมูลมาจาก family ที่รู้")
for truth in [Clayton(3.0), Gumbel(3.0), Frank(8.0)]:
    u, v = truth.sample(15_000, rng)
    ranked = select_family(u, v)
    check(f"ข้อมูลจาก {truth.name}", ranked[0]["family"] == truth.name,
          f"เลือก {ranked[0]['family']}, ΔAIC ถึงอันดับ 2 = "
          f"{ranked[1]['aic'] - ranked[0]['aic']:.1f}")


print("\n[11] pseudo-observations")
x = rng.normal(size=1000)
u = pseudo_obs(x)
check("อยู่ใน (0,1) เคร่งครัด", u.min() > 0 and u.max() < 1)
check("แบน (KS test)", stats.kstest(u, "uniform").pvalue > 0.01)
ru = rolling_pseudo_obs(x, 250)
check("rolling ไม่มี look-ahead (NaN ช่วงต้น)", np.all(np.isnan(ru[:250])))
check("rolling อยู่ใน (0,1)", np.nanmin(ru) > 0 and np.nanmax(ru) < 1)


print("\n[12] เครื่องมือฝั่งพอร์ตโฟลิโอ")
check("N_eff: 20 สถานะ ρ̄=0.15 → ~5.2",
      abs(effective_breadth(np.full((20, 20), 0.15) + np.eye(20) * 0.85) - 5.19) < 0.05)
check("N_eff: 20 สถานะ ρ̄=0.70 → ~1.4",
      abs(effective_breadth(np.full((20, 20), 0.70) + np.eye(20) * 0.30) - 1.40) < 0.05)
check("N_eff: อิสระเต็มที่ → N", abs(effective_breadth(np.eye(8)) - 8.0) < 1e-9)

# half-life ของ AR(1) ที่รู้คำตอบ
b = 0.9
e = np.zeros(200_000)
noise = rng.normal(scale=0.1, size=200_000)
for i in range(1, len(e)):
    e[i] = b * e[i - 1] + noise[i]
hl = half_life(e)
check("half-life ของ AR(1) b=0.9 → ln2/−ln0.9 ≈ 6.58",
      abs(hl - np.log(2) / -np.log(b)) < 0.2, f"got {hl:.2f}")
check("half-life ของ random walk → inf", half_life(np.cumsum(rng.normal(size=5000))) == np.inf)


print("\n[13] สัญญาณและการวินิจฉัย")
cop = Clayton(2.0)
u, v = cop.sample(5000, rng)
mi = mispricing_index(cop, u, v)
check("MI อยู่ใน [−0.5, 0.5]", mi.min() >= -0.5 and mi.max() <= 0.5)
check("MI เฉลี่ย ≈ 0", abs(mi.mean()) < 0.02, f"got {mi.mean():.4f}")

# ตัวเลขที่ใช้เป็นตัวอย่างในบทที่ 7 ต้องตรงกับที่หนังสือเขียนไว้
h_a = float(Clayton(2.0).h(np.array(0.15), np.array(0.60)))
h_b = float(Clayton(2.0).h(np.array(0.15), np.array(0.10)))
check("บทที่ 7 ตัวอย่าง A: h(0.15|0.60) ≈ 0.0147", abs(h_a - 0.0147) < 0.0005, f"got {h_a:.4f}")
check("บทที่ 7 ตัวอย่าง B: h(0.15|0.10) ≈ 0.582", abs(h_b - 0.582) < 0.002, f"got {h_b:.4f}")

# bucket diagnostic: สัญญาณที่ทำนายได้จริงต้องออกมา monotone
sig = rng.normal(size=20_000)
fwd = 0.3 * sig + rng.normal(size=20_000)
means = [b["mean_fwd_return"] for b in bucket_forward_return(sig, fwd)]
check("bucket monotone เมื่อมีความสัมพันธ์จริง", all(np.diff(means) > 0))
fwd_noise = rng.normal(size=20_000)
means_n = [b["mean_fwd_return"] for b in bucket_forward_return(sig, fwd_noise)]
check("bucket ไม่ monotone เมื่อเป็น noise", not all(np.diff(means_n) > 0))

# λ ตามทฤษฎีของ Student-t ตรงกับตารางในบทที่ 4
for rho, nu, want in [(0.5, 4, 0.25), (0.5, 8, 0.12), (0.8, 4, 0.49), (0.8, 8, 0.34)]:
    got = StudentT(rho, nu).lambda_upper()
    check(f"บทที่ 4 ตาราง λ (ρ={rho}, ν={nu}) ≈ {want}", abs(got - want) < 0.01,
          f"got {got:.3f}")


print(f"\n{'='*60}")
print(f"ผ่าน {len(PASS)} / {len(PASS) + len(FAIL)}")
if FAIL:
    print("ไม่ผ่าน:")
    for f in FAIL:
        print(f"  - {f}")
print(f"{'='*60}")
sys.exit(1 if FAIL else 0)
