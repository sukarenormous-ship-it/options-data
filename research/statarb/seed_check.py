"""เช็คว่าเลขบวกในเคส NONE เป็น edge จริงหรือ noise จาก seed เดียว"""
import numpy as np
from engine import BacktestEngine, summarize
from plumbing_test import SYMBOLS, make_data
from signals import CarrySignal, MomentumSignal

for edge, gens in [('none', [CarrySignal, MomentumSignal]), ('momentum', [CarrySignal])]:
    for G in gens:
        sh = []
        for seed in range(1, 9):
            r, f = make_data(edge, n_bars=3000, seed=seed)
            pnl, _ = BacktestEngine(r, f, SYMBOLS, G()).run()
            sh.append(summarize(pnl)['sharpe'])
        sh = np.array(sh)
        print(f"edge={edge:9s} signal={G().name:9s} Sharpe mean={sh.mean():6.2f} "
              f"sd={sh.std():5.2f}  t={sh.mean()/(sh.std()/np.sqrt(len(sh))):6.2f}  {np.round(sh,2)}")
