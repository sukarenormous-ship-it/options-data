"""
Stat-arb backtest engine — ส่วนที่ไม่ขึ้นกับกลยุทธ์

engine รับผิดชอบ: rolling PCA + shrinkage, constrained optimization,
hysteresis, การคิดค่าธรรมเนียม/funding, และ accounting
ตัว alpha ทั้งหมดอยู่ใน signals.py
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from signals import SignalContext, SignalGenerator, SignalOutput


class Config:
    TIMEFRAME = '4h'
    BAR_HOURS = 4
    FUNDING_INTERVAL_HOURS = 8      # Binance จ่าย funding ทุก 8 ชม. ไม่ใช่ทุกแท่ง

    FACTOR_WINDOW = 42              # window สำหรับ PCA/covariance
    N_FACTORS = 2

    HYSTERESIS_BUFFER = 0.020
    GROSS_LEVERAGE = 1.0
    MAX_CAP_PER_ASSET = 0.12

    MAKER_FEE_PCT = 0.00020
    SLIPPAGE_PCT = 0.00005


# ==============================================================================
# สถิติ
# ==============================================================================
class StatEngine:
    @staticmethod
    def ledoit_wolf_shrinkage(returns: np.ndarray) -> np.ndarray:
        """
        Ledoit-Wolf shrinkage ไปหา scaled identity

        เวอร์ชัน vectorized ของ b_bar = sum_t ||x_t x_t' - S||_F^2 :
            ||x_t x_t' - S||_F^2 = (x_t'x_t)^2 - 2 x_t'S x_t + ||S||_F^2
        ให้ผลเท่ากับลูป Python เป๊ะ แต่เร็วกว่ามากเพราะรันทุกแท่ง
        """
        T, N = returns.shape
        y = returns - returns.mean(axis=0)
        sample_cov = (y.T @ y) / max(T - 1, 1)

        mu = np.trace(sample_cov) / N
        target = mu * np.eye(N)
        d_sq = np.sum((sample_cov - target) ** 2)

        sq = np.einsum('ij,ij->i', y, y)
        quad = np.einsum('ij,jk,ik->i', y, sample_cov, y)
        b_bar = np.sum(sq ** 2) - 2.0 * np.sum(quad) + T * np.sum(sample_cov ** 2)
        b_sq = min(b_bar / (T ** 2), d_sq)

        delta = float(np.clip(b_sq / (d_sq + 1e-12), 0.0, 1.0))
        return (1.0 - delta) * sample_cov + delta * target

    @staticmethod
    def extract_factors_and_residuals(window: pd.DataFrame,
                                      n_factors: int) -> Tuple[np.ndarray, np.ndarray]:
        norm = (window - window.mean()) / (window.std() + 1e-8)
        shrunk = StatEngine.ledoit_wolf_shrinkage(norm.values)
        eig_vals, eig_vecs = np.linalg.eigh(shrunk)
        loadings = eig_vecs[:, np.argsort(eig_vals)[::-1]][:, :n_factors]
        residuals = norm.values - (norm.values @ loadings) @ loadings.T
        return loadings, residuals


# ==============================================================================
# Optimizer
# ==============================================================================
class PortfolioOptimizer:
    @staticmethod
    def solve(target: pd.Series,
              loadings: np.ndarray,
              max_caps: np.ndarray,
              gross_leverage: float,
              force_flat_mask: np.ndarray) -> Tuple[pd.Series, bool]:
        """
        min  0.5*||w - c||^2 + 0.01*||w||^2
        s.t. sum(w) = 0,  B^T w = 0,  -cap <= w <= cap
             และ w_i = 0 สำหรับชื่อที่สั่งปิด (bound เป็น (0,0))

        c = target ตรงๆ ไม่กลับเครื่องหมาย — signal layer ให้ทิศทางน้ำหนักมาแล้ว
        """
        n = len(target)
        c = target.values.astype(float)

        def objective(w):
            return 0.5 * np.sum((w - c) ** 2) + 0.01 * np.sum(w ** 2)

        def jac(w):
            return (w - c) + 0.02 * w

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w)}]
        for k in range(loadings.shape[1]):
            constraints.append({'type': 'eq',
                                'fun': lambda w, k=k: np.dot(w, loadings[:, k])})

        bounds = [(0.0, 0.0) if force_flat_mask[i] else (-max_caps[i], max_caps[i])
                  for i in range(n)]

        res = minimize(objective, np.zeros(n), method='SLSQP', jac=jac,
                       bounds=bounds, constraints=constraints,
                       options={'maxiter': 200, 'ftol': 1e-6})

        if not res.success:
            return pd.Series(0.0, index=target.index), False

        w = res.x
        gross = np.sum(np.abs(w))
        if gross > gross_leverage:
            w = w * (gross_leverage / gross)
        return pd.Series(w, index=target.index), True


# ==============================================================================
# Backtest
# ==============================================================================
class BacktestEngine:
    def __init__(self, returns_df: pd.DataFrame, funding_df: pd.DataFrame,
                 symbols: List[str], signal_gen: SignalGenerator,
                 cfg: Config = Config()):
        self.returns_df = returns_df[symbols]
        self.funding_df = funding_df[symbols]
        self.symbols = symbols
        self.signal_gen = signal_gen
        self.cfg = cfg
        self.max_caps = np.full(len(symbols), cfg.MAX_CAP_PER_ASSET)

        # funding ถูกคิดเฉพาะแท่งที่ตรงกับรอบจ่ายจริง (00/08/16 UTC)
        bars_per_funding = cfg.FUNDING_INTERVAL_HOURS // cfg.BAR_HOURS
        self.funding_due = (
            pd.Series(returns_df.index.hour, index=returns_df.index)
            % cfg.FUNDING_INTERVAL_HOURS == 0
        ) if bars_per_funding > 1 else pd.Series(True, index=returns_df.index)

    def run(self, apply_costs: bool = True) -> Tuple[pd.DataFrame, Dict]:
        cfg = self.cfg
        warmup = max(cfg.FACTOR_WINDOW, self.signal_gen.lookback)
        n = len(self.returns_df)
        if warmup >= n:
            raise ValueError(f"ข้อมูลไม่พอ: ต้องการ > {warmup} แท่ง มี {n}")

        current_w = pd.Series(0.0, index=self.symbols)
        holding = {s: 0 for s in self.symbols}
        history, agg_stats = [], {'solver_failures': 0}

        for t in range(warmup, n):
            ts = self.returns_df.index[t]

            window = self.returns_df.iloc[t - cfg.FACTOR_WINDOW:t]
            loadings, resids = StatEngine.extract_factors_and_residuals(
                window, cfg.N_FACTORS)

            for s in self.symbols:
                holding[s] = holding[s] + 1 if abs(current_w[s]) > 1e-9 else 0

            ctx = SignalContext(
                t=t, timestamp=ts, symbols=self.symbols,
                returns_hist=self.returns_df.iloc[:t],
                funding_hist=self.funding_df.iloc[:t],
                cum_resids=np.cumsum(resids, axis=0),
                loadings=loadings, current_w=current_w.copy(),
                holding_bars=dict(holding),
            )
            out: SignalOutput = self.signal_gen.generate(ctx)
            for k, v in out.stats.items():
                agg_stats[k] = agg_stats.get(k, 0) + v

            flat_mask = np.array([s in out.force_flat for s in self.symbols])
            target_w, ok = PortfolioOptimizer.solve(
                out.target, loadings, self.max_caps, cfg.GROSS_LEVERAGE, flat_mask)

            if not ok:
                # solver ล้ม -> คงพอร์ตเดิม ไม่ใช่ล้างพอร์ตเงียบๆ
                agg_stats['solver_failures'] += 1
                target_w = current_w.copy()

            delta_w = target_w - current_w
            orders = delta_w.copy()
            below_band = orders.abs() < cfg.HYSTERESIS_BUFFER
            below_band &= ~pd.Series(flat_mask, index=self.symbols)  # ปิดจริงต้องผ่านเสมอ
            orders[below_band] = 0.0

            turnover = orders.abs().sum()
            current_w = current_w + orders

            # ถ้าน้ำหนักพลิกข้าง = ไม้ใหม่ ต้องรีเซ็ตตัวนับเวลาถือ
            for s in self.symbols:
                if orders[s] != 0.0 and np.sign(current_w[s]) != np.sign(current_w[s] - orders[s]):
                    holding[s] = 0

            gross_ret = float((current_w * self.returns_df.iloc[t]).sum())
            fund_cost = (float((current_w * self.funding_df.iloc[t]).sum())
                         if self.funding_due.iloc[t] else 0.0)
            exec_cost = turnover * (cfg.MAKER_FEE_PCT + cfg.SLIPPAGE_PCT)

            net_ret = gross_ret - (exec_cost + fund_cost if apply_costs else 0.0)

            history.append({
                'timestamp': ts, 'gross_pnl': gross_ret, 'net_pnl': net_ret,
                'exec_cost': exec_cost, 'funding_cost': fund_cost,
                'turnover': turnover, 'gross_exposure': current_w.abs().sum(),
                'active_positions': int((current_w.abs() > 1e-9).sum()),
            })

        pnl = pd.DataFrame(history).set_index('timestamp')
        pnl['cum_net'] = (1 + pnl['net_pnl']).cumprod() * 100
        peak = pnl['cum_net'].cummax()
        pnl['drawdown'] = (pnl['cum_net'] - peak) / peak * 100
        return pnl, agg_stats


def summarize(pnl: pd.DataFrame, bars_per_year: int = 6 * 365) -> Dict:
    r = pnl['net_pnl']
    downside = r[r < 0].std()
    return {
        'net_return_pct': float(pnl['cum_net'].iloc[-1] - 100),
        'sharpe': float(r.mean() / r.std() * np.sqrt(bars_per_year)) if r.std() > 0 else 0.0,
        'sortino': float(r.mean() / downside * np.sqrt(bars_per_year)) if downside > 0 else 0.0,
        'max_dd_pct': float(pnl['drawdown'].min()),
        'turnover_daily_pct': float(pnl['turnover'].resample('1D').sum().mean() * 100),
        'avg_gross_exposure': float(pnl['gross_exposure'].mean()),
        'total_cost_pct': float((pnl['exec_cost'] + pnl['funding_cost']).sum() * 100),
    }
