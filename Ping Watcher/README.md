# NationStates Card Ping Watcher

Watches every member's assigned NationStates Trading Cards for missing
bids and posts it in Discord.

## Setup

1. `pip install -r requirements.txt` (or `pip install requests`)

2. Updated "ping_config.json" and fill in:
   - `nation_name`: the user actually running this instance
   - `discord_webhook_url`: from your Discord channel's webhook
   
3. Double-click `run_card_ping_watcher.bat` (Windows), or from a terminal:
   `python ns_card_ping_watcher.py`

By default it runs one check and exits. Use `--watch` for continuous
polling (uses `poll_interval_seconds` as the minimum gap between checks).

## Flags - Runtime Arguments

- `--watch` — run continuously instead of a single check
- `--debug-raw` — print the raw XML the API returns for each card
- `--show-ratelimit` — print live rate-limit numbers from the server
