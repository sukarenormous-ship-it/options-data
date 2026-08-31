"""
copula_toolkit — ชุดเครื่องมือขนาดเล็กประกอบหนังสือ "Copula สำหรับ Statistical Arbitrage"

เขียนให้อ่านง่ายก่อนเร็ว — ทุกฟังก์ชันมีสูตรกำกับไว้ตรงกับภาคผนวก A

ต้องการ: numpy, scipy
ทดสอบ:  python3 book/copula/code/test_toolkit.py
"""

from __future__ import annotations

import numpy as np
from scipy import integrate, optimize, stats
from scipy.special import gammaln

EPS = 1e-10


# ─────────────────────────────────────────────────────────────
# 1. Marginal → pseudo-observations  (บทที่ 2)
# ─────────────────────────────────────────────────────────────

def pseudo_obs(x):
    """แปลงเป็น percentile ของตัวเอง: û = rank/(n+1)

    หารด้วย n+1 ไม่ใช่ n เพื่อไม่ให้มีค่าเป็น 1 พอดี ซึ่งจะทำให้
    copula density หลายตัวระเบิด
    """
    x = np.asarray(x, dtype=float)
    return stats.rankdata(x) / (len(x) + 1.0)


def rolling_pseudo_obs(x, window):
    """PIT แบบไม่มี look-ahead: u_t คำนวณจากข้อมูลถึง t เท่านั้น

    คืน array ที่ตำแหน่งแรก ๆ (< window) เป็น NaN

    นี่คือเวอร์ชันที่ต้องใช้ใน backtest — เวอร์ชัน pseudo_obs() ด้านบน
    ใช้ข้อมูลทั้งชุดรวมอนาคต จึงใช้ได้เฉพาะตอนวิเคราะห์ย้อนหลัง
    (ดูบทที่ 5 หัวข้อ 5.6 กับดัก 3)
    """
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    for t in range(window, len(x)):
        hist = x[t - window:t]                    # อดีตล้วน ไม่รวมวันนี้
        rank = np.sum(hist <= x[t]) + 1.0         # อันดับของวันนี้ในกลุ่ม window+1 ค่า
        out[t] = rank / (window + 2.0)            # หาร window+2 เพื่อให้อยู่ใน (0,1) เคร่งครัด
    return out


# ─────────────────────────────────────────────────────────────
# 2. Copula families  (บทที่ 4, ภาคผนวก A.3)
# ─────────────────────────────────────────────────────────────

class Copula:
    """ฐานร่วม — ลูกต้อง implement cdf, logpdf, h, tau_to_theta, bounds"""

    name = "base"
    param_bounds = (-np.inf, np.inf)
    n_params = 1               # ลูกที่มีพารามิเตอร์มากกว่าหนึ่งตัวต้อง override

    def __init__(self, theta):
        self.theta = float(theta)

    def __repr__(self):
        return f"{self.name}(theta={self.theta:.4f})"

    # --- ต้อง override ---
    def cdf(self, u, v):
        raise NotImplementedError

    def logpdf(self, u, v):
        raise NotImplementedError

    def h(self, u, v):
        """h(u|v) = ∂C(u,v)/∂v = P(U ≤ u | V = v)"""
        raise NotImplementedError

    @staticmethod
    def tau_to_theta(tau):
        raise NotImplementedError

    # --- ใช้ร่วมกันได้ ---
    def lambda_lower(self):
        return 0.0

    def lambda_upper(self):
        return 0.0

    def h_inv(self, w, v):
        """หา u ที่ทำให้ h(u|v) = w — ใช้ bisection แบบ vectorized

        ใช้สำหรับสุ่มตัวอย่างด้วยวิธี conditional inversion
        """
        w = np.clip(np.asarray(w, dtype=float), EPS, 1 - EPS)
        v = np.clip(np.asarray(v, dtype=float), EPS, 1 - EPS)
        lo = np.full_like(w, EPS)
        hi = np.full_like(w, 1 - EPS)
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            too_small = self.h(mid, v) < w
            lo = np.where(too_small, mid, lo)
            hi = np.where(too_small, hi, mid)
        return 0.5 * (lo + hi)

    def sample(self, n, rng=None):
        """สุ่ม (u,v) ด้วย conditional inversion: v ~ U(0,1), u = h⁻¹(w|v)"""
        rng = np.random.default_rng(rng)
        v = rng.uniform(EPS, 1 - EPS, n)
        w = rng.uniform(EPS, 1 - EPS, n)
        return self.h_inv(w, v), v


