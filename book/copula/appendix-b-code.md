# ภาคผนวก B — โค้ดที่รันได้จริง

> โค้ดทั้งหมดอยู่ใน [`code/`](code/) และผ่านการทดสอบแล้ว
> ต้องการ `numpy` และ `scipy`

---

## B.1 ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | หน้าที่ |
|---|---|
| [`code/copula_toolkit.py`](code/copula_toolkit.py) | ชุดเครื่องมือหลัก — copula 5 ตระกูล + การประมาณค่า + เครื่องมือวินิจฉัย |
| [`code/test_toolkit.py`](code/test_toolkit.py) | ชุดทดสอบ 78 ข้อ ยืนยันทุกสูตรกับผลต่างเชิงตัวเลข |
| [`code/example_repo_data.py`](code/example_repo_data.py) | ตัวอย่างเต็มขั้นตอน รันบนข้อมูล `data/` ของรีโปนี้ |
| [`code/build_web.py`](code/build_web.py) | สร้างหน้าอ่านออนไลน์หน้าเดียวจากไฟล์ markdown ทั้งเล่ม |

```bash
pip install numpy scipy

python3 book/copula/code/test_toolkit.py        # ควรได้ "ผ่าน 78 / 78"
python3 book/copula/code/example_repo_data.py   # วิเคราะห์ข้อมูลจริงในรีโป

pip install markdown                            # เฉพาะตอนสร้างหน้าเว็บ
python3 book/copula/code/build_web.py out.html  # รวมทั้งเล่มเป็นหน้าเดียว
```

---

## B.2 ทำไมต้องมีชุดทดสอบ

สูตร copula เต็มไปด้วยอนุพันธ์ที่ทำด้วยมือ และความผิดพลาดเครื่องหมายเดียว
จะให้ตัวเลขที่ **ดูสมเหตุสมผลแต่ผิด** ซึ่งเป็นความผิดพลาดชนิดที่แย่ที่สุด
เพราะไม่มีอะไรพัง มันแค่ให้คำตอบผิดเงียบ ๆ

วิธีที่ได้ผลที่สุดคือเทียบกับผลต่างเชิงตัวเลขของ CDF ซึ่งไม่ต้องพึ่ง
การทำอนุพันธ์ด้วยมือเลย:

```python
def numeric_h(cop, u, v, eps=1e-6):
    """h(u|v) = ∂C(u,v)/∂v ประมาณด้วยผลต่างกลาง"""
    return (cop.cdf(u, v + eps) - cop.cdf(u, v - eps)) / (2 * eps)

# ต้องตรงกับ cop.h(u, v) ที่เขียนด้วยมือ
```

การทดสอบนี้จับความผิดพลาดของอนุพันธ์ได้เกือบทั้งหมด และใช้เวลาเขียน
สิบนาที ชุดทดสอบยังตรวจอีกหลายชั้น:

```
[1]  h ตรงกับ ∂C/∂v เชิงตัวเลข             ทุก family
[2]  density ตรงกับ ∂²C/∂u∂v เชิงตัวเลข    ทุก family
[3]  Student-t density อินทิเกรตได้ 1
[4]  h เป็น CDF จริง (อยู่ใน [0,1], เพิ่มตาม u)
[5]  dependence → 0  ⟹  h(u|v) → u
[6]  h_inv กลับด้าน h ได้
[7]  λ ตามทฤษฎีตรงกับที่วัดจากตัวอย่างสุ่ม 200,000 จุด
[8]  τ-inversion กลับไปกลับมาได้
[9]  การประมาณค่ากู้พารามิเตอร์จริงคืนได้
[10] select_family เลือกถูกเมื่อรู้คำตอบ
[11] pseudo-observations แบนและอยู่ใน (0,1)
[12] N_eff และ half-life ตรงกับกรณีที่คำนวณมือได้
[13] ตัวเลขตัวอย่างในบทที่ 4 และ 7 ตรงกับที่หนังสือเขียนไว้จริง
```

ข้อสุดท้ายสำคัญ — **ตัวเลขทุกตัวที่ปรากฏในหนังสือเล่มนี้ถูกตรวจ
ด้วยโค้ดว่าไม่ได้พิมพ์ผิด**

---

## B.3 สูตรที่ต้องระวังเป็นพิเศษ

### PIT แบบไม่มี look-ahead

นี่คือ bug ที่เงียบที่สุดในงาน backtest สาย copula (บทที่ 5 หัวข้อ 5.6)

