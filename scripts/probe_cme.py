#!/usr/bin/env python3
"""Throwaway reachability probe for CME open-interest sources.

Answers one question before any real work starts: which CME endpoints, if
any, respond to a GitHub Actions runner? Prints a status line per candidate
and never fails the job -- the log IS the result.

Delete this file once the answer is recorded.
"""

import gzip
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")

BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.cmegroup.com/",
    "Connection": "close",
}


def prev_business_day(days_back: int = 1) -> date:
    d = date.today()
    while days_back > 0:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days_back -= 1
    return d


def probe(name: str, url: str, headers: dict | None = None) -> tuple[int, bytes]:
    """Fetch a URL and print one summary line. Returns (status, body)."""
    req = urllib.request.Request(url, headers=headers or BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            ctype = resp.headers.get("Content-Type", "?").split(";")[0]
            print(f"[ OK  {resp.status}] {name}")
            print(f"        {url}")
            print(f"        {len(raw)} bytes, {ctype}")
            print(f"        {raw[:220]!r}")
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        body = exc.read()[:220]
        print(f"[FAIL {exc.code}] {name}")
        print(f"        {url}")
        print(f"        {body!r}")
        return exc.code, b""
    except Exception as exc:
        print(f"[ERR     ] {name}")
        print(f"        {url}")
        print(f"        {type(exc).__name__}: {exc}")
        return 0, b""
    finally:
        print()


def main() -> None:
    trade_date = prev_business_day()
    ymd = trade_date.strftime("%Y%m%d")
    slash = trade_date.strftime("%m/%d/%Y")
    print(f"Probing CME for trade date {trade_date} ({ymd})\n")

    print("=" * 70)
    print("ROUTE 1: CmeWS JSON (the API behind cmegroup.com's own OI pages)")
    print("=" * 70 + "\n")

    status, raw = probe(
        "product slate: crypto products (to discover numeric productIds)",
        "https://www.cmegroup.com/CmeWS/mvc/ProductSlate/V2/List"
        "?pageNumber=1&pageSize=200&sortField=globexCode&sortAsc=true"
        "&group=Cryptocurrency")

    product_ids: dict[str, str] = {}
    if status == 200 and raw:
        try:
            for p in json.loads(raw).get("products", []):
                label = f"{p.get('globexSymbol') or p.get('globex')} {p.get('name')}"
                product_ids[label] = str(p.get("id"))
            print("        discovered products:")
            for label, pid in list(product_ids.items())[:40]:
                print(f"          {pid:>8}  {label}")
            print()
        except Exception as exc:
            print(f"        (could not parse product slate: {exc})\n")

    # Fall back to hard-coded guesses so the rest of the probe still runs.
    candidates = list(product_ids.values())[:6] or ["8460", "8874"]

    for pid in candidates:
        probe(f"volume+OI detail by strike, productId={pid}",
              f"https://www.cmegroup.com/CmeWS/mvc/Volume/Details/O/{pid}/{ymd}/G")

    for pid in candidates[:2]:
        probe(f"settlements (options) productId={pid}",
              f"https://www.cmegroup.com/CmeWS/mvc/Settlements/Options/Settlements/{pid}/OOF"
              f"?tradeDate={slash}&strategy=DEFAULT")

    print("=" * 70)
    print("ROUTE 2: file exports / public ftp mirror (usually no bot wall)")
    print("=" * 70 + "\n")

    probe("volume+OI product list export (xls)",
          f"https://www.cmegroup.com/CmeWS/exp/voiProductsViewExport.ctl"
          f"?media=xls&tradeDate={slash}&reportType=F&sortField=vol&sortAsc=false")

    probe("volume+OI per-strike export, productId=8460",
          f"https://www.cmegroup.com/CmeWS/exp/voiProductDetailsViewExport.ctl"
          f"?media=xls&tradeDate={slash}&reportType=P&productId=8460")

    for path in ["pub/settle/stlcur", "pub/settle/stleqt", "pub/settle/stlint"]:
        probe(f"settlement file {path}", f"https://www.cmegroup.com/ftp/{path}")

    probe("daily bulletin index", "https://www.cmegroup.com/ftp/bulletin/")

    print("=" * 70)
    print("ROUTE 3: baseline sanity checks")
    print("=" * 70 + "\n")

    probe("cmegroup.com homepage (is the DOMAIN reachable at all?)",
          "https://www.cmegroup.com/", {"User-Agent": UA})
    probe("datamine (needs free account; 401 = reachable, good sign)",
          "https://datamine.cmegroup.com/cme/api/v1/list?dataset=cme.settle")
    probe("control: deribit (proves outbound HTTPS works from this runner)",
          "https://www.deribit.com/api/v2/public/get_time")

    print("Probe finished. Read the [ OK ] lines above -- those are the "
          "endpoints a daily job could use.")


if __name__ == "__main__":
    main()
    sys.exit(0)
