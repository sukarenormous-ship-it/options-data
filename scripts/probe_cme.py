#!/usr/bin/env python3
"""Throwaway reachability probe for CME open-interest sources.

Answers one question before any real work starts: which CME endpoints, if
any, respond to a GitHub Actions runner? Prints a status line per candidate
and never fails the job -- the log IS the result.

Targets the two products we actually want: WTI crude oil options (NYMEX,
underlying CL) and gold options (COMEX, underlying GC). Note these are two
different exchanges under the CME Group umbrella, so the settlement-file
mirror needs stlnymex/stlcomex, not the CME-proper files.

Delete this file once the answer is recorded.
"""

import gzip
import io
import json
import sys
import urllib.error
import urllib.parse
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

# (product slate group, exchange, what we are looking for)
TARGETS = [
    ("Energy", "NYMEX", "WTI crude oil options (CL / LO)"),
    ("Metals", "COMEX", "gold options (GC / OG)"),
]


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
            print(f"        {raw[:240]!r}")
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        body = exc.read()[:240]
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


def discover_option_products(group: str, exchange: str, wanted: str) -> dict[str, str]:
    """Return {label: numeric productId} for option products in a group."""
    status, raw = probe(
        f"product slate: {group}/{exchange} -- looking for {wanted}",
        "https://www.cmegroup.com/CmeWS/mvc/ProductSlate/V2/List"
        f"?pageNumber=1&pageSize=500&sortField=globexCode&sortAsc=true"
        f"&group={urllib.parse.quote(group)}&exchange={exchange}")
    if status != 200 or not raw:
        return {}

    found: dict[str, str] = {}
    try:
        products = json.loads(raw).get("products", [])
    except Exception as exc:
        print(f"        (could not parse product slate: {exc})\n")
        return {}

    print(f"        {len(products)} products in {group}/{exchange}; options only:")
    for p in products:
        # cleared-as tells futures from options; fall back to the name
        kind = (p.get("cleared") or p.get("clearedAs") or "").lower()
        name = p.get("name", "")
        if "option" not in kind and "option" not in name.lower():
            continue
        code = p.get("globex") or p.get("globexSymbol") or p.get("clearing") or "?"
        label = f"{code:<8} {name}"
        found[label] = str(p.get("id"))
        print(f"          {p.get('id'):>8}  {label}")
    print()
    return found


def main() -> None:
    trade_date = prev_business_day()
    ymd = trade_date.strftime("%Y%m%d")
    slash = trade_date.strftime("%m/%d/%Y")
    print(f"Probing CME for trade date {trade_date} ({ymd})")
    print("Targets: WTI crude options (NYMEX) and gold options (COMEX)\n")

    print("=" * 70)
    print("ROUTE 1: CmeWS JSON (the API behind cmegroup.com's own OI pages)")
    print("=" * 70 + "\n")

    product_ids: dict[str, str] = {}
    for group, exchange, wanted in TARGETS:
        product_ids.update(discover_option_products(group, exchange, wanted))

    # Fall back so the rest of the probe still runs if the slate is blocked.
    candidates = list(product_ids.items())[:6]
    if not candidates:
        print("        (no productIds discovered -- trying the endpoint shape "
              "anyway with a placeholder id)\n")
        candidates = [("placeholder", "190")]

    for label, pid in candidates:
        probe(f"volume+OI detail by strike -- {label} (id={pid})",
              f"https://www.cmegroup.com/CmeWS/mvc/Volume/Details/O/{pid}/{ymd}/G")

    for label, pid in candidates[:2]:
        probe(f"settlements (options) -- {label} (id={pid})",
              f"https://www.cmegroup.com/CmeWS/mvc/Settlements/Options/Settlements/{pid}/OOF"
              f"?tradeDate={slash}&strategy=DEFAULT")

    print("=" * 70)
    print("ROUTE 2: file exports / public ftp mirror (usually no bot wall)")
    print("=" * 70 + "\n")

    probe("volume+OI product list export (xls)",
          f"https://www.cmegroup.com/CmeWS/exp/voiProductsViewExport.ctl"
          f"?media=xls&tradeDate={slash}&reportType=F&sortField=vol&sortAsc=false")

    for label, pid in candidates[:2]:
        probe(f"volume+OI per-strike export -- {label} (id={pid})",
              f"https://www.cmegroup.com/CmeWS/exp/voiProductDetailsViewExport.ctl"
              f"?media=xls&tradeDate={slash}&reportType=P&productId={pid}")

    # NYMEX = energy (WTI), COMEX = metals (gold). These are the right two.
    for path in ["pub/settle/stlnymex", "pub/settle/stlcomex"]:
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