```python
def pseudo_obs(x):
    """ใช้ได้เฉพาะการวิเคราะห์ย้อนหลัง — ใช้ข้อมูลทั้งชุดรวมอนาคต"""
    return stats.rankdata(x) / (len(x) + 1.0)


def rolling_pseudo_obs(x, window):
    """เวอร์ชันที่ต้องใช้ใน backtest — u_t มาจากข้อมูลถึง t เท่านั้น"""
    out = np.full(len(x), np.nan)
    for t in range(window, len(x)):
        hist = x[t - window:t]                 # อดีตล้วน ไม่รวมวันนี้
        rank = np.sum(hist <= x[t]) + 1.0
        out[t] = rank / (window + 2.0)         # window+2 เพื่อให้อยู่ใน (0,1) เคร่งครัด
    return out
```

ตัวหารเป็น `window + 2` ไม่ใช่ `window + 1` — ถ้าใช้ `window + 1`
ค่าจะเป็น 1.0 พอดีได้เมื่อวันนี้สูงกว่าทุกวันในหน้าต่าง ซึ่งทำให้
copula density ระเบิด (นี่คือ bug จริงที่ชุดทดสอบจับได้ตอนเขียนหนังสือเล่มนี้)

### h-function ของแต่ละตระกูล

```python
class Clayton(Copula):
    def h(self, u, v):
        t = self.theta
        s = np.clip(u ** -t + v ** -t - 1.0, EPS, None)
        return v ** (-t - 1.0) * s ** (-1.0 / t - 1.0)

    def h_inv(self, w, v):                     # Clayton มีรูปปิด
        t = self.theta
        a = (w * v ** (t + 1.0)) ** (-t / (1.0 + t))
        return np.clip(a - v ** -t + 1.0, EPS, None) ** (-1.0 / t)


class Gumbel(Copula):
    def h(self, u, v):
        t = self.theta
        x, y = -np.log(u), -np.log(v)
        A = (x ** t + y ** t) ** (1.0 / t)
        return np.exp(-A) * (1.0 / v) * y ** (t - 1.0) * A ** (1.0 - t)


class Gaussian(Copula):
    def h(self, u, v):
        r = self.theta
        x, y = stats.norm.ppf(u), stats.norm.ppf(v)
        return stats.norm.cdf((x - r * y) / np.sqrt(1 - r ** 2))
```

ตระกูลที่ไม่มี `h_inv` รูปปิดใช้ bisection แบบ vectorized 80 รอบ
ซึ่งได้ความแม่นระดับ 1e-16 และเร็วพอสำหรับการสุ่มหลักแสนจุด

---

## B.4 การใช้งานพื้นฐาน

```python
import numpy as np
from copula_toolkit import (Clayton, Gumbel, StudentT, fit_cml,
                            fit_tau_inversion, select_family,
                            pseudo_obs, mispricing_index, empirical_tail_dep)

# 1. เตรียมข้อมูล
u = pseudo_obs(residual_eth)
v = pseudo_obs(residual_sol)

# 2. เลือก family — ดูช่องว่าง AIC ไม่ใช่แค่ผู้ชนะ
for row in select_family(u, v):
    print(row["family"], round(row["aic"], 2))

# 3. fit
cop = fit_cml(u, v, Clayton)            # MLE
cop = fit_tau_inversion(u, v, Clayton)  # เร็วกว่า เหมาะกับ rolling refit

# 4. สัญญาณ
mi = mispricing_index(cop, u, v)        # h(u|v) − 0.5  ∈ [−0.5, 0.5]
signal = np.cumsum(mi)                  # cumulative MI

# 5. ความเสี่ยง
print("λ_L ทฤษฎี   =", cop.lambda_lower())
print("λ̂_L ข้อมูล  =", empirical_tail_dep(u, v, 0.05, "lower"))
```

---

## B.5 โครงร่าง backtest ที่ไม่มี look-ahead

โครงนี้เป็นจุดเริ่มต้น ไม่ใช่ระบบที่พร้อมใช้ — อ่านบทที่ 12 ก่อนเชื่อผลใด ๆ

