#!/usr/bin/env bash
# เก็บสแนปช็อตรายวันบน "เครื่องของคุณเอง" แล้ว push ขึ้น GitHub
#
# ตั้งเวลาด้วย cron ของเครื่อง (07:15 น. เวลาไทยทุกวัน):
#   crontab -e
#   15 7 * * *  /path/to/options-data/scripts/run_local.sh >> /path/to/options-data/snapshot.log 2>&1
#
# ทำไมไม่ใช้ GitHub Actions: ข้อกำหนดของ Actions ครอบคลุมเฉพาะงานสร้าง ทดสอบ
# และเผยแพร่ซอฟต์แวร์ของ repo นั้น การตั้ง cron ดูดข้อมูลตลาดมาสะสมอยู่นอกขอบเขต
set -euo pipefail
cd "$(dirname "$0")/.."

export SKIP_IF_EXISTS=1          # ไม่เขียนทับไฟล์ของวันที่มีอยู่แล้ว
git pull --rebase --quiet origin main

rc=0
python3 scripts/fetch_chain.py || rc=$?

if git diff --quiet -- data; then
  echo "$(date -u +%Y-%m-%dT%H:%MZ) ไม่มีข้อมูลใหม่ (rc=$rc)"
else
  git add data
  git commit -q -m "Snapshot $(date -u +%Y-%m-%d)"
  git push -q origin main
  echo "$(date -u +%Y-%m-%dT%H:%MZ) push สแนปช็อตแล้ว (rc=$rc)"
fi

# rc: 0 = ครบ · 1 = ล้มเหลวทั้งหมด · 2 = ได้บางส่วน
exit "$rc"
