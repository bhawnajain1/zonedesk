"""ZoneDesk backend: serves index.html and /api/candles (yfinance, ~15 min delayed).

Run locally:  pip install -r requirements.txt && python app.py
"""
import logging
import os
import re
import time
from pathlib import Path

import yfinance as yf
from flask import Flask, jsonify, request, send_from_directory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("zonedesk")

app = Flask(__name__)
HERE = Path(__file__).parent
CACHE_SECONDS = 60
MAX_SYMBOLS = 60
MIN_CANDLES = 10
cache = {}  # tuple(sorted syms) -> (fetched_at, response dict)


@app.get("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/api/candles")
def candles():
    raw = request.args.get("syms", "").split(",")
    syms = [s for s in raw if re.fullmatch(r"[A-Z0-9&-]{1,20}", s)][:MAX_SYMBOLS]
    log.info("candles request: %d valid of %d symbols", len(syms), len(raw))
    if not syms:
        return jsonify(error="no valid symbols"), 400

    key = tuple(sorted(syms))
    hit = cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        log.info("cache hit (age %.0fs)", time.time() - hit[0])
        return jsonify(hit[1])

    try:
        result = fetch_from_yfinance(syms)
    except Exception:
        log.exception("yfinance fetch failed")
        if hit:
            log.info("serving stale cache (age %.0fs)", time.time() - hit[0])
            return jsonify(hit[1])
        return jsonify(error="upstream data unavailable"), 502

    cache[key] = (time.time(), result)
    log.info("fetched %d symbols, %d missing", len(result["data"]), len(result["missing"]))
    return jsonify(result)


def fetch_from_yfinance(syms):
    tickers = [s + ".NS" for s in syms]
    intraday = yf.download(tickers, period="5d", interval="5m", group_by="ticker",
                           progress=False, threads=True, auto_adjust=False)
    daily = yf.download(tickers, period="1mo", interval="1d", group_by="ticker",
                        progress=False, threads=True, auto_adjust=False)

    data, missing = {}, []
    for sym, tk in zip(syms, tickers):
        try:
            df = intraday[tk].dropna()
            dd = daily[tk].dropna()
            if df.empty or dd.empty:
                raise ValueError("empty frame")
            last_day = df.index[-1].date()          # newest session only (holiday/weekend safe)
            today = df[[d.date() == last_day for d in df.index]]
            if len(today) < MIN_CANDLES:
                raise ValueError("only %d candles" % len(today))
            avg_range = float((dd["High"] - dd["Low"]).tail(14).mean())
            data[sym] = {
                "candles": [{"o": float(r.Open), "h": float(r.High), "l": float(r.Low), "c": float(r.Close)}
                            for r in today.itertuples()],
                "avgDailyRange": avg_range,
                "session": str(last_day),
            }
        except Exception as e:
            log.warning("skip %s: %s", sym, e)
            missing.append(sym)
    return {"source": "yfinance (delayed ~15 min)", "data": data, "missing": missing}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
