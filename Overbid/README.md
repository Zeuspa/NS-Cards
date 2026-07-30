# NationStates Bid Watcher

-Checks your NationStates Trading Card bids

-Writes an HTML report of everything you're outbid on

-Navigate links using "enter" to each card's market page

## Setup and usage

1. run `pip install requests`
2. edit `config.json` and fill in:
   - `nation_name`: identify yourself for the API
   - `check_nation`: the nation you want to check
   - `html_report_path`: where to write the report (default `overbid_report.html`)
     
*Avoid Touching other rate limiting Settings - Unless you know what you are doing*

3. Double click `run_bid_watcher.bat` (Windows).
   Or from a terminal: `python ns_bid_watcher.py`
4. Open `overbid_report.html` in a browser.

By default the script runs one sweep and exits, nothing runs in the background. 
You can use `--watch` for continuous polling instead.

## Flags - Runtime arguments

- `--watch` — run continuously instead of a single sweep (uses
  `poll_interval_seconds` as the minimum gap between sweeps)
- `--debug-raw` — print the raw XML the API returns for every request,
  useful if a result looks wrong and you want to see exactly what the
  server sent
- `--show-ratelimit` — print live rate-limit numbers as they come back
  from the server, so you can watch the actual pacing in real time
