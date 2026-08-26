"""
Signal layer สำหรับ stat-arb engine

แนวคิด: ตัว engine (PCA / solver / accounting) ไม่ควรรู้ว่า signal มาจากไหน
มันแค่ขอ "น้ำหนักที่อยากได้ต่อสินทรัพย์" แล้วเอาไป neutralize + optimize ต่อ
ดังนั้นการเปลี่ยนกลยุทธ์ = สลับ SignalGenerator ตัวเดียว ไม่ต้องแตะ engine

SIGN CONVENTION (สำคัญ):
    generate() คืนค่าเป็น "ทิศทางน้ำหนักที่ต้องการ" ตรงๆ
    บวก = อยากถือ long, ลบ = อยากถือ short
    optimizer จะดึง w เข้าหาค่านี้โดยไม่กลับเครื่องหมายอีก
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd
from scipy import stats


# ==============================================================================
# Context ที่ engine ส่งให้ signal generator ทุกแท่ง
# ==============================================================================
@dataclass
class SignalContext:
    t: int                        # index ของแท่งที่กำลังจะเทรด
    timestamp: pd.Timestamp
    symbols: List[str]
    returns_hist: pd.DataFrame    # ผลตอบแทนถึงแท่ง t-1 (ไม่รวม t — กัน look-ahead)
    funding_hist: pd.DataFrame    # funding ถึงแท่ง t-1
    cum_resids: np.ndarray        # (W, N) cumulative PCA residual ของ window ปัจจุบัน
    loadings: np.ndarray          # (N, K) factor loadings
    current_w: pd.Series          # น้ำหนักที่ถืออยู่ก่อนรีบาลานซ์
    holding_bars: Dict[str, int]  # ถือมากี่แท่งแล้ว


@dataclass
class SignalOutput:
    """
    target: ทิศทางน้ำหนักที่ต้องการ (index = symbols)
    force_flat: ชื่อที่ต้อง "ปิดจริง" — ข้าม hysteresis และถูก bound ที่ (0,0)
                ใน optimizer เพื่อไม่ให้ constraint โยนน้ำหนักกลับมาให้
    stats: ตัวนับสำหรับ diagnostic
    """
    target: pd.Series
    force_flat: Set[str] = field(default_factory=set)
    stats: Dict[str, int] = field(default_factory=dict)


class SignalGenerator(ABC):
    name: str = "base"
    lookback: int = 0   # ต้องการ history กี่แท่งก่อนเริ่มเทรดได้

    @abstractmethod
    def generate(self, ctx: SignalContext) -> SignalOutput:
        ...

    @staticmethod
    def _cross_sectional_z(s: pd.Series) -> pd.Series:
        """z-score ตัดขวาง — พอร์ตเป็น dollar-neutral อยู่แล้ว จึงสนใจแค่ลำดับสัมพัทธ์"""
        sd = s.std()
        if not np.isfinite(sd) or sd < 1e-12:
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / sd


# ==============================================================================
# 1. RESIDUAL MEAN REVERSION (Avellaneda-Lee) — ของเดิม แก้บั๊กแล้ว
# ==============================================================================
class ResidualReversionSignal(SignalGenerator):
    name = "residual_reversion"

    def __init__(self,
                 entry_threshold: float = 1.20,
                 squeeze_breaker: float = 2.50,
                 hurst_max: float = 0.50,
                 use_hurst: bool = False,
                 max_holding_hl_mult: float = 2.0,
                 min_time_stop_bars: int = 2,
                 lambda_funding: float = 0.30,
                 funding_scale: float = 0.0001,
                 lookback: int = 42):
        self.entry_threshold = entry_threshold
        self.squeeze_breaker = squeeze_breaker
        self.hurst_max = hurst_max
        # ปิด Hurst เป็นค่าเริ่มต้น: บน window 42 จุด lag ถึง 15 ค่าที่ได้เป็น noise
        # ต้องการอย่างน้อย ~500 จุดถึงจะมีความหมาย
        self.use_hurst = use_hurst
        self.max_holding_hl_mult = max_holding_hl_mult
        self.min_time_stop_bars = min_time_stop_bars
        self.lambda_funding = lambda_funding
        self.funding_scale = funding_scale
        self.lookback = lookback

    @staticmethod
    def hurst_exponent(ts: np.ndarray, max_lag: int = 16) -> float:
        if len(ts) < max_lag * 2:
            return 0.5
        lags = np.arange(2, max_lag)
        tau = np.array([np.std(ts[lag:] - ts[:-lag]) for lag in lags])
        if np.any(tau <= 0):
            return 0.5
        # H = slope ของ log(std ของ lagged diff) เทียบ log(lag) โดยตรง
        # (ของเดิมใช้ sqrt แล้วคูณ 2 ซึ่งหักล้างกันพอดี แต่เขียนสับสน)
        return float(np.polyfit(np.log(lags), np.log(tau), 1)[0])

    @staticmethod
    def fit_ou(s_ts: np.ndarray) -> tuple:
        """
        fit OU: ds = -theta*(s - mu)dt + sigma dW
        คืน (theta, mu, sigma_eq) โดย sigma_eq = sigma/sqrt(2*theta) คือ SD สมดุล
        """
        s_lag, s_diff = s_ts[:-1], np.diff(s_ts)
        slope, intercept, _, _, _ = stats.linregress(s_lag, s_diff)
        theta = -slope
        if theta <= 1e-6:
            return 0.0, float(np.mean(s_ts)), float(np.std(s_ts))
        mu = intercept / theta
        resid_var = np.var(s_diff - (slope * s_lag + intercept))
        sigma_eq = np.sqrt(resid_var / (2.0 * theta)) if resid_var > 0 else np.std(s_ts)
        return float(theta), float(mu), float(sigma_eq)

    def generate(self, ctx: SignalContext) -> SignalOutput:
        target, force_flat = {}, set()
        st = {'hurst_filtered': 0, 'squeeze_cuts': 0, 'time_stops': 0, 'entries': 0}

        for i, sym in enumerate(ctx.symbols):
            s_ts = ctx.cum_resids[:, i]
            theta, mu, sigma_eq = self.fit_ou(s_ts)

            # s-score ตามสูตร A-L จริง: หารด้วย sigma สมดุลของ OU
            # ไม่ใช่ np.std ของ cumsum ซึ่ง non-stationary (โตตาม sqrt(T))
            s_score = (s_ts[-1] - mu) / (sigma_eq if sigma_eq > 1e-12 else 1.0)

            avg_fund = ctx.funding_hist[sym].iloc[-6:].mean()
            adj_s = s_score + self.lambda_funding * (avg_fund / self.funding_scale)

            # --- time stop: มี floor กัน int() ปัดเป็น 0 แล้วบังคับปิดทุกแท่ง
            if abs(ctx.current_w[sym]) > 1e-9:
                hl = np.log(2) / theta if theta > 0 else 18.0
                limit = max(self.min_time_stop_bars, int(self.max_holding_hl_mult * hl))
                if ctx.holding_bars[sym] >= limit:
                    target[sym] = 0.0
                    force_flat.add(sym)
                    st['time_stops'] += 1
                    continue

            # --- squeeze breaker: ต้องปิดจริง ไม่ใช่แค่ตั้ง signal = 0
            if abs(adj_s) >= self.squeeze_breaker:
                target[sym] = 0.0
                force_flat.add(sym)
                st['squeeze_cuts'] += 1
                continue

            if abs(adj_s) < self.entry_threshold:
                target[sym] = 0.0
                continue

            if self.use_hurst and self.hurst_exponent(s_ts) >= self.hurst_max:
                target[sym] = 0.0
                st['hurst_filtered'] += 1
                continue

            # mean reversion: s สูง = ยืดขึ้นเกิน = อยากขาย -> น้ำหนักลบ
            target[sym] = -adj_s
            st['entries'] += 1

        return SignalOutput(pd.Series(target).reindex(ctx.symbols).fillna(0.0),
                            force_flat, st)


# ==============================================================================
# 2. FUNDING CARRY
# ==============================================================================
class CarrySignal(SignalGenerator):
    """
    Perp funding เป็นบวกโดยโครงสร้าง (retail ฝั่ง long จ่ายให้ฝั่ง short)
    funding บวกสูง -> ถือ short แล้วได้รับเงิน -> น้ำหนักลบ

    risk-adjust ด้วย vol: ไม่ไปเก็บ carry ในเหรียญที่แกว่งจนกลบ carry
    """
    name = "carry"

    def __init__(self, smooth_bars: int = 42, vol_bars: int = 42,
                 risk_adjust: bool = True, min_abs_z: float = 0.0):
        self.smooth_bars = smooth_bars
        self.vol_bars = vol_bars
        self.risk_adjust = risk_adjust
        self.min_abs_z = min_abs_z
        self.lookback = max(smooth_bars, vol_bars) + 1

    def generate(self, ctx: SignalContext) -> SignalOutput:
        # funding ดิบ spiky มาก ต้องเฉลี่ยก่อนถึงจะเป็นตัวประมาณ carry ที่คาดหวัง
        expected_funding = ctx.funding_hist[ctx.symbols].iloc[-self.smooth_bars:].mean()

        if self.risk_adjust:
            vol = ctx.returns_hist[ctx.symbols].iloc[-self.vol_bars:].std()
            expected_funding = expected_funding / vol.replace(0, np.nan)
            expected_funding = expected_funding.fillna(0.0)

        # เครื่องหมายลบ: funding สูง -> short เพื่อรับ funding
        sig = -self._cross_sectional_z(expected_funding)

        if self.min_abs_z > 0:
            sig[sig.abs() < self.min_abs_z] = 0.0

        return SignalOutput(sig.reindex(ctx.symbols).fillna(0.0), set(),
                            {'entries': int((sig != 0).sum())})


# ==============================================================================
# 3. CROSS-SECTIONAL MOMENTUM
# ==============================================================================
class MomentumSignal(SignalGenerator):
    """
    Momentum ตัดขวาง 1-4 สัปดาห์ (Liu/Tsyvinski/Wu พบใน crypto)

    skip_bars: ข้ามช่วงล่าสุดทิ้ง เพราะช่วง 1-2 วันหลังสุดมี short-term reversal
               ปนอยู่ ซึ่งจะหักล้าง momentum (หลักการเดียวกับ 12-1 momentum ในหุ้น)

    ไม่ต้อง de-factor เอง — solver บังคับ B^T w = 0 อยู่แล้ว
    ผลลัพธ์จึงเป็น residual momentum โดยปริยาย
    """
    name = "momentum"

    def __init__(self, mom_bars: int = 180, skip_bars: int = 6,
                 vol_bars: int = 42, risk_adjust: bool = True):
        self.mom_bars = mom_bars
        self.skip_bars = skip_bars
        self.vol_bars = vol_bars
        self.risk_adjust = risk_adjust
        self.lookback = mom_bars + skip_bars + 1

    def generate(self, ctx: SignalContext) -> SignalOutput:
        r = ctx.returns_hist[ctx.symbols]
        end = len(r) - self.skip_bars
        window = r.iloc[end - self.mom_bars:end]
        cum_ret = (1.0 + window).prod() - 1.0

        if self.risk_adjust:
            vol = r.iloc[-self.vol_bars:].std() * np.sqrt(self.mom_bars)
            cum_ret = cum_ret / vol.replace(0, np.nan)
            cum_ret = cum_ret.fillna(0.0)

        # momentum: ตัวที่วิ่งขึ้น -> long (เครื่องหมายบวก ตรงข้ามกับ reversion)
        sig = self._cross_sectional_z(cum_ret)
        return SignalOutput(sig.reindex(ctx.symbols).fillna(0.0), set(),
                            {'entries': int((sig != 0).sum())})


# ==============================================================================
# 4. COMPOSITE — ผสมหลาย signal
# ==============================================================================
class CompositeSignal(SignalGenerator):
    """
    ผสม z-score ของหลาย signal ตามน้ำหนักที่กำหนด

    ข้อควรระวัง: carry กับ momentum มักขัดกันเอง — เหรียญที่ funding สูง
    คือเหรียญที่คนแห่ long ซึ่งมักเป็นเหรียญที่เพิ่งวิ่งขึ้น การผสมจึงลด
    ความผันผวนได้จริง แต่ก็ทอน gross signal ลงด้วย ต้องวัดผลจริงก่อนเชื่อ
    """
    name = "composite"

    def __init__(self, parts: List[tuple]):   # [(SignalGenerator, weight), ...]
        self.parts = parts
        self.lookback = max(g.lookback for g, _ in parts)
        self.name = "composite(" + "+".join(g.name for g, _ in parts) + ")"

    def generate(self, ctx: SignalContext) -> SignalOutput:
        total = pd.Series(0.0, index=ctx.symbols)
        force_flat, st = set(), {}
        for gen, wgt in self.parts:
            out = gen.generate(ctx)
            total = total.add(self._cross_sectional_z(out.target) * wgt, fill_value=0.0)
            force_flat |= out.force_flat
            for k, v in out.stats.items():
                st[f"{gen.name}.{k}"] = st.get(f"{gen.name}.{k}", 0) + v
        total[list(force_flat)] = 0.0
        return SignalOutput(total.reindex(ctx.symbols).fillna(0.0), force_flat, st)
