# my-dashboard Phase 1 — Session Wrap-up & Pitfalls
Date: 2026-06-19

---

## What We Built

A personal daily briefing dashboard at `C:\Users\User\my-dashboard` using:

- React 19 + TypeScript 6 + Vite 8
- TanStack Query v5 (data fetching, caching, retry)
- Recharts v3 (SVG line charts)
- CSS Modules (dark theme, 2-column responsive grid)
- dayjs + relativeTime ("Updated X ago" footers)

### 5 Panels

| Panel    | Data Source                     | Status              |
|----------|---------------------------------|---------------------|
| ☀️ Weather  | OpenWeatherMap API              | ✅ Live             |
| 📈 Stocks  | Yahoo Finance `/v8/finance/chart`| ✅ Live             |
| 📰 Top News | NewsAPI.org                    | ✅ Live             |
| 🗓 Calendar | Google Calendar MCP            | ⏳ Phase 2          |
| 📧 Email   | Gmail MCP                      | ⏳ Phase 2          |

### Final State
- Weather: Taipei 25°C, Broken Clouds, 5-day temperature trend line
- Stocks: AAPL / TSLA / NVDA — real-time price, change %, 1-month trend lines
- News: 8 real headlines (CNN, NPR, CNBC, TechCrunch…)
- Calendar / Email: ⚠️ error banners — MCP not connected (Phase 2 expected)
- Git: initial commit `26fcd71`, 48 files, `.env` excluded from repo

---

## Architecture Decisions

**1. Yahoo Finance over Alpha Vantage**
Alpha Vantage free tier: 25 calls/day, 1 req/sec. With 3 symbols × 2 endpoints = 6
simultaneous calls, rate limits were consistently hit. Yahoo Finance
`/v8/finance/chart/{symbol}?interval=1d&range=1mo` returns both current price (`meta`)
and full OHLCV history (`indicators`) in a single call — no API key required.

**2. Vite dev proxy for CORS bypass**
Browser `fetch()` is blocked by CORS for `newsapi.org` and `query1.finance.yahoo.com`.
Vite's `server.proxy` rewrites `/api/news` and `/api/finance` at the Node.js layer,
bypassing browser CORS entirely. Configured in `vite.config.ts`.

**3. NewsAPI auth via `X-Api-Key` header**
NewsAPI returns 401 if the key is passed as a query param (`?apiKey=...`).
The correct method is the `X-Api-Key` request header.

**4. Zero-mock-data rule**
Every panel shows either real API data or an explicit ⚠️ error banner with timestamp.
No empty states, no placeholder numbers.

---

## Pitfalls Encountered

### 1. Alpha Vantage Rate Limit (25 calls/day, 1 req/sec)
- **Symptom:** TSLA data missing; AAPL and NVDA showed but TSLA timed out.
- **Root cause:** 6 fetch requests fired simultaneously on mount, exceeding the burst limit.
- **Attempted fix:** Stagger delays (`i * 1500ms`). Partial improvement only.
- **Final fix:** Switched entirely to Yahoo Finance — no key, no rate limit, 1 call per symbol.

### 2. StocksPanel Runtime Crash (`undefined.toFixed`)
- **Symptom:** After switching to Yahoo Finance, the entire React tree went blank.
- **Root cause:** Yahoo Finance `/v8/finance/chart` does **not** return `regularMarketChange`
  or `regularMarketChangePercent` in the `meta` object. The original code called `.toFixed(2)`
  on `undefined`, crashing React.
- **Fix:** Calculate manually from fields that ARE present:
  ```ts
  const price = result.meta.regularMarketPrice
  const prevClose = result.meta.chartPreviousClose ?? price
  const change = price - prevClose
  const changePercent = prevClose !== 0 ? ((price - prevClose) / prevClose) * 100 : 0
  ```

### 3. NewsAPI 401 Unauthorized (two separate causes)
- **Root cause A:** Key passed as query param — must use `X-Api-Key` header instead.
- **Root cause B:** The original key was invalid/unverified.
- **Fix:** Corrected auth method + replaced with a valid key from local env store.

