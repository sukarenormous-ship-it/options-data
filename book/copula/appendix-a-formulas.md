# ภาคผนวก A — สัญลักษณ์และสูตรรวม

> หน้าเดียวจบ สำหรับเปิดดูตอนเขียนโค้ด

---

## A.1 สัญลักษณ์

| สัญลักษณ์ | ความหมาย |
|---|---|
| `X, Y` | ตัวแปรสุ่ม (return, residual) |
| `F₁, F₂` | marginal CDF |
| `u = F₁(x)`, `v = F₂(y)` | pseudo-observation / percentile |
| `C(u,v)` | copula (CDF บน unit square) |
| `c(u,v)` | copula density = ∂²C/∂u∂v |
| `h(u\|v)` | conditional CDF = ∂C(u,v)/∂v = P(U ≤ u \| V = v) |
| `θ` | พารามิเตอร์ dependence |
| `τ` | Kendall's tau |
| `ρ_S` | Spearman's rho |
| `ρ` | Pearson correlation หรือพารามิเตอร์ของ elliptical copula |
| `λ_L, λ_U` | tail dependence ล่าง / บน |
| `ν` | degrees of freedom (t copula) |
| `Φ, Φ⁻¹` | standard normal CDF และ inverse |
| `t_ν, t_ν⁻¹` | Student-t CDF และ inverse |

---

## A.2 ผลลัพธ์หลัก

**Sklar's Theorem**
```
F(x,y) = C( F₁(x), F₂(y) )
f(x,y) = c(u,v) · f₁(x) · f₂(y)
```

**PIT**
```
U = F₁(X) ~ Uniform(0,1)     เมื่อ F₁ ต่อเนื่อง
```

**Pseudo-observations**
```
ûᵢ = rank(xᵢ) / (n+1)
```

**Fréchet–Hoeffding bounds**
```
max(u+v−1, 0)  ≤  C(u,v)  ≤  min(u,v)
```

**Independence copula**
```
Π(u,v) = u·v        →  h(u|v) = u
```

**Tail dependence**
```
λ_U = lim_{q→1⁻} P(V > q | U > q) = lim_{q→1⁻} (1 − 2q + C(q,q)) / (1 − q)
λ_L = lim_{q→0⁺} P(V ≤ q | U ≤ q) = lim_{q→0⁺} C(q,q) / q
```

---

## A.3 ตารางสรุปแต่ละตระกูล

### Gaussian
```
C(u,v)   = Φ_ρ( Φ⁻¹(u), Φ⁻¹(v) )
h(u|v)   = Φ( (Φ⁻¹(u) − ρ·Φ⁻¹(v)) / √(1−ρ²) )
τ        = (2/π)·arcsin(ρ)          →  ρ = sin(πτ/2)
ρ_S      = (6/π)·arcsin(ρ/2)
λ_L=λ_U  = 0
โดเมน     ρ ∈ (−1,1)
```

### Student-t
```
C(u,v)   = t_{ρ,ν}( t_ν⁻¹(u), t_ν⁻¹(v) )
h(u|v)   = t_{ν+1}( (x − ρy) / √( ((ν + y²)(1 − ρ²)) / (ν+1) ) )
           โดย x = t_ν⁻¹(u), y = t_ν⁻¹(v)
τ        = (2/π)·arcsin(ρ)
λ_L=λ_U  = 2·t_{ν+1}( −√(ν+1)·√((1−ρ)/(1+ρ)) )
โดเมน     ρ ∈ (−1,1), ν > 0
          (ν > 2 เป็นเงื่อนไขให้ *การแจกแจง* t มีความแปรปรวนจำกัด
           ไม่ใช่เงื่อนไขของ copula — ค่า ν < 2 ที่ fit ได้ถูกต้องตามนิยาม)
```

### Clayton
```
C(u,v)   = ( u^(−θ) + v^(−θ) − 1 )^(−1/θ)
c(u,v)   = (1+θ)·(u·v)^(−θ−1)·( u^(−θ)+v^(−θ)−1 )^(−1/θ−2)
h(u|v)   = v^(−θ−1)·( u^(−θ)+v^(−θ)−1 )^(−1/θ−1)
τ        = θ/(θ+2)                  →  θ = 2τ/(1−τ)
λ_L      = 2^(−1/θ),   λ_U = 0
โดเมน     θ > 0   (นิยามเต็มคือ θ ≥ −1 โดยช่วง [−1,0) ให้ dependence เชิงลบ
                   และ τ = θ/(θ+2) ใช้ได้ตลอด — เล่มนี้จำกัดที่ θ > 0
                   เพื่อความเรียบง่าย ถ้าต้องการ dependence เชิงลบให้ใช้
                   Frank หรือ rotation 90°/270°)
```

