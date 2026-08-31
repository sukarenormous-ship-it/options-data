# ภาคผนวก C — อ่านต่อ

> รายการสั้น อ่านจบได้จริง เรียงตามลำดับที่ควรอ่าน

---

## C.1 ถ้าจะอ่านแค่สามชิ้น

**1. Embrechts, McNeil & Straumann (2002)**
*"Correlation and dependence in risk management: properties and pitfalls"*
ใน *Risk Management: Value at Risk and Beyond*, Cambridge University Press

บทความที่อธิบายว่าทำไม correlation ไม่พอ ได้ชัดเจนที่สุด และเป็นรากของ
บทที่ 1 ทั้งบท อ่านง่ายกว่าที่ชื่อฟังดู

**2. Genest & Favre (2007)**
*"Everything you always wanted to know about copula modeling but were afraid to ask"*
*Journal of Hydraulic Engineering*, 12(4), 347–368

คู่มือปฏิบัติที่ดีที่สุดสำหรับการ fit และตรวจสอบ copula ครอบคลุม
pseudo-observations, การเลือก family, GOF test และกราฟวินิจฉัย
มาจากสาย hydrology แต่ใช้ได้ตรง ๆ กับการเงิน

**3. Nelsen (2006)**
*An Introduction to Copulas*, ฉบับที่ 2, Springer

ตำราอ้างอิงมาตรฐาน ไม่ต้องอ่านทั้งเล่ม — บทที่ 1–2 (พื้นฐานและ Sklar)
และบทที่ 5 (dependence และ tail dependence) พอสำหรับงานที่หนังสือเล่มนี้พูดถึง

---

## C.2 ตามหัวข้อ

### พื้นฐานและทฤษฎี

- **Sklar (1959)** *"Fonctions de répartition à n dimensions et leurs marges"*
  งานต้นฉบับ ภาษาฝรั่งเศส ยาว 2 หน้า — น่าอ่านเชิงประวัติศาสตร์
- **Joe (2014)** *Dependence Modeling with Copulas*, Chapman & Hall
  ครอบคลุมกว่า Nelsen โดยเฉพาะเรื่อง vine และมิติสูง
- **Darsow, Nguyen & Olsen (1992)** *"Copulas and Markov processes"*
  *Illinois Journal of Mathematics*, 36(4), 600–642
  งานที่แสดงว่ากระบวนการ Markov อธิบายได้ด้วย copula ของคู่ที่ต่างเวลากัน —
  เป็นฐานของ "ขอบเขตของข้ออ้าง" ในบทที่ 8 หัวข้อ 8.2 อ่านเมื่อคุณอยากรู้ว่า
  ทำไม copula *ในรูปแบบอื่น* ถึงพูดเรื่องเวลาได้ ทั้งที่ตัวที่เราใช้ในเล่มนี้พูดไม่ได้

### การประยุกต์ทางการเงิน

- **Patton (2013)** *"Copula methods for forecasting multivariate time series"*
  ใน *Handbook of Economic Forecasting* Vol. 2 — สรุปงาน copula
  ในบริบทอนุกรมเวลาที่ครบที่สุด รวมถึง time-varying copula (บทที่ 6)
- **Cherubini, Luciano & Vecchiato (2004)** *Copula Methods in Finance*, Wiley
  เน้นการประยุกต์ ตัวอย่างเยอะ

### Vine copula

- **Aas, Czado, Frigessi & Bakken (2009)**
  *"Pair-copula constructions of multiple dependence"*
  *Insurance: Mathematics and Economics*, 44(2), 182–198
  งานที่ทำให้ vine ใช้ได้จริง — เป็นรากของบทที่ 9
- **Czado (2019)** *Analyzing Dependent Data with Vine Copulas*, Springer

### Copula ในการเทรด (อ่านอย่างระแวง)

- **Liew & Wu (2013)** *"Pairs trading: A copula approach"*
  *Journal of Derivatives & Hedge Funds*, 19(1), 12–30
- **Xie, Liew, Wu & Zou (2016)** *"Pairs Trading with Copulas"*
  *The Journal of Trading*, 11(3), 41–52
  ต้นทางของ mispricing index ในบทที่ 7
- **Krauss (2017)** *"Statistical arbitrage pairs trading strategies:
  review and outlook"* *Journal of Economic Surveys*, 31(2), 513–545
  สำรวจภาพรวมทั้งสาขา — ควรอ่านเพื่อเห็นว่าตระกูลวิธีมีอะไรบ้าง

