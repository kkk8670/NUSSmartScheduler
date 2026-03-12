from __future__ import annotations

import argparse
import csv
import datetime as dt
import logging
import os
import re
import sys
import time
from typing import List, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    # Python 3.9+: zoneinfo is stdlib
    from zoneinfo import ZoneInfo
    SG_TZ = ZoneInfo("Asia/Singapore")
except Exception:
    SG_TZ = None  # fallback to naive timestamps if zoneinfo not available

CAPACITY_URL = "https://reboks.nus.edu.sg/nus_public_web/public/index.php/facilities/capacity"

# -------- HTTP session with retries --------
def build_session(timeout: int = 15) -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    })
    # attach default timeout to session by wrapping request
    original_request = sess.request
    def request_with_timeout(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return original_request(method, url, **kwargs)
    sess.request = request_with_timeout  # type: ignore[assignment]
    return sess

# -------- Parsing helpers --------
CAP_RE = re.compile(r"(?P<used>\d+)\s*/\s*(?P<total>\d+)")

def parse_capacity_cell(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Extract 'used/total' like '23/100' from arbitrary cell text."""
    if not text:
        return None, None
    m = CAP_RE.search(text.replace(",", ""))
    if not m:
        return None, None
    try:
        return int(m.group("used")), int(m.group("total"))
    except Exception:
        return None, None

def timestamp_now() -> str:
    now = dt.datetime.now(tz=SG_TZ) if SG_TZ else dt.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S%z" if SG_TZ else "%Y-%m-%d %H:%M:%S")

def scrape_capacity(session: requests.Session, save_snapshot_dir: Optional[str] = None) -> List[Dict[str, object]]:
    """Scrape the capacity table and return a list of dict rows."""
    logging.info("Fetching %s", CAPACITY_URL)
    r = session.get(CAPACITY_URL)
    r.raise_for_status()
    html = r.text

    # Optional snapshot for debugging changes
    if save_snapshot_dir:
        os.makedirs(save_snapshot_dir, exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(save_snapshot_dir, f"capacity-{ts}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        logging.debug("Saved HTML snapshot to %s", path)

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    rows_out: List[Dict[str, object]] = []
    scraped_at = timestamp_now()

    if not tables:
        logging.warning("No <table> found on page; trying list-based fallback.")
        # Fallback: maybe items are in cards/divs with capacity text
        # we will scan all text blocks that look like "Gym XYZ 34/100"
        for blk in soup.find_all(text=CAP_RE):
            cap_used, cap_total = parse_capacity_cell(blk)
            facility = blk.parent.get_text(" ", strip=True)[:200] if blk and blk.parent else "Unknown"
            rows_out.append({
                "scraped_at": scraped_at,
                "facility": facility,
                "used": cap_used,
                "total": cap_total,
                "raw": facility,
            })
        return rows_out

    # Prefer the largest table (most rows)
    main_table = max(tables, key=lambda t: len(t.find_all("tr")))
    header_cells = [th.get_text(strip=True) for th in main_table.find_all("th")]
    has_header = any(header_cells)

    # Identify column indices heuristically
    # Look for columns like 'Facility', 'Venue', 'Location', 'Capacity/Occupancy'
    facility_idx = None
    capacity_idx = None
    if has_header:
        for i, h in enumerate([h.lower() for h in header_cells]):
            if any(key in h for key in ("facility", "venue", "location", "name")) and facility_idx is None:
                facility_idx = i
            if any(key in h for key in ("capacity", "occupancy", "usage", "current")) and capacity_idx is None:
                capacity_idx = i

    # Iterate rows
    for tr in main_table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue

        # facility text
        if facility_idx is not None and facility_idx < len(tds):
            facility_text = tds[facility_idx].get_text(" ", strip=True)
        else:
            # fallback: first non-empty cell
            facility_text = ""
            for td in tds:
                t = td.get_text(" ", strip=True)
                if t:
                    facility_text = t
                    break

        # capacity text
        cap_text = ""
        if capacity_idx is not None and capacity_idx < len(tds):
            cap_text = tds[capacity_idx].get_text(" ", strip=True)
        else:
            # search all cells for pattern
            for td in tds:
                m = CAP_RE.search(td.get_text(" ", strip=True))
                if m:
                    cap_text = m.group(0)
                    break

        used, total = parse_capacity_cell(cap_text)
        raw_row = " | ".join(td.get_text(" ", strip=True) for td in tds)

        # Skip rows that don't look like data
        if not facility_text and used is None and total is None:
            continue

        rows_out.append({
            "scraped_at": scraped_at,
            "facility": facility_text,
            "used": used,
            "total": total,
            "raw": raw_row,
        })

    return rows_out

# -------- CSV handling --------
CSV_HEADERS = ["scraped_at", "facility", "used", "total", "raw"]

def append_csv(rows: List[Dict[str, object]], csv_path: str) -> None:
    if not rows:
        logging.info("No rows to write.")
        return
    file_exists = os.path.exists(csv_path)
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            # ensure keys exist
            writer.writerow({k: row.get(k, "") for k in CSV_HEADERS})
    logging.info("Appended %d rows to %s", len(rows), csv_path)

# -------- Main loop --------
def run_once(session: requests.Session, csv_path: str, snapshots: Optional[str]) -> bool:
    try:
        rows = scrape_capacity(session, save_snapshot_dir=snapshots)
        append_csv(rows[2:], csv_path)
        return True
    except Exception as e:
        logging.exception("Scrape failed: %s", e)
        return False

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape NUS REBOKS facilities capacity on a schedule.")
    p.add_argument("--interval", type=int, default=10,
                   help="Scrape interval in minutes (ignored if --once). Default: 10")
    p.add_argument("--once", action="store_true",
                   help="Run a single scrape then exit (useful for cron).")
    p.add_argument("--csv", type=str, default="./capacity_log.csv",
                   help="Path to CSV output. Default: ./capacity_log.csv")
    p.add_argument("--snapshots", type=str, default=None,
                   help="Directory to save raw HTML snapshots (optional).")
    p.add_argument("--log-level", type=str, default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Logging level. Default: INFO")
    return p.parse_args(argv)

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    session = build_session()

    if args.once:
        ok = run_once(session, args.csv, args.snapshots)
        return 0 if ok else 1

    interval_sec = max(60, args.interval * 60)  # minimum 60s
    logging.info("Starting loop: every %d min(s), writing to %s", args.interval, args.csv)
    while True:
        start = time.time()
        run_once(session, args.csv, args.snapshots)
        elapsed = time.time() - start
        sleep_for = max(5.0, interval_sec - elapsed)
        logging.debug("Sleeping for %.1f seconds", sleep_for)
        time.sleep(sleep_for)

if __name__ == "__main__":
    sys.exit(main())