class Clayton(Copula):
    """หนาที่มุมซ้ายล่าง — 'ร่วงพร้อมกัน แต่ขึ้นแยกกัน'"""

    name = "Clayton"
    param_bounds = (1e-4, 50.0)

    def cdf(self, u, v):
        t = self.theta
        return np.clip(u ** -t + v ** -t - 1.0, EPS, None) ** (-1.0 / t)

    def logpdf(self, u, v):
        t = self.theta
        s = np.clip(u ** -t + v ** -t - 1.0, EPS, None)
        return (np.log1p(t)
                - (t + 1.0) * (np.log(u) + np.log(v))
                - (1.0 / t + 2.0) * np.log(s))

    def h(self, u, v):
        t = self.theta
        s = np.clip(u ** -t + v ** -t - 1.0, EPS, None)
        return v ** (-t - 1.0) * s ** (-1.0 / t - 1.0)

    def h_inv(self, w, v):
        # มีรูปปิด ไม่ต้อง bisection
        t = self.theta
        a = (w * v ** (t + 1.0)) ** (-t / (1.0 + t))
        return np.clip(a - v ** -t + 1.0, EPS, None) ** (-1.0 / t)

    @staticmethod
    def tau_to_theta(tau):
        tau = np.clip(tau, 1e-4, 0.95)
        return 2.0 * tau / (1.0 - tau)

    def lambda_lower(self):
        return 2.0 ** (-1.0 / self.theta)


class Gumbel(Copula):
    """หนาที่มุมขวาบน — 'พุ่งพร้อมกัน'"""

    name = "Gumbel"
    param_bounds = (1.0 + 1e-6, 30.0)

    def _A(self, u, v):
        t = self.theta
        x = -np.log(u)
        y = -np.log(v)
        return x, y, (x ** t + y ** t) ** (1.0 / t)

    def cdf(self, u, v):
        _, _, A = self._A(u, v)
        return np.exp(-A)

    def logpdf(self, u, v):
        t = self.theta
        x, y, A = self._A(u, v)
        # c = C · (xy)^(θ−1)/(uv) · A^(1−2θ) · (A + θ − 1)
        return (-A
                + (t - 1.0) * (np.log(x) + np.log(y))
                - np.log(u) - np.log(v)
                + (1.0 - 2.0 * t) * np.log(A)
                + np.log(A + t - 1.0))

    def h(self, u, v):
        t = self.theta
        _, y, A = self._A(u, v)
        return np.exp(-A) * (1.0 / v) * y ** (t - 1.0) * A ** (1.0 - t)

    @staticmethod
    def tau_to_theta(tau):
        tau = np.clip(tau, 0.0, 0.95)
        return 1.0 / (1.0 - tau)

    def lambda_upper(self):
        return 2.0 - 2.0 ** (1.0 / self.theta)


