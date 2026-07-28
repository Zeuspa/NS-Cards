# NationStates Card Ping Watcher

Watches every Cardtel member's assigned NationStates Trading Card(s) for missing
bids and posts it in Discord.

## Setup

1. Run `pip install requests`

2. Update "ping_config.json" and fill in:
   - `nation_name`: tells nationstates' API the user running the script 
   - `discord_webhook_url`: from your Discord channel's webhook
   
3. Double-click `run_card_ping_watcher.bat` (Windows), or from a terminal:
   `python ns_card_ping_watcher.py`

By default it runs one check and exits. Use `--watch` for continuous
polling (uses `poll_interval_seconds` as the minimum gap between checks).

## Flags - Runtime Arguments

- `--watch` — run continuously instead of a single check
- `--debug-raw` — print the raw XML the API returns for each card
- `--show-ratelimit` — print live rate-limit numbers from the server