> **ข้อควรระวังกับหมวดนี้:** งานสาย copula trading เกือบทั้งหมด
> รายงานผลที่ดี ซึ่งเป็นสิ่งที่คาดได้จาก publication bias
> ตอนอ่านให้ตรวจสามข้อทุกครั้ง: (1) มี transaction cost ที่สมจริงไหม
> (2) เทียบกับ baseline ที่จูนมาดีเท่ากันไหม (3) ทดสอบ execution delay
> ไหม — บทที่ 12 คือรายการตรวจสอบเต็ม

### StatArb และโครงสร้างพอร์ต

- **Avellaneda & Lee (2010)** *"Statistical arbitrage in the US equities market"*
  *Quantitative Finance*, 10(7), 761–782
  ต้นแบบของสถาปัตยกรรม PCA → residual → OU ในบทที่ 11 อ่านให้จบ
- **Gatev, Goetzmann & Rouwenhorst (2006)**
  *"Pairs trading: Performance of a relative-value arbitrage rule"*
  *Review of Financial Studies*, 19(3), 797–827
  งาน distance approach คลาสสิก และเป็น baseline ที่ทุกวิธีใหม่ควรเทียบด้วย
- **Grinold & Kahn (1999)** *Active Portfolio Management*, ฉบับที่ 2
  ที่มาของ fundamental law และแนวคิด breadth ในบทที่ 10

### ระเบียบวิธีและการหลอกตัวเอง

- **Bailey & López de Prado (2014)** *"The deflated Sharpe ratio"*
  *Journal of Portfolio Management*, 40(5), 94–107
  วิธีปรับ Sharpe ตามจำนวนการทดลองที่ทำไป — ตรงกับบทที่ 12 หัวข้อ 12.6 ข้อ 3
- **López de Prado (2018)** *Advances in Financial Machine Learning*, Wiley
  บทที่ 7 (purged cross-validation) และบทที่ 11 (backtest overfitting)
  คุ้มค่าที่สุดสำหรับคนทำ StatArb
- **Harvey, Liu & Zhu (2016)** *"…and the Cross-Section of Expected Returns"*
  *Review of Financial Studies*, 29(1), 5–68
  ว่าด้วยปัญหา multiple testing ในงานวิจัยการเงินทั้งสาขา

---

## C.3 ซอฟต์แวร์

| แพ็กเกจ | ภาษา | หมายเหตุ |
|---|---|---|
| `copulas` | Python | ใช้ง่าย เหมาะเริ่มต้น |
| `statsmodels.distributions.copula` | Python | อยู่ใน statsmodels อยู่แล้ว |
| `pyvinecopulib` | Python | binding ของ `vinecopulib` — ตัวเลือกที่ดีที่สุดสำหรับ vine |
| `VineCopula` | R | ครบที่สุดในบรรดาทั้งหมด งานวิชาการส่วนใหญ่ใช้ตัวนี้ |
| `copula` (Hofert et al.) | R | ตัวอ้างอิงมาตรฐานสำหรับ copula ทั่วไป |

**คำแนะนำ:** เขียน h-function และการ fit เองอย่างน้อยหนึ่งครั้ง
ก่อนใช้ไลบรารี ([`code/`](code/) ของหนังสือเล่มนี้ทำแบบนั้น) เพราะ
ตอน debug ระบบเทรด คุณจะต้องรู้ว่าตัวเลขทุกตัวมาจากไหน และไลบรารี
ส่วนใหญ่ซ่อนรายละเอียดที่สำคัญที่สุดไว้ — เช่นวิธีจัดการ marginal
และการกำหนดขอบเขตของ pseudo-observations

---

## C.4 ข้อมูลสำหรับฝึก

**รีโปนี้** — `data/` มี option chain snapshot รายวันของ Deribit และ OKX
พร้อม IV และ Greeks ใช้ทำแบบฝึกหัดเรื่อง dependence ของ implied vol,
term structure และ cross-exchange ได้ (ดู [README หลัก](../../README.md))

**ข้อมูลราคา spot/perp** ความถี่สูงกว่านี้ต้องดึงจาก public API ของ
exchange เอง — ซึ่งจำเป็นถ้าจะทดสอบเรื่องที่บทที่ 8 หัวข้อ 8.5 พูดถึง
(microstructure noise เทียบกับ mispricing จริง) เพราะข้อมูลรายวัน
แยกสองอย่างนี้ไม่ออก

---

[← ภาคผนวก B](appendix-b-code.md) | [สารบัญ](README.md)
