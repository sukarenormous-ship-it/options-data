#!/usr/bin/env python3
"""Snapshot crypto option chains from Deribit and OKX into daily CSV files.

Runs inside GitHub Actions (see .github/workflows/snapshot.yml) but can be
run anywhere: `python3 scripts/fetch_chain.py`. Standard library only.

Output: data/<exchange>/<YYYY>/<MM>/<YYYY-MM-DD>.csv, one row per option
contract. Prices from both exchanges are quoted in the base coin (e.g. a
mark_price of 0.0425 on a BTC option means 0.0425 BTC); multiply by
underlying_price to get USD.
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DERIBIT_CURRENCIES = ["BTC", "ETH", "SOL", "XRP"]
OKX_FAMILIES = ["BTC-USD", "ETH-USD", "SOL-USD"]

COLUMNS = [
    "snapshot_utc", "exchange", "underlying", "instrument", "expiry", "strike",
    "type", "mark_price", "bid", "ask", "mark_iv", "delta", "gamma", "vega",
    "theta", "open_interest", "volume_24h", "underlying_price",
]

MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def http_get_json(url: str, params: dict | None = None) -> object:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "options-snapshot/1.0"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            if attempt == 4:
                raise
            wait = 2 ** attempt
            print(f"  retry in {wait}s: {url.split('?')[0]} ({exc})", file=sys.stderr)
            time.sleep(wait)


def num(value) -> str:
    """Normalize a numeric API field to a CSV cell ('' when absent)."""
    if value is None or value == "":
        return ""
    return str(value)


# ---------------------------------------------------------------- Deribit

def parse_deribit_instrument(name: str):
    """BTC-25JUL26-60000-C -> (underlying, expiry ISO, strike, type)."""
    base, expiry, strike, opt_type = name.split("-")
    day, mon, year = int(expiry[:-5]), expiry[-5:-2], int(expiry[-2:])
    iso = f"20{year:02d}-{MONTHS[mon]:02d}-{day:02d}"
    # small-cap strikes use 'd' as the decimal point, e.g. XRP ... 2d1
    strike_val = strike.replace("d", ".")
    return base, iso, strike_val, "call" if opt_type == "C" else "put"


def fetch_deribit(snapshot_ts: str) -> list[dict]:
    rows = []
    for currency in DERIBIT_CURRENCIES:
        try:
            data = http_get_json(
                "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
                {"currency": currency, "kind": "option"})
            if "result" not in data:
                raise RuntimeError(data.get("error", "no result"))
        except Exception as exc:
            print(f"  deribit {currency}: skipped ({exc})", file=sys.stderr)
            continue
        for item in data["result"]:
            try:
                base, expiry, strike, opt_type = parse_deribit_instrument(item["instrument_name"])
            except Exception:
                continue
            rows.append({
                "snapshot_utc": snapshot_ts,
                "exchange": "deribit",
                "underlying": base,
                "instrument": item["instrument_name"],
                "expiry": expiry,
                "strike": strike,
                "type": opt_type,
                "mark_price": num(item.get("mark_price")),
                "bid": num(item.get("bid_price")),
                "ask": num(item.get("ask_price")),
                "mark_iv": num(item.get("mark_iv")),
                "delta": "", "gamma": "", "vega": "", "theta": "",
                "open_interest": num(item.get("open_interest")),
                "volume_24h": num(item.get("volume")),
                "underlying_price": num(item.get("underlying_price")),
            })
        print(f"  deribit {currency}: {sum(r['underlying'] == currency for r in rows)} contracts")
        time.sleep(0.3)
    return rows


# -------------------------------------------------------------------- OKX

def parse_okx_instrument(inst_id: str):
    """BTC-USD-260725-60000-C -> (underlying, expiry ISO, strike, type)."""
    parts = inst_id.split("-")
    base, date, strike, opt_type = parts[0], parts[2], parts[3], parts[4]
    iso = f"20{date[0:2]}-{date[2:4]}-{date[4:6]}"
    return base, iso, strike, "call" if opt_type == "C" else "put"


def okx_result(payload) -> list:
    if payload.get("code") != "0":
        raise RuntimeError(payload.get("msg", f"code {payload.get('code')}"))
    return payload["data"]


def fetch_okx(snapshot_ts: str) -> list[dict]:
    rows = []
    for family in OKX_FAMILIES:
        try:
            summary = okx_result(http_get_json(
                "https://www.okx.com/api/v5/public/opt-summary", {"instFamily": family}))
            marks = okx_result(http_get_json(
                "https://www.okx.com/api/v5/public/mark-price",
                {"instType": "OPTION", "instFamily": family}))
            tickers = okx_result(http_get_json(
                "https://www.okx.com/api/v5/market/tickers",
                {"instType": "OPTION", "instFamily": family}))
            oi = okx_result(http_get_json(
                "https://www.okx.com/api/v5/public/open-interest",
                {"instType": "OPTION", "instFamily": family}))
            index = okx_result(http_get_json(
                "https://www.okx.com/api/v5/market/index-tickers",
                {"instId": family.replace("USD", "USDT")}))
        except Exception as exc:
            print(f"  okx {family}: skipped ({exc})", file=sys.stderr)
            continue

        mark_by_id = {m["instId"]: m for m in marks}
        ticker_by_id = {t["instId"]: t for t in tickers}
        oi_by_id = {o["instId"]: o for o in oi}
        index_px = index[0].get("idxPx", "") if index else ""

        count = 0
        for item in summary:
            inst_id = item["instId"]
            try:
                base, expiry, strike, opt_type = parse_okx_instrument(inst_id)
            except Exception:
                continue
            ticker = ticker_by_id.get(inst_id, {})
            rows.append({
                "snapshot_utc": snapshot_ts,
                "exchange": "okx",
                "underlying": base,
                "instrument": inst_id,
                "expiry": expiry,
                "strike": strike,
                "type": opt_type,
                "mark_price": num(mark_by_id.get(inst_id, {}).get("markPx")),
                "bid": num(ticker.get("bidPx")),
                "ask": num(ticker.get("askPx")),
                "mark_iv": num(item.get("markVol")),
                "delta": num(item.get("delta")),
                "gamma": num(item.get("gamma")),
                "vega": num(item.get("vega")),
                "theta": num(item.get("theta")),
                "open_interest": num(oi_by_id.get(inst_id, {}).get("oi")),
                "volume_24h": num(ticker.get("vol24h")),
                "underlying_price": index_px,
            })
            count += 1
        print(f"  okx {family}: {count} contracts")
        time.sleep(0.3)
    return rows


# ------------------------------------------------------------------- main

def write_csv(rows: list[dict], exchange: str, now: datetime, repo_root: Path) -> Path:
    path = (repo_root / "data" / exchange / f"{now:%Y}" / f"{now:%m}"
            / f"{now:%Y-%m-%d}.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    now = datetime.now(timezone.utc)
    snapshot_ts = now.strftime("%Y-%m-%d %H:%M:%S")

    results = {}
    print("Fetching Deribit...")
    results["deribit"] = fetch_deribit(snapshot_ts)
    print("Fetching OKX...")
    results["okx"] = fetch_okx(snapshot_ts)

    wrote_any = False
    for exchange, rows in results.items():
        if not rows:
            print(f"{exchange}: no data, file not written", file=sys.stderr)
            continue
        path = write_csv(rows, exchange, now, repo_root)
        print(f"{exchange}: wrote {len(rows)} rows -> {path.relative_to(repo_root)}")
        wrote_any = True

    if not wrote_any:
        sys.exit("All sources failed — nothing written.")


if __name__ == "__main__":
    main()
