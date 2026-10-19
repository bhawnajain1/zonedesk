// Cloudflare Worker: CORS proxy for Yahoo Finance candles (same /api/candles contract as server.js).
const HEADERS = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' }

export default {
  async fetch(req) {
    const url = new URL(req.url)
    if (url.pathname !== '/api/candles') return new Response('not found', { status: 404, headers: HEADERS })
    const symbol = url.searchParams.get('symbol') || '^NSEI'
    const interval = url.searchParams.get('interval') || '1d'
    const range = url.searchParams.get('range') || '6mo'
    const yahoo = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=${interval}&range=${range}`
    try {
      const r = await fetch(yahoo, { headers: { 'User-Agent': 'Mozilla/5.0' }, cf: { cacheTtl: 60, cacheEverything: true } })
      const d = (await r.json()).chart.result[0]
      const q = d.indicators.quote[0]
      const candles = []
      d.timestamp.forEach((t, i) => {
        if (q.open[i] == null || q.close[i] == null) return
        candles.push({ t: t * 1000, o: q.open[i], h: q.high[i], l: q.low[i], c: q.close[i] })
      })
      return new Response(JSON.stringify(candles), { headers: HEADERS })
    } catch (e) {
      return new Response(JSON.stringify({ error: 'fetch failed for ' + symbol }), { status: 502, headers: HEADERS })
    }
  },
}