```python
def backtest(x, y, window=250, refit_every=20, entry=3.0, exit_at=0.5,
             family=Clayton, cost_bps=10.0, delay=1):
    """
    x, y      : residual รายวันของสองสินทรัพย์ (หัก common factor แล้ว)
    window    : ความยาวหน้าต่างสำหรับ PIT และ fit copula
    refit_every : refit copula ทุกกี่วัน
    entry/exit  : threshold บน cumulative MI
    delay     : เข้าออกช้ากี่บาร์ — ตั้ง 1 เป็นอย่างน้อยเสมอ (บทที่ 8 หัวข้อ 8.5)
    """
    n = len(x)
    pos = np.zeros(n)          # สถานะที่ถืออยู่จริงในแต่ละวัน (+1 = long x / short y)
    current = 0.0              # การตัดสินใจล่าสุด — เก็บเป็นสเกลาร์ ไม่ใช่อ่านจาก pos
    cum_mi = 0.0
    cop = None

    for t in range(window, n - delay):
        # --- ทุกอย่างในบล็อกนี้ใช้ข้อมูลถึง t−1 เท่านั้น ---
        hist = slice(t - window, t)
        u_h, v_h = pseudo_obs(x[hist]), pseudo_obs(y[hist])

        if cop is None or (t - window) % refit_every == 0:
            cop = fit_tau_inversion(u_h, v_h, family)

        # PIT ของวันนี้ เทียบกับ "อดีต" เท่านั้น
        u_t = (np.sum(x[hist] <= x[t]) + 1.0) / (window + 2.0)
        v_t = (np.sum(y[hist] <= y[t]) + 1.0) / (window + 2.0)

        cum_mi += float(cop.h(np.array(u_t), np.array(v_t))) - 0.5

        # --- ตัดสินใจ แล้วผลจะเกิดที่ t+delay ---
        if abs(cum_mi) < exit_at:
            if current != 0.0:
                cum_mi = 0.0           # ปิดสถานะแล้วจึงเริ่มสะสมใหม่
            current = 0.0
        elif cum_mi < -entry:
            current = +1.0
        elif cum_mi > entry:
            current = -1.0
        # กรณีอื่น = ถือสถานะเดิมต่อ (current ไม่เปลี่ยน)

        pos[t + delay] = current       # การตัดสินใจ ณ t มีผลที่ t+delay

    # P&L: สถานะของเมื่อวาน คูณผลตอบแทนวันนี้ หักต้นทุนตอนเปลี่ยนสถานะ
    spread_ret = x - y
    gross = pos[:-1] * spread_ret[1:]
    turnover = np.abs(np.diff(pos))
    net = gross - turnover * cost_bps / 1e4
    return {"pos": pos, "gross": gross, "net": net,
            "turnover": float(turnover.sum())}
```

**สิ่งที่โครงนี้ทำถูกและต้องรักษาไว้**

```
□ PIT ใช้เฉพาะข้อมูลอดีต ไม่ใช่ rank จากทั้งชุด
□ copula fit จากหน้าต่างอดีต และ refit เป็นระยะ
□ มี execution delay อย่างน้อย 1 บาร์
□ หักต้นทุนตาม turnover จริง
□ P&L ใช้สถานะเมื่อวานคูณผลตอบแทนวันนี้ ไม่ใช่วันเดียวกัน
□ แต่ละช่องของ pos ถูกเขียนครั้งเดียว จากการตัดสินใจครั้งเดียว
```

**หมายเหตุสองข้อที่คนอ่านโค้ดนี้ควรรู้**

*ทำไมต้องเก็บ `current` เป็นสเกลาร์* — เวอร์ชันแรกของโค้ดนี้อ่านสถานะเดิมจาก
`pos[t−1]` แล้วเขียนกลับด้วย `pos[t+delay:] = new_pos` (เขียนทับหางทั้งก้อน
ทุกรอบ) ซึ่งให้ผลถูกโดยบังเอิญ แต่อ่านยาก และเป็น O(n²) การแยก "การตัดสินใจ
ล่าสุด" ออกมาเป็นตัวแปรของตัวเอง ทำให้แต่ละช่องของ `pos` ถูกเขียนครั้งเดียว
และตรวจสอบได้ว่ามาจากข้อมูลถึงวันไหน

*delay ที่แท้จริงคือ `delay + 1` บาร์* — เพราะสถานะที่ตั้ง ณ `t+delay`
ไปได้ผลตอบแทนของช่วง `t+delay → t+delay+1` ถ้าจะเทียบกับงานวิจัยที่
รายงาน "เข้าวันถัดไป" ให้ตั้ง `delay=0` แล้วอ่านค่านั้นเป็น 1 บาร์

**ลองรันดูก่อนเชื่อ — แล้วคุณจะเจอเรื่องนี้**

ด้วยพารามิเตอร์ตั้งต้นข้างบน (`entry=3.0`) บนข้อมูลจำลอง 900 วัน
โครงนี้เข้าเทรด **ครั้งเดียว** ตลอดทั้งช่วง

