#!/usr/bin/env python3
import json
import os
import sys
import time
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import deque

import requests

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except (AttributeError, ValueError):
    pass

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

AUTHOR_CONTACT = "zeuspa40@gmail.com"
AUTHOR_NATION = "Laudesia"

class SlidingWindowPacer:
    def __init__(self, max_requests=40, window_seconds=30, verbose=False,
                 remaining_threshold=15, backoff_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.verbose = verbose
        self._timestamps = deque()
        self.remaining_threshold = remaining_threshold
        self.backoff_seconds = backoff_seconds

    def wait(self):
        now = time.monotonic()
        while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_requests:
            sleep_for = self.window_seconds - (now - self._timestamps[0]) + 0.05
            if sleep_for > 0:
                print(f"[ratelimit] pausing {sleep_for:.1f}s ({self.max_requests}/{self.window_seconds}s reached)")
                time.sleep(sleep_for)
        self._timestamps.append(time.monotonic())

    def update(self, headers):
        remaining_raw = headers.get("RateLimit-Remaining")
        if self.verbose:
            print(f"[ratelimit] server {remaining_raw}/{headers.get('RateLimit-Limit')}, "
                  f"resets {headers.get('RateLimit-Reset')}s")
        if remaining_raw is None:
            return
        try:
            remaining = int(remaining_raw)
        except ValueError:
            return
        if remaining < self.remaining_threshold:
            print(f"[ratelimit] server reports only {remaining} requests left on this IP "
                  f"(likely other traffic sharing it) — pausing {self.backoff_seconds}s")
            time.sleep(self.backoff_seconds)


pacer = SlidingWindowPacer()


def api_get(params, user_agent, retries=3):
    headers = {"User-Agent": user_agent}
    for attempt in range(1, retries + 1):
        pacer.wait()
        try:
            resp = requests.get(API_URL, params=params, headers=headers, timeout=15)
        except requests.RequestException as e:
            print(f"[error] request failed ({e}), attempt {attempt}/{retries}")
            time.sleep(5)
            continue

        pacer.update(resp.headers)

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 30))
            print(f"[ratelimit] 429 - sleeping {retry_after}s")
            time.sleep(retry_after + 0.5)
            continue
        if resp.status_code == 403:
            print("[error] 403 - check your nation name in the config.json")
            return None
        if resp.status_code != 200:
            print(f"[error] status {resp.status_code}: {resp.text[:200]}")
            time.sleep(3)
            continue

        try:
            return ET.fromstring(resp.content)
        except ET.ParseError as e:
            print(f"...attempt {attempt}/{retries}")
            time.sleep(2)
            continue

    print("[error] giving up after retries")
    return None


def _text(elem, tag):
    child = elem.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _float(elem, tag):
    val = _text(elem, tag)
    try:
        return float(val) if val is not None else None
    except ValueError:
        return None


def get_my_bids(nation, user_agent, api_version=None, debug_raw=False):
    params = {"q": "cards asksbids", "nationname": nation}
    if api_version:
        params["v"] = str(api_version)
    root = api_get(params, user_agent)
    if root is None:
        return []
    if debug_raw:
        print("[debug] raw asksbids XML:")
        print(ET.tostring(root, encoding="unicode"))
    return parse_asksbids_xml(root)


def parse_asksbids_xml(root):
    results = []
    bids_container = root.find(".//BIDS")
    asks_container = root.find(".//ASKS")
    if bids_container is not None:
        for bid in bids_container.findall("BID"):
            results.append({
                "cardid": _text(bid, "CARDID"),
                "season": _text(bid, "SEASON"),
                "price": _float(bid, "BID_PRICE"),
                "card_name": _text(bid, "NAME"),
                "type": "bid",
            })
    if asks_container is not None:
        for ask in asks_container.findall("ASK"):
            results.append({
                "cardid": _text(ask, "CARDID"),
                "season": _text(ask, "SEASON"),
                "price": _float(ask, "ASK_PRICE"),
                "card_name": _text(ask, "NAME"),
                "type": "ask",
            })
    return [r for r in results if r["cardid"] and r["price"] is not None]


def get_market(cardid, season, user_agent, api_version=None, debug_raw=False):
    params = {"q": "card markets", "cardid": cardid, "season": season}
    if api_version:
        params["v"] = str(api_version)
    root = api_get(params, user_agent)
    if root is None:
        return []
    if debug_raw:
        print(f"[debug] raw market XML {cardid}/{season}:")
        print(ET.tostring(root, encoding="unicode"))
    return parse_market_xml(root)


def parse_market_xml(root):
    results = []
    markets = root.find(".//MARKETS")
    container = markets if markets is not None else root
    for market in container.findall("MARKET"):
        entry_type = (_text(market, "TYPE") or "").lower()
        if entry_type not in ("bid", "ask"):
            continue
        results.append({
            "nation": _text(market, "NATION"),
            "price": _float(market, "PRICE"),
            "type": entry_type,
        })
    return [r for r in results if r["price"] is not None]