### 4. Page Flashing / Blank Screen at `localhost:5173`
- **Symptom:** Page flashed briefly then went blank; no stable render.
- **Root cause 1:** StocksPanel crash (Pitfall 2) caused React to unmount the whole tree.
- **Root cause 2:** 10 zombie `node` processes from repeated dev server restarts; one at
  344% CPU making Vite HMR behave erratically.
- **Fix:** `Get-Process node | Stop-Process -Force`, restart a single clean Vite instance,
  hard-refresh browser (`Ctrl+Shift+R`).

### 5. `file:///` Opens Blank Page
- **Root cause:** Vite apps require a web server. `file://` has no module resolution,
  no proxy, and browsers block ES module loading over that protocol.
- **Fix:** Always use `http://localhost:5173` (`npm run dev`).

### 6. Screenshot Automation — GPU Black Content Area
- **Symptom:** PowerShell `CopyFromScreen` captured the window frame but content was black.
- **Root cause:** Chrome uses GPU/DirectComposition for page content; BitBlt only captures
  the GDI layer.
- **Fix:** Use `chrome --headless=new --screenshot` or puppeteer with `--disable-gpu` and
  `executablePath` pointing to the system Chrome.

### 7. Multiple Zombie Node Processes
- **Root cause:** Each hidden `Start-Process "npm run dev"` launched a new node process
  without terminating the previous one.
- **Fix:** Always `Get-Process node | Stop-Process -Force` before restarting Vite.

### 8. `--virtual-time-budget` Collapses `setTimeout`
- **Root cause:** This Chrome headless flag advances virtual time instantly, causing all
  `setTimeout` callbacks to fire simultaneously — stagger delays become useless.
- **Note:** Only affects headless automation, not real browser usage.

### 9. Puppeteer Bundled Chromium Shows Black Screenshot
- **Root cause:** Puppeteer's bundled Chromium had compatibility issues with Vite's ES
  module serving in headless mode.
- **Fix:** Pass `executablePath` to use the system Chrome installation instead.

---

## File Structure (final)

```
my-dashboard/
├── .env                        ← API keys (gitignored — never commit)
├── .env.example                ← template for new developers
├── .gitignore
├── vite.config.ts              ← proxy: /api/news, /api/finance
└── src/
    ├── App.tsx                 ← viewMode state + 5-panel grid
    ├── config/index.ts         ← typed env vars wrapper
    ├── types/                  ← app.ts, weather.ts, stocks.ts, news.ts
    ├── services/               ← weather.ts, stocks.ts, news.ts
    ├── hooks/                  ← useWeather, useStocks, useNews
    ├── utils/time.ts           ← dayjs helpers (timeAgo, formatDate)
    └── components/
        ├── PanelWrapper        ← loading skeleton / error / success shell
        ├── ui/KpiCard          ← metric display card
        ├── ui/ErrorBanner      ← ⚠️ error banner
        ├── charts/TrendLine    ← Recharts ResponsiveContainer wrapper
        ├── layout/DashboardHeader
        ├── layout/ViewModeTabs ← Daily / Weekly / On-Demand tabs
        └── panels/             ← WeatherPanel, StocksPanel, NewsPanel,
                                   CalendarPanel, EmailPanel
```

---

## Phase 2 Roadmap

- Google Calendar MCP → real events replacing CalendarPanel error banner
- Gmail MCP → real email summary replacing EmailPanel error banner
- Obsidian MCP → ActivityHeatmap panel (contribution graph style)
- Weekly view → 30-day TrendLine, email volume BarChart, Obsidian heatmap
- Auto-launch → cron at 07:55 opens dashboard in browser daily

---

## Dev Commands

```powershell
# Start dev server (required before opening browser)
cd C:\Users\User\my-dashboard
npm run dev
# Open: http://localhost:5173

# Kill zombie node processes before restart
Get-Process node | Stop-Process -Force

# Production preview
npm run build && npm run preview
# Open: http://localhost:4173
```