นี่ไม่ใช่บั๊ก แต่เป็นหน้าตาจริงของกฎแบบ cumulative MI: `cum_mi` เป็นผลรวมสะสม
ที่ไม่เคยถูกรีเซ็ตระหว่างที่ยังไม่มีสถานะ กว่าจะไต่ถึง ±3 จึงใช้เวลานานมาก
และนี่คือเหตุผลที่บทที่ 7 หัวข้อ 7.3 เตือนว่า **จุดรีเซ็ต `t₀` เป็นพารามิเตอร์
ซ่อนที่มีอิทธิพลสูงมาก**

> **ก่อนดู Sharpe ให้ดูจำนวนเทรดเสมอ** ถ้าทั้ง backtest มี 3 เทรด
> ตัวเลขสถิติใด ๆ ที่คำนวณจากมันไม่มีความหมาย — และนี่เป็นความผิดพลาด
> ที่มองไม่เห็นถ้าคุณดูแค่กราฟ equity curve

**สิ่งที่ยังขาดและต้องเพิ่มก่อนใช้จริง**

```
□ วิธีเลือก family แบบ walk-forward (ตอนนี้ตรึงไว้ตัวเดียว)
□ การจัดการหลายคู่พร้อมกันและการจำกัดความเสี่ยงรวม
□ slippage ตามขนาดคำสั่ง ไม่ใช่ค่าคงที่
□ funding cost ของ perp
□ กฎ stop loss และ time stop
□ การจัดการวันที่ข้อมูลขาด
```

---

## B.6 เครื่องมือวินิจฉัยที่ควรรันทุกครั้ง

```python
from copula_toolkit import bucket_forward_return, effective_breadth, half_life

# 1. สัญญาณแรงขึ้นแล้วผลตอบแทนดีขึ้นตามไหม (บทที่ 8, 12)
for b in bucket_forward_return(signal[:-5], fwd_return_5d):
    print(b["bucket"], b["n"], round(b["mean_fwd_return"], 5))
# ต้องเห็น monotonicity — ถ้าไม่มี ให้หยุดแล้วกลับไปคิดใหม่

# 2. มี reversion ให้เทรดจริงไหม (บทที่ 8)
print("half-life =", half_life(spread))      # inf = ไม่มีอะไรให้เทรด

# 3. พอร์ตมีกี่เดิมพันจริง ๆ (บทที่ 10)
print("N_eff ปกติ   =", effective_breadth(np.corrcoef(pnl_legs, rowvar=False)))
print("N_eff ที่ tail =", effective_breadth(np.corrcoef(pnl_legs[worst_days], rowvar=False)))
```

---

## B.7 ตัวอย่างบนข้อมูลของรีโปนี้

`example_repo_data.py` เดินทั้งขั้นตอนบนข้อมูล option chain ที่มีอยู่จริง:

```
[1] หัก common factor        →  ETH beta ต่อ BTC และสัดส่วนความแปรปรวนที่เหลือ
[2] copula ของผลตอบแทน       →  BTC ↔ ETH
[3] copula ของ ΔATM IV       →  IV ของสองเหรียญพุ่งพร้อมกันไหม
[4] ทดสอบ mean reversion     →  half-life พร้อมคำเตือนเรื่อง small-sample bias
[5] effective breadth        →  พอร์ตสมมติ 3 ขา ที่จริงแล้วเป็นกี่เดิมพัน
```

ผลที่ได้จากข้อมูลปัจจุบัน (~55 วัน) มีสองอย่างที่สอนได้ดี:

- **ΔAIC ระหว่างอันดับ 1 กับ 2 ของคู่ IV อยู่ที่ราว 2** — ซึ่งแปลว่า
  แยกไม่ออก สคริปต์จะพิมพ์เตือนเองตามหลักในบทที่ 5
- **N_eff ของพอร์ต 3 ขาออกมาราว 1.5** — เพราะสองขาเป็นเรื่องเดียวกัน
  ซึ่งเป็นภาพจำลองย่อส่วนของปัญหาในบทที่ 10

และสคริปต์จะเตือนตลอดว่าข้อมูลสั้นเกินกว่าจะสรุปอะไร ซึ่งเป็น
พฤติกรรมที่โค้ดวิจัยทุกตัวควรมี

---

[← ภาคผนวก A](appendix-a-formulas.md) | [สารบัญ](README.md) | [ภาคผนวก C: อ่านต่อ →](appendix-c-reading.md)
