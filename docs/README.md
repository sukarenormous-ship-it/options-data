# docs/ — เอกสารในคลังนี้

คลังนี้เป็น **คลังข้อมูล** เป็นหลัก (ดู `README.md` ที่ราก) โฟลเดอร์นี้เก็บเฉพาะ
**เอกสารวางแผน** ส่วนตัวหนังสือย้ายออกไปแล้ว

## หนังสือ "คิดแบบ Quant" ย้ายไปที่ไหน

หนังสือ **"คิดแบบ Quant" (Quant for Non-Quant)** พร้อมภาคผนวก เครื่องมือโต้ตอบ
และบทเสริมสาย stat arb ทั้งห้าบท ย้ายไปอยู่รวมกับหนังสือเล่มอื่นที่
**`sukarenormous-ship-it/Claude-code-project`** branch `claude/payoff-chart-lesson-KchZQ`
แล้ว (ผ่าน PR #31) — ทั้งไฟล์ `docs/nq-*.html`, `docs/statarb-*.html`,
`docs/*-figures.json` และสคริปต์ `tools/nq_*.py`, `tools/copula_figures.py`,
`tools/blending_figures.py`, `tools/live_backtest_figures.py`,
`tools/alpha_decay_figures.py`, `tools/data_health.py`

**ข้อมูลตลาดยังอยู่ที่นี่** — สคริปต์สร้างตัวเลขทุกตัวในคลังโน้นอ่านข้อมูลจาก
`data/` ของคลังนี้ ถ้า clone ทั้งสองคลังเป็น sibling directory
(`options-data/` กับ `Claude-code-project/` อยู่ข้างกัน) สคริปต์จะหาเจอเอง
หรือระบุตรง ๆ ก็ได้:

```bash
python3 tools/nq_figures.py --data-dir /path/to/options-data/data
# หรือ
NQ_DATA_DIR=/path/to/options-data/data python3 tools/data_health.py
```

## ไฟล์ที่ยังอยู่ในโฟลเดอร์นี้

| ไฟล์ | คืออะไร |
|---|---|
| `quant-for-non-quant-book-plan.md` | แผนโครงหนังสือเดิม — โครง 10 บท ภาคผนวก เครื่องมือ กฎเหล็ก 5 ข้อ |
| `next-phase-plan.md` | แผนเฟสถัดไป — งาน A (ย้ายคลัง) และงาน B–E (บทเสริม stat arb) พร้อมสถานะ |

เก็บสองไฟล์นี้ไว้ที่นี่เพราะเป็นบันทึกกระบวนการทำงานที่เกิดขึ้นในคลังนี้ ไม่ใช่ตัวเนื้อหาหนังสือ