class Frank(Copula):
    """dependence ที่แรงตรงกลาง แต่ไม่มี tail dependence — รองรับค่าลบ"""

    name = "Frank"
    param_bounds = (-35.0, 35.0)

    def cdf(self, u, v):
        t = self.theta
        D = np.expm1(-t)
        return -np.log1p(np.expm1(-t * u) * np.expm1(-t * v) / D) / t

    def logpdf(self, u, v):
        # c = θ(1−e^−θ)·e^(−θ(u+v)) / [ (1−e^−θ) − (1−e^(−θu))(1−e^(−θv)) ]²
        t = self.theta
        A = -np.expm1(-t)           # = 1 − e^(−θ)
        B = -np.expm1(-t * u)       # = 1 − e^(−θu)
        Cv = -np.expm1(-t * v)      # = 1 − e^(−θv)
        num = t * A * np.exp(-t * (u + v))
        den = (A - B * Cv) ** 2
        return np.log(np.abs(num)) - np.log(den)

    def h(self, u, v):
        t = self.theta
        gu = np.expm1(-t * u)
        gv = np.expm1(-t * v)
        D = np.expm1(-t)
        return np.exp(-t * v) * gu / (D + gu * gv)

    @staticmethod
    def _tau(theta):
        """tau(theta) = 1 - 4/theta + 4*D1(theta)/theta

        ใกล้ theta = 0 ต้องใช้อนุกรม เพราะ -4/theta กับ 4*D1/theta หักล้างกัน
        เกือบหมด ความคลาดเคลื่อนเชิงตัวเลขจึงถูกขยายด้วย 1/theta
        """
        if abs(theta) < 1e-4:
            return theta / 9.0 - theta ** 3 / 900.0
        d1 = integrate.quad(lambda x: 1.0 if x == 0.0 else x / np.expm1(x),
                            0.0, theta)[0] / theta
        return 1.0 - 4.0 / theta + 4.0 * d1 / theta

    @staticmethod
    def tau_to_theta(tau):
        """ไม่มีรูปปิด - แก้เชิงตัวเลขจาก tau(theta)

        โดเมน theta ตาม param_bounds เอื้อมถึง |tau| <= 0.891 เท่านั้น
        ค่าที่เกินจะถูก clip (ในทางทฤษฎี Frank รองรับ tau ได้ทั้ง (-1, 1))
        """
        lo, hi = Frank.param_bounds
        tau_max = Frank._tau(hi) * (1 - 1e-9)
        tau = float(np.clip(tau, -tau_max, tau_max))
        if abs(tau) < 1e-8:
            return 1e-8

        def f(t):
            return Frank._tau(t) - tau

        return (optimize.brentq(f, 1e-8, hi) if tau > 0
                else optimize.brentq(f, lo, -1e-8))

class Gaussian(Copula):
    """elliptical, สมมาตร, ไม่มี tail dependence"""

    name = "Gaussian"
    param_bounds = (-0.999, 0.999)

    def cdf(self, u, v):
        x = stats.norm.ppf(np.clip(u, EPS, 1 - EPS))
        y = stats.norm.ppf(np.clip(v, EPS, 1 - EPS))
        mvn = stats.multivariate_normal(mean=[0, 0],
                                        cov=[[1, self.theta], [self.theta, 1]])
        pts = np.column_stack([np.atleast_1d(x), np.atleast_1d(y)])
        return np.array([mvn.cdf(p) for p in pts]).reshape(np.shape(u))

    def logpdf(self, u, v):
        r = self.theta
        x = stats.norm.ppf(np.clip(u, EPS, 1 - EPS))
        y = stats.norm.ppf(np.clip(v, EPS, 1 - EPS))
        return (-0.5 * np.log(1 - r ** 2)
                - (r ** 2 * (x ** 2 + y ** 2) - 2 * r * x * y) / (2 * (1 - r ** 2)))

    def h(self, u, v):
        r = self.theta
        x = stats.norm.ppf(np.clip(u, EPS, 1 - EPS))
        y = stats.norm.ppf(np.clip(v, EPS, 1 - EPS))
        return stats.norm.cdf((x - r * y) / np.sqrt(1 - r ** 2))

    @staticmethod
    def tau_to_theta(tau):
        return np.sin(np.pi * np.clip(tau, -0.99, 0.99) / 2.0)


