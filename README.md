# options-data

คลังข้อมูล option chain ของคริปโต เก็บสแนปช็อตวันละครั้งจาก public API
(ไม่มีค่าใช้จ่าย ไม่ต้องมี API key) โดย**รันบนเครื่องของเจ้าของ repo** ผ่าน cron
แล้ว push ขึ้นมา ดูวิธีตั้งที่หัวข้อ "เก็บข้อมูลรายวัน" ด้านล่าง

| แหล่งข้อมูล | เหรียญ | ข้อมูลที่ได้ |
|---|---|---|
| **Deribit** | BTC, ETH, SOL, XRP | mark price, bid/ask, IV, open interest, volume |
| **OKX** | BTC, ETH, SOL | mark price, bid/ask, IV, **Greeks (delta/gamma/vega/theta)**, OI, volume |

> ทำไมไม่ใช่ Bybit/Binance: ทั้งสองเจ้าบล็อก IP ของศูนย์ข้อมูล (ได้ HTTP 403/451)
> ส่วน Deribit คือตลาด options ที่ใหญ่ที่สุดอยู่แล้ว จึงเป็นแหล่งที่เหมาะกว่า

## โครงไฟล์

```
data/
├── deribit/2026/07/2026-07-05.csv
└── okx/2026/07/2026-07-05.csv
```

ไฟล์ละ 1 วัน 1 exchange — หนึ่งแถวคือหนึ่งสัญญา option

## คอลัมน์ใน CSV

| คอลัมน์ | ความหมาย |
|---|---|
| `snapshot_utc` | เวลาที่เก็บข้อมูล (UTC) |
| `exchange` | `deribit` หรือ `okx` |
| `underlying` | เหรียญอ้างอิง เช่น `BTC` |
| `instrument` | ชื่อสัญญาตามรูปแบบของ exchange |
| `expiry` | วันหมดอายุ (`YYYY-MM-DD`) |
| `strike` | ราคาใช้สิทธิ์ (USD) |
| `type` | `call` หรือ `put` |
| `mark_price` | ราคา mark **หน่วยเป็นเหรียญอ้างอิง** (คูณ `underlying_price` เพื่อแปลงเป็น USD) |
| `bid` / `ask` | ราคาเสนอซื้อ/ขายที่ดีที่สุด (หน่วยเดียวกับ mark) |
| `mark_iv` | implied volatility — **หน่วยต่างกัน**: Deribit เป็นเปอร์เซ็นต์ (เช่น `49.57`), OKX เป็นทศนิยม (เช่น `0.4172` = 41.72%) |
| `delta` `gamma` `vega` `theta` | Greeks (มีเฉพาะฝั่ง OKX) |
| `open_interest` | สัญญาคงค้าง |
| `volume_24h` | ปริมาณซื้อขาย 24 ชม. |
| `underlying_price` | ราคา spot/index ของเหรียญอ้างอิง (USD) |

ช่องว่าง = exchange ไม่ให้ข้อมูลนั้น

## วิธีใช้กับ pandas

```python
import pandas as pd
from glob import glob

# โหลดทั้งเดือน
files = glob("data/deribit/2026/07/*.csv")
df = pd.concat(pd.read_csv(f) for f in files)

# กราฟ IV smile ของ BTC expiry ใกล้สุด ณ วันล่าสุด
last = df[df.snapshot_utc == df.snapshot_utc.max()]
btc = last[(last.underlying == "BTC") & (last.type == "call")]
nearest = btc[btc.expiry == btc.expiry.min()]
nearest.sort_values("strike").plot(x="strike", y="mark_iv")
```

## เก็บข้อมูลรายวัน

รันบนเครื่องของคุณเอง ไม่ใช่บน GitHub Actions เพราะข้อกำหนดของ Actions ครอบคลุม
เฉพาะงานสร้าง ทดสอบ และเผยแพร่ซอฟต์แวร์ของ repo นั้น การตั้ง cron ดูดข้อมูลตลาด
มาสะสมอยู่นอกขอบเขต และเคยทำให้บัญชีถูกระงับมาแล้ว

```bash
crontab -e
# 07:15 น. เวลาไทยทุกวัน
15 7 * * *  /path/to/options-data/scripts/run_local.sh >> /path/to/options-data/snapshot.log 2>&1
```

สคริปต์จะ pull ก่อน ดึงข้อมูล commit และ push ให้เอง · ถ้าไฟล์ของวันนั้นมีอยู่แล้ว
จะข้าม (`SKIP_IF_EXISTS=1`) · ดู log ที่ `snapshot.log` เมื่ออยากรู้ว่ารอบไหนพลาด

รันครั้งเดียวแบบไม่ push: `python3 scripts/fetch_chain.py` (ใช้ Python มาตรฐาน ไม่ต้องติดตั้งอะไร)

## หมายเหตุ

- ขนาดข้อมูล ~1 MB/วันก่อนบีบอัด — git เก็บได้หลายปีสบาย ๆ
- ถ้าแหล่งใดล่มในวันนั้น อีกแหล่งยังถูกบันทึกตามปกติ (ล้มแยกกัน)
- โปรเจกต์เครื่องมือ/บทเรียนอยู่ที่ [Claude-code-project](https://github.com/sukarenormous-ship-it/Claude-code-project)
