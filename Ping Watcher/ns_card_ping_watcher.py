#!/usr/bin/env python3
import json
import os
import sys
import time
import argparse
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from collections import deque

import requests

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except (AttributeError, ValueError):
    pass

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "ping_config.json")
STATE_FILE = os.path.join(BASE_DIR, "ping_state.json")

AUTHOR_CONTACT = "zeuspa40@gmail.com"
AUTHOR_NATION = "Laudesia"


class SlidingWindowPacer:
    def __init__(self, max_requests=45, window_seconds=30, verbose=False,
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
            print(f"[ratelimit] 429, sleeping {retry_after}s")
            time.sleep(retry_after + 0.5)
            continue
        if resp.status_code == 403:
            print("[error] 403 — check your nation_name in ping_config.json")
            return None
        if resp.status_code != 200:
            print(f"[error] status {resp.status_code}: {resp.text[:200]}")
            time.sleep(3)
            continue

        try:
            return ET.fromstring(resp.content)
        except ET.ParseError as e:
            print(f"[error] XML parse failed: {e}")
            return None

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


def normalize_nation(name):
    return (name or "").strip().lower().replace(" ", "_")


import re

CARD_URL_RE = re.compile(r"card=(\d+)/season=(\d+)")


def clean_cell(val):
    val = (val or "").strip()
    if val.endswith(".0") and val[:-2].isdigit():
        return val[:-2]
    return val


def fetch_tsv_table(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[error] failed to fetch sheet {url}: {e}")
        return [], []
    reader = csv.reader(io.StringIO(resp.text), delimiter="\t")
    all_rows = list(reader)
    if not all_rows:
        return [], []
    headers = [h.strip().lower() for h in all_rows[0]]
    rows = [r for r in all_rows[1:] if any(cell.strip() for cell in r)]
    return headers, rows


def _cell(headers, row, i):
    return clean_cell(row[i]) if i < len(row) else ""


def _first_by_header(headers, row, *aliases):
    for i, h in enumerate(headers):
        if h in aliases:
            v = _cell(headers, row, i)
            if v:
                return v
    return ""


def _all_by_header_contains(headers, row, *substrings):
    vals = []
    for i, h in enumerate(headers):
        if any(s in h for s in substrings):
            v = _cell(headers, row, i)
            if v:
                vals.append(v)
    return vals


def _truthy(val):
    return val.strip().lower() in ("true", "yes", "y", "1", "x")


def extract_card_from_url(url):
    m = CARD_URL_RE.search(url)
    if not m:
        return None
    return {"cardid": m.group(1), "season": m.group(2)}


def load_tracked_cards(config, debug_raw=False):
    url = config.get("tracked_cards_sheet_url")
    if not url:
        return config.get("tracked_cards", [])
    headers, rows = fetch_tsv_table(url)
    cards = []
    for row in rows:
        cardid = _first_by_header(headers, row, "cardid", "card id", "id")
        season = _first_by_header(headers, row, "season")
        name = _first_by_header(headers, row, "name", "card name") or cardid
        if cardid and season:
            cards.append({"cardid": cardid, "season": season, "name": name})
    if debug_raw:
        print(f"[debug] tracked_cards from sheet ({len(cards)} row(s)): {cards}")
    return cards


def looks_like_valid_discord_id(val):
    return val.isdigit() and 15 <= len(val) <= 20


def load_users(config, debug_raw=False):
    url = config.get("users_sheet_url")
    if not url:
        return config.get("users", [])
    headers, rows = fetch_tsv_table(url)
    has_opt_in_column = any(
        h in ("opt_in", "opt in", "opted_in", "opted in", "ping me", "opt-in") for h in headers
    )

    users = []
    for row in rows:
        nation = _first_by_header(headers, row, "nation")
        discord_username = _first_by_header(headers, row, "discord", "discord username")
        discord_id = _first_by_header(headers, row, "discord id", "discord_id", "id")
        display_name = _first_by_header(headers, row, "name", "username") or discord_username or nation
        if not (nation and discord_id):
            continue
        if not looks_like_valid_discord_id(discord_id):
            print(f"[warn] skipping {display_name or nation}: Discord ID '{discord_id}' doesn't look valid "
                  f"(expected a 17-19 digit number — check the sheet column isn't formatted as Number)")
            continue

        card_urls = _all_by_header_contains(headers, row, "backing card", "additional backing")
        assigned = []
        seen = set()
        for u in card_urls:
            c = extract_card_from_url(u)
            if c and (c["cardid"], c["season"]) not in seen:
                seen.add((c["cardid"], c["season"]))
                assigned.append(c)

        opt_in = _truthy(_first_by_header(headers, row, "opt_in", "opt in", "opted_in", "opted in", "ping me", "opt-in")) \
            if has_opt_in_column else False

        users.append({
            "name": display_name,
            "discord_id": discord_id,
            "nation": nation,
            "opt_in": opt_in,
            "assigned_cards": assigned,
        })
    if debug_raw:
        print(f"[debug] users from sheet ({len(users)} row(s)):")
        for u in users:
            print(f"  {u['name']} (nation={u['nation']}, discord_id={u['discord_id']}, "
                  f"opt_in={u['opt_in']}, assigned_cards={u['assigned_cards']})")
    return users


def get_card_bundle(cardid, season, user_agent, api_version=None, debug_raw=False):
    params = {"q": "card info markets trades", "cardid": cardid, "season": season}
    if api_version:
        params["v"] = str(api_version)
    root = api_get(params, user_agent)
    if root is None:
        return {"name": None, "bidding_nations": set(), "latest_trade": None, "market_value": None}
    if debug_raw:
        print(f"[debug] raw card bundle XML {cardid}/{season}:")
        print(ET.tostring(root, encoding="unicode"))
    return parse_card_bundle(root)


def parse_card_bundle(root):
    name = _text(root, ".//NAME")
    market_value = _float(root, ".//MARKET_VALUE")

    bidding_nations = set()
    markets = root.find(".//MARKETS")
    if markets is not None:
        for market in markets.findall("MARKET"):
            if (_text(market, "TYPE") or "").lower() == "bid":
                nation = _text(market, "NATION")
                if nation:
                    bidding_nations.add(normalize_nation(nation))

    latest_trade = None
    trades_container = root.find(".//TRADES")
    if trades_container is not None:
        best_ts = -1
        for trade in trades_container.findall("TRADE"):
            ts_raw = _text(trade, "TIMESTAMP")
            try:
                ts = int(ts_raw) if ts_raw else -1
            except ValueError:
                ts = -1
            price = _float(trade, "PRICE")
            if price is not None and ts > best_ts:
                best_ts = ts
                latest_trade = {
                    "price": price,
                    "buyer": _text(trade, "BUYER"),
                    "seller": _text(trade, "SELLER"),
                    "timestamp": ts,
                }

    return {
        "name": name,
        "bidding_nations": bidding_nations,
        "latest_trade": latest_trade,
        "market_value": market_value,
    }


def card_page_url(cardid, season):
    return f"https://www.nationstates.net/page=deck/card={cardid}/season={season}"


def send_discord_ping(webhook_url, user, missing_cards, ping=True):
    lines = []
    for c in missing_cards:
        url = card_page_url(c["cardid"], c["season"])
        name = c.get("name") or f"Card #{c['cardid']}"
        trade = c.get("latest_trade")
        if trade:
            last_sale = f"Last sold by `{trade['seller']}` for **{trade['price']:.2f}** to `{trade['buyer']}`"
        elif c.get("market_value") is not None:
            last_sale = f"est. market value **{c['market_value']:.2f}** bank (no trade history)"
        else:
            last_sale = "no sale data available"
        lines.append(f"- [{name}]({url}) (S{c['season']}) — {last_sale}")
    payload = {
        "content": f"<@{user['discord_id']}>" if ping else "",
        "embeds": [{
            "title": f"{user['name']} — no bid on {len(missing_cards)} card(s)",
            "description": "\n".join(lines),
            "color": 0x5865F2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code >= 300:
            print(f"[error] discord webhook returned {resp.status_code}: {resp.text[:200]}")
    except requests.RequestException as e:
        print(f"[error] failed to post to discord: {e}")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def run_check(config, state, debug_raw=False):
    user_agent = (
        f"CardPingWatcher/1.0 "
        f"(author:{AUTHOR_NATION}; contact:{AUTHOR_CONTACT}; user:{config['nation_name']})"
    )
    print(f"[{datetime.now().isoformat(timespec='seconds')}] using User-Agent: {user_agent}")
    api_version = config.get("api_version")
    webhook_url = config["discord_webhook_url"]

    global_cards = load_tracked_cards(config, debug_raw)
    users = load_users(config, debug_raw)

    if not users:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] no members found — nothing to check")
        return

    global_keys = {(c["cardid"], c["season"]) for c in global_cards}
    for u in users:
        u["_required"] = {(c["cardid"], c["season"]) for c in u.get("assigned_cards", [])} | global_keys

    unique_cards = sorted(global_keys.union(*(u["_required"] for u in users)))
    if not unique_cards:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] no cards to check for any member")
        return

    print(f"[{datetime.now().isoformat(timespec='seconds')}] checking {len(unique_cards)} unique card(s) "
          f"for {len(users)} member(s)...")

    bundles = {}
    for i, (cardid, season) in enumerate(unique_cards, start=1):
        print(f"  [{i}/{len(unique_cards)}] {cardid} (S{season})...", end="", flush=True)
        bundle = get_card_bundle(cardid, season, user_agent, api_version, debug_raw)
        bundles[(cardid, season)] = bundle
        label = bundle["name"] or cardid
        print(f" {label} — {len(bundle['bidding_nations'])} bidder(s)")

    for user in users:
        norm_nation = normalize_nation(user["nation"])
        missing = []
        for key in sorted(user["_required"]):
            cardid, season = key
            bundle = bundles.get(key, {})
            has_bid = norm_nation in bundle.get("bidding_nations", set())
            state_key = f"{cardid}:{season}:{user['discord_id']}"
            already_pinged = state_key in state

            if has_bid:
                if already_pinged:
                    del state[state_key]
                continue
            if not already_pinged:
                state[state_key] = True
                missing.append({
                    "cardid": cardid,
                    "season": season,
                    "name": bundle.get("name"),
                    "latest_trade": bundle.get("latest_trade"),
                    "market_value": bundle.get("market_value"),
                })

        if missing:
            ping = bool(user.get("opt_in"))
            verb = "pinging" if ping else "posting (not opted in, no ping)"
            print(f"  {user['name']}: {verb} for {len(missing)} missing bid(s)")
            send_discord_ping(webhook_url, user, missing, ping=ping)

    save_state(state)


def main():
    parser = argparse.ArgumentParser(
        description="Checks tracked NationStates cards for missing bids and posts to Discord."
    )
    parser.add_argument("--watch", action="store_true",
                         help="Run continuously instead of a single check (uses poll_interval_seconds).")
    parser.add_argument("--debug-raw", action="store_true",
                         help="Print raw API responses -- use this if names/prices look wrong.")
    parser.add_argument("--show-ratelimit", action="store_true",
                         help="Print live API rate-limit status on every request.")
    parser.add_argument("--config", default=CONFIG_FILE,
                         help="Path to config file (default: ping_config.json next to this script).")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"[error] config not found: {args.config}\ncopy ping_config.example.json to ping_config.json and fill it in")
        sys.exit(1)

    with open(args.config, "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[error] {args.config} isn't valid JSON: {e}\n"
                  f"Check for a missing comma or quote near line {e.lineno}.")
            sys.exit(1)

    missing = [k for k in ("nation_name", "discord_webhook_url") if not config.get(k)]
    if missing:
        print(f"[error] ping_config.json missing: {', '.join(missing)}")
        sys.exit(1)

    global pacer
    pacer = SlidingWindowPacer(
        max_requests=int(config.get("max_requests_per_window", 45)),
        window_seconds=int(config.get("ratelimit_window_seconds", 30)),
        verbose=args.show_ratelimit,
        remaining_threshold=int(config.get("ratelimit_remaining_threshold", 15)),
        backoff_seconds=int(config.get("ratelimit_backoff_seconds", 60)),
    )

    state = load_state()

    if not args.watch:
        run_check(config, state, debug_raw=args.debug_raw)
        return

    min_gap = int(config.get("poll_interval_seconds", 90))
    print("watching tracked cards — Ctrl+C to stop")
    while True:
        start = time.monotonic()
        try:
            run_check(config, state, debug_raw=args.debug_raw)
        except Exception as e:
            print(f"[error] {e}")
        remaining = min_gap - (time.monotonic() - start)
        if remaining > 0:
            next_check = datetime.now() + timedelta(seconds=remaining)
            print(f"Next check at {next_check:%Y-%m-%d %H:%M:%S} "
                  f"(sleeping {remaining:.0f} seconds)")
            time.sleep(remaining)


if __name__ == "__main__":
    main()