class StudentT(Copula):
    """elliptical + tail dependence สมมาตร — default ที่ปลอดภัยที่สุด

    พารามิเตอร์: theta = ρ, nu = degrees of freedom
    """

    name = "StudentT"
    param_bounds = (-0.999, 0.999)
    n_params = 2               # rho และ nu

    def __init__(self, theta, nu=6.0):
        super().__init__(theta)
        self.nu = float(nu)

    def __repr__(self):
        return f"StudentT(rho={self.theta:.4f}, nu={self.nu:.2f})"

    def logpdf(self, u, v):
        r, nu = self.theta, self.nu
        x = stats.t.ppf(np.clip(u, EPS, 1 - EPS), nu)
        y = stats.t.ppf(np.clip(v, EPS, 1 - EPS), nu)
        q = (x ** 2 - 2 * r * x * y + y ** 2) / (nu * (1 - r ** 2))
        log_joint = (gammaln((nu + 2) / 2) - gammaln(nu / 2)
                     - np.log(nu * np.pi) - 0.5 * np.log(1 - r ** 2)
                     - (nu + 2) / 2 * np.log1p(q))
        return log_joint - stats.t.logpdf(x, nu) - stats.t.logpdf(y, nu)

    def h(self, u, v):
        r, nu = self.theta, self.nu
        x = stats.t.ppf(np.clip(u, EPS, 1 - EPS), nu)
        y = stats.t.ppf(np.clip(v, EPS, 1 - EPS), nu)
        scale = np.sqrt((nu + y ** 2) * (1 - r ** 2) / (nu + 1))
        return stats.t.cdf((x - r * y) / scale, nu + 1)

    @staticmethod
    def tau_to_theta(tau):
        return np.sin(np.pi * np.clip(tau, -0.99, 0.99) / 2.0)

    def _lambda(self):
        r, nu = self.theta, self.nu
        arg = -np.sqrt((nu + 1) * (1 - r) / (1 + r))
        return 2.0 * stats.t.cdf(arg, nu + 1)

    lambda_lower = _lambda
    lambda_upper = _lambda


FAMILIES = {c.name: c for c in (Clayton, Gumbel, Frank, Gaussian)}


# ─────────────────────────────────────────────────────────────
# 3. การประมาณค่า  (บทที่ 5)
# ─────────────────────────────────────────────────────────────

def fit_tau_inversion(u, v, family):
    """τ-inversion — เร็วและเสถียร เหมาะกับ rolling refit

    ไม่ต้อง optimize เลย จึงไม่มีปัญหาการลู่เข้า
    """
    tau = stats.kendalltau(u, v).statistic
    return family(family.tau_to_theta(tau))


def fit_cml(u, v, family):
    """CML — empirical marginal (ที่ทำมาแล้ว) + MLE บนพารามิเตอร์ copula

    หมายเหตุ: optimize พารามิเตอร์ตัวเดียว (scalar) เท่านั้น — ถ้าใช้กับ StudentT
    ค่า nu จะถูกตรึงที่ค่า default ไม่ได้ถูกประมาณจากข้อมูล
    """
    lo, hi = family.param_bounds

    def neg_ll(theta):
        try:
            val = -np.sum(family(theta).logpdf(u, v))
        except (FloatingPointError, ValueError):
            return 1e12
        return val if np.isfinite(val) else 1e12

    res = optimize.minimize_scalar(neg_ll, bounds=(lo, hi), method="bounded")
    return family(res.x)


def select_family(u, v, families=None):
    """เรียง family ตาม AIC — อ่าน *ช่องว่าง* ไม่ใช่แค่ผู้ชนะ (บทที่ 5 หัวข้อ 5.3)"""
    families = families or list(FAMILIES.values())
    rows = []
    for fam in families:
        try:
            cop = fit_cml(u, v, fam)
            ll = float(np.sum(cop.logpdf(u, v)))
            k = getattr(fam, "n_params", 1)
            rows.append({"family": fam.name, "copula": cop,
                         "loglik": ll, "aic": -2 * ll + 2 * k})
        except Exception as exc:                      # noqa: BLE001
            rows.append({"family": fam.name, "copula": None,
                         "loglik": np.nan, "aic": np.inf, "error": str(exc)})
    return sorted(rows, key=lambda r: r["aic"])