### Gumbel
```
A        = ( (−ln u)^θ + (−ln v)^θ )^(1/θ)
C(u,v)   = exp(−A)
h(u|v)   = C(u,v)·(1/v)·(−ln v)^(θ−1)·A^(1−θ)
τ        = 1 − 1/θ                  →  θ = 1/(1−τ)
λ_U      = 2 − 2^(1/θ),   λ_L = 0
โดเมน     θ ≥ 1
```

### Frank
```
g(x)     = e^(−θx) − 1,   D = e^(−θ) − 1
C(u,v)   = −(1/θ)·ln( 1 + g(u)·g(v)/D )
h(u|v)   = e^(−θv)·g(u) / ( D + g(u)·g(v) )
τ        = 1 − 4/θ + 4·D₁(θ)/θ      (D₁ = Debye function อันดับ 1)
λ_L=λ_U  = 0
โดเมน     θ ∈ ℝ \ {0}   (รองรับค่าลบ)
```

### Joe
```
C(u,v)   = 1 − [ ū^θ + v̄^θ − ū^θ·v̄^θ ]^(1/θ)     โดย ū = 1−u, v̄ = 1−v
λ_U      = 2 − 2^(1/θ),   λ_L = 0
โดเมน     θ ≥ 1
```

---

## A.4 การหมุน (rotation)

```
C₀(u,v)    = C(u,v)                          เดิม
C₉₀(u,v)   = v − C(1−u, v)                   dependence เชิงลบ
C₁₈₀(u,v)  = u + v − 1 + C(1−u, 1−v)         survival — สลับ tail บน/ล่าง
C₂₇₀(u,v)  = u − C(u, 1−v)                   dependence เชิงลบ
```

`C₁₈₀` ของ Clayton ให้ `λ_U` เท่ากับ `λ_L` ของ Clayton เดิม

---

## A.5 Vine (3 มิติ, C-vine ราก = ตัวที่ 1)

```
c(u₁,u₂,u₃) = c₁₂(u₁,u₂) · c₁₃(u₁,u₃) · c₂₃|₁( h(u₂|u₁), h(u₃|u₁) )
```

จำนวน pair copula สำหรับ d มิติ = `d(d−1)/2`
จำนวนโครงสร้าง R-vine ที่เป็นไปได้ = `(d!/2) · 2^((d−2)(d−3)/2)`
(d=3 → 3, d=5 → 480, d=8 → 660,602,880)

---

## A.6 สูตรฝั่งพอร์ตโฟลิโอ

**Effective breadth**
```
N_eff = N / ( 1 + (N−1)·ρ̄ )
```

**Fundamental law**
```
IR ≈ IC · √breadth
```

**OU process และ half-life**
```
de_t = κ(μ − e_t)dt + σ·dW_t
half-life = ln(2) / κ
```
ประมาณ κ จาก AR(1): `e_t = a + b·e_{t−1} + ε` แล้ว `κ ≈ −ln(b)` (ต่อหน่วยเวลา)

**Mispricing index**
```
MI_{A|B} = h(u_A | v_B) − 0.5          ∈ [−0.5, +0.5]
M_t      = Σ MI_s                       (cumulative)
```

**Standard error ของ Sharpe รายปี**
```
SE(SR) ≈ √( (1 + SR²/2) / T )   โดย SR และ T อยู่ในหน่วยความถี่เดียวกัน
       ≈ 1 / √(จำนวนปี)          เมื่อ SR ต่อคาบมีค่าน้อย ซึ่งเป็นกรณีปกติ
```

**Joint exceedance ที่ระดับ q**
```
P(U ≤ q, V ≤ q) = C(q,q)
เทียบกับกรณีอิสระ q²  →  อัตราส่วน C(q,q)/q²
```

---

## A.7 การแปลงระหว่าง τ กับพารามิเตอร์ (สำหรับ τ-inversion)

| Family | θ จาก τ | ช่วง τ ที่รองรับ |
|---|---|---|
| Gaussian | ρ = sin(πτ/2) | (−1, 1) |
| Clayton | θ = 2τ/(1−τ) | (0, 1) |
| Gumbel | θ = 1/(1−τ) | [0, 1) |
| Frank | แก้เชิงตัวเลขจาก D₁ | (−1, 1) ในทฤษฎี — แต่ถ้าจำกัด \|θ\| ≤ 35 ตามโค้ด จะได้ \|τ\| ≤ 0.891 |
| Joe | แก้เชิงตัวเลข (ไม่มีรูปปิด) | [0, 1) |

---

[← บทที่ 13](13-pitfalls.md) | [สารบัญ](README.md) | [ภาคผนวก B: โค้ด →](appendix-b-code.md)
