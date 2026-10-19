# ZoneDesk

F&O order-block and liquidity terminal for Indian stocks. One static page, no build step, no dependencies.

- Board: top Bullish / Bearish stocks by strength = (last - open) / average daily range. Stocks that cross their open more than 4 times score 0 (choppy).
- Per stock: chart with order-block zones and liquidity levels, plus stop / target / risk:reward.
- Data: Yahoo Finance, delayed about 15 minutes. Refreshes every 10 seconds while the market is open (09:15-15:30 IST, Mon-Fri), and only while the tab is visible. Falls back to simulated prices if the feed is down.

## How it works

`index.html` fetches 5-minute candles straight from a Cloudflare Worker (`worker.js`) that adds CORS headers in front of Yahoo, because Yahoo blocks direct browser calls. Change `API_BASE` in the data-feed section of `index.html` to use your own Worker:

```
npx wrangler deploy worker.js --name order-block-proxy --compatibility-date 2024-01-01
```

Free Worker quota is 100k requests/day. One open terminal tab polling every 10s uses about 70k during market hours, so a second tab at the same time can exhaust it.

## Hosting

GitHub Pages, deploy from `main` / root. Open `index.html` locally to try it.

## Disclaimer

Education only, not financial advice. Data is delayed and unofficial; do not trade on it.