# ─────────────────────────────────────────────────────────────
# 4. เครื่องมือวินิจฉัย  (บทที่ 3, 8, 10, 12)
# ─────────────────────────────────────────────────────────────

def empirical_tail_dep(u, v, q, side="lower"):
    """λ̂(q) จากข้อมูล — ดูว่ามันลู่เข้าหาเลขที่ไม่ใช่ 0 ไหมเมื่อ q → ขอบ

    ระวัง: ที่ q เล็กมาก ตัวส่วนเหลือไม่กี่จุด อย่าอ่านจุดสุดท้ายเป็นคำตอบ
    """
    u, v = np.asarray(u), np.asarray(v)
    if side == "lower":
        cond = u <= q
        both = cond & (v <= q)
    else:
        cond = u > 1 - q
        both = cond & (v > 1 - q)
    n = cond.sum()
    return np.nan if n == 0 else both.sum() / n


def mispricing_index(cop, u, v):
    """MI_{A|B} = h(u|v) − 0.5   ∈ [−0.5, +0.5]   (บทที่ 7)"""
    return cop.h(u, v) - 0.5


def bucket_forward_return(signal, fwd_return, n_buckets=10):
    """ผลตอบแทนข้างหน้าเฉลี่ยแยกตามถังสัญญาณ

    สิ่งที่ต้องมองหาคือ monotonicity — ถ้าไม่มี แปลว่าไม่ใช่ edge
    ที่มีโครงสร้าง (บทที่ 8 หัวข้อ 8.6, บทที่ 12 หัวข้อ 12.4)
    """
    signal = np.asarray(signal, dtype=float)
    fwd_return = np.asarray(fwd_return, dtype=float)
    ok = np.isfinite(signal) & np.isfinite(fwd_return)
    signal, fwd_return = signal[ok], fwd_return[ok]

    edges = np.quantile(signal, np.linspace(0, 1, n_buckets + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    idx = np.digitize(signal, edges[1:-1])

    return [{"bucket": b + 1,
             "n": int(np.sum(idx == b)),
             "mean_signal": float(np.mean(signal[idx == b])) if np.any(idx == b) else np.nan,
             "mean_fwd_return": float(np.mean(fwd_return[idx == b])) if np.any(idx == b) else np.nan}
            for b in range(n_buckets)]


def effective_breadth(corr_matrix):
    """N_eff = N / (1 + (N−1)·ρ̄)   (บทที่ 10)

    เรียกสองครั้ง: ครั้งหนึ่งด้วย correlation ปกติ อีกครั้งด้วย
    correlation เฉพาะวันที่แย่ที่สุด — แล้วตั้ง limit จากตัวที่สอง
    """
    C = np.asarray(corr_matrix, dtype=float)
    n = C.shape[0]
    if n < 2:
        return float(n)
    off_diag = C[~np.eye(n, dtype=bool)]
    rho_bar = float(np.mean(off_diag))
    return n / (1.0 + (n - 1) * rho_bar)


def half_life(residual):
    """half-life ของ OU ประมาณจาก AR(1)  (ภาคผนวก A.6)

    คืน np.inf ในสองกรณีที่การแปลง kappa = -ln(b) ใช้ไม่ได้ ซึ่ง **ต่างกันมาก**:
      b >= 1  → ไม่มี mean reversion (random walk) — ไม่มีอะไรให้เทรด
      b <= 0  → autocorrelation ติดลบ คือแกว่งข้ามค่ากลางทุกก้าว

    และระวังข้อมูลที่ b ประมาณได้ใกล้ 0 (เช่นอนุกรมที่ถูกสลับลำดับ) — ค่าที่ได้
    จะไร้ความหมาย บางครั้ง inf บางครั้งเกือบศูนย์ แล้วแต่เศษ noise (บทที่ 8)
    """
    e = np.asarray(residual, dtype=float)
    e = e[np.isfinite(e)]
    x, y = e[:-1], e[1:]
    b = np.polyfit(x, y, 1)[0]
    if b <= 0 or b >= 1:
        return np.inf
    return float(np.log(2) / -np.log(b))