def card_page_url(cardid, season):
    return f"https://www.nationstates.net/page=deck/card={cardid}/season={season}"


def generate_html_report(overbid_cards, output_path, nation):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cards = sorted(overbid_cards, key=lambda x: (x["top_bid_price"] - x["your_price"]), reverse=True)

    rows = []
    for i, c in enumerate(cards):
        url = card_page_url(c["cardid"], c["season"])
        gap = c["top_bid_price"] - c["your_price"]
        rows.append(f"""
        <div class="card-row" tabindex="0" data-index="{i}">
          <div class="card-main">
            <a href="{url}" target="_blank" tabindex="-1">{c['card_name']}</a>
            <span class="season">S{c['season']}</span>
          </div>
          <div class="card-stats">
            <span class="stat"><span class="label">Your bid</span>{c['your_price']:.2f}</span>
            <span class="stat"><span class="label">Top bid</span>{c['top_bid_price']:.2f}</span>
            <span class="stat"><span class="label">By</span>{c['top_bid_nation']}</span>
            <span class="stat gap"><span class="label">Gap</span>+{gap:.2f}</span>
          </div>
        </div>""")

    rows_html = "".join(rows) if rows else '<div class="empty">You\'re not currently outbid on anything. 🎉</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NS Bid Watcher — Overbid Report ({nation})</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #1e1f24; color: #e8e8ea; margin: 2rem; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
  .meta {{ color: #9a9aa5; margin-bottom: 0.4rem; font-size: 0.9rem; }}
  .hint {{ color: #6f7580; margin-bottom: 1.5rem; font-size: 0.85rem; }}
  .count {{ color: #ff8f6b; font-weight: 600; }}
  kbd {{ background: #2a2b32; border: 1px solid #444; border-radius: 4px; padding: 0.05rem 0.4rem; font-size: 0.8rem; }}
  #card-list {{ display: flex; flex-direction: column; gap: 0.5rem; max-width: 900px; }}
  .card-row {{
    display: flex; justify-content: space-between; align-items: center;
    background: #26272e; border: 1px solid #33343c; border-radius: 8px;
    padding: 0.8rem 1rem; max-height: 100px; opacity: 1; overflow: hidden;
    transition: max-height 0.28s ease, opacity 0.22s ease, padding 0.28s ease, margin 0.28s ease, border-color 0.2s ease;
    outline: none; cursor: default;
  }}
  .card-row:focus {{ border-color: #7fb3ff; box-shadow: 0 0 0 2px rgba(127,179,255,0.25); }}
  .card-row.collapsed {{ max-height: 0; opacity: 0; padding-top: 0; padding-bottom: 0; margin: 0; border-width: 0; pointer-events: none; }}
  .card-main {{ display: flex; align-items: baseline; gap: 0.6rem; min-width: 0; }}
  .card-main a {{ color: #7fb3ff; text-decoration: none; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .card-main a:hover {{ text-decoration: underline; }}
  .season {{ color: #6f7580; font-size: 0.8rem; flex-shrink: 0; }}
  .card-stats {{ display: flex; gap: 1.2rem; flex-shrink: 0; }}
  .stat {{ display: flex; flex-direction: column; align-items: flex-end; font-size: 0.9rem; min-width: 3.5rem; }}
  .stat .label {{ color: #6f7580; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.03em; }}
  .stat.gap {{ color: #ff8f6b; font-weight: 600; }}
  .empty {{ color: #888; text-align: center; padding: 2rem; }}
  #done-message {{ display: none; color: #7fdca0; padding: 1rem 0; }}
</style>
</head>
<body>
  <h1>Overbid Report for {nation}</h1>
  <div class="meta">Generated {now_str} &nbsp;·&nbsp; <span class="count" id="remaining-count">{len(cards)}</span> card(s) currently outbid on</div>
  <div class="hint">Use <kbd>Enter</kbd> to open the top card's market page. Afer pressing <kbd>Enter</kbd> it will collapse the top card and navigate to the next. Refresh the page to restore all links.</div>
  <div id="card-list">{rows_html}</div>
  <div id="done-message">All caught up - every card has been handled 🎉</div>
<script>
  (function() {{
    var rows = Array.prototype.slice.call(document.querySelectorAll('.card-row'));
    var remainingEl = document.getElementById('remaining-count');
    var doneMsg = document.getElementById('done-message');

    function updateCount() {{
      var remaining = rows.filter(function(r) {{ return !r.classList.contains('collapsed'); }}).length;
      if (remainingEl) remainingEl.textContent = remaining;
      if (remaining === 0 && rows.length > 0) doneMsg.style.display = 'block';
    }}

    function nextFocusable(fromIndex) {{
      for (var i = fromIndex + 1; i < rows.length; i++) {{ 
        if (!rows[i].classList.contains('collapsed')) return rows[i]; 
      }}
      for (var i = 0; i < fromIndex; i++) {{ 
        if (!rows[i].classList.contains('collapsed')) return rows[i]; 
      }}
      return null;
    }}

    rows.forEach(function(row) {{
      row.addEventListener('keydown', function(e) {{
        if (e.key !== 'Enter') return;
        e.preventDefault();
        var link = row.querySelector('a');
        var idx = parseInt(row.getAttribute('data-index'), 10);

        if (link) {{
          link.click();
        }}

        row.classList.add('collapsed');
        row.setAttribute('tabindex', '-1');
        updateCount();

        var next = nextFocusable(idx);
        if (next) {{
          setTimeout(function() {{
            next.focus();
          }}, 10);
        }}
      }});
    }});

    // Initial focus
    if (rows.length > 0) rows[0].focus();
  }})();
  </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] wrote {output_path} ({len(cards)} outbid)")


def run_check(config, debug_raw=False):
    user_agent = (
        f"NSBidWatcher/2.1 "
        f"(author:{AUTHOR_NATION}; contact:{AUTHOR_CONTACT}; user:{config['nation_name']})"
    )
    print(f"[{datetime.now().isoformat(timespec='seconds')}] using User-Agent: {user_agent}")
    nation = config["check_nation"]
    api_version = config.get("api_version")
    html_path = config.get("html_report_path", "overbid_report.html")

    my_bids = [b for b in get_my_bids(nation, user_agent, api_version, debug_raw) if b["type"] == "bid"]
    if not my_bids:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] no active bids for {nation}")
        generate_html_report([], html_path, nation)
        return

    unique_cards = {}
    for b in my_bids:
        key = (b["cardid"], b["season"])
        if key not in unique_cards or b["price"] > unique_cards[key]["price"]:
            unique_cards[key] = b

    total = len(unique_cards)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] sweeping {total} unique bid card(s)...")

    overbid_cards = []
    start = time.monotonic()
    for i, ((cardid, season), mybid) in enumerate(unique_cards.items(), start=1):
        your_price = mybid["price"]
        card_name = mybid.get("card_name") or cardid
        print(f"  [{i}/{total}] {card_name} (S{season}, {cardid})...", end="", flush=True)

        market = get_market(cardid, season, user_agent, api_version, debug_raw)
        bids_only = [m for m in market if m["type"] == "bid"]
        if not bids_only:
            print(" no bids")
            continue

        top_bid = max(bids_only, key=lambda b: b["price"])
        if top_bid["price"] > your_price and top_bid["nation"] != nation:
            print(f" OUTBID ({your_price} vs {top_bid['price']} by {top_bid['nation']})")
            overbid_cards.append({
                "cardid": cardid, "season": season, "card_name": card_name,
                "your_price": your_price, "top_bid_price": top_bid["price"],
                "top_bid_nation": top_bid["nation"],
            })
        else:
            print(" safe")

        if total > 20 and i % 20 == 0:
            print(f"  ...{i}/{total} ({time.monotonic()-start:.0f}s elapsed)")

    print(f"[{datetime.now().isoformat(timespec='seconds')}] sweep complete in {time.monotonic()-start:.0f}s")
    generate_html_report(overbid_cards, html_path, nation)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--debug-raw", action="store_true")
    parser.add_argument("--show-ratelimit", action="store_true")
    parser.add_argument("--config", default=CONFIG_FILE)
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"[error] config not found: {args.config}\ncopy config.example.json to config.json and fill it in")
        sys.exit(1)

    with open(args.config, "r") as f:
        config = json.load(f)

    missing = [
        k for k in ("nation_name", "check_nation")
        if not config.get(k)
    ]
    if missing:
        print(f"[error] config.json missing: {', '.join(missing)}")
        sys.exit(1)

    global pacer
    pacer = SlidingWindowPacer(
        max_requests=int(config.get("max_requests_per_window", 45)),
        window_seconds=int(config.get("ratelimit_window_seconds", 30)),
        verbose=args.show_ratelimit,
        remaining_threshold=int(config.get("ratelimit_remaining_threshold", 15)),
        backoff_seconds=int(config.get("ratelimit_backoff_seconds", 60)),
    )

    if not args.watch:
        run_check(config, debug_raw=args.debug_raw)
        return

    min_gap = int(config.get("poll_interval_seconds", 90))
    print(f"watching '{config['check_nation']}' — Ctrl+C to stop")
    while True:
        start = time.monotonic()
        try:
            run_check(config, debug_raw=args.debug_raw)
        except Exception as e:
            print(f"[error] {e}")
        remaining = min_gap - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(remaining)


if __name__ == "__main__":
    main()
