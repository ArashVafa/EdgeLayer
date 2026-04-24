# EdgeLayer — Claude Code Project Prompt

## What is EdgeLayer?

EdgeLayer is a data-driven pre-bet intelligence platform for Premier League sports betting. A user enters a player name, and the system analyzes 13 dimensions of data to produce an Edge Score (0-100), confidence level, risk indicators, and a narrative summary in three modes (aggressive, conservative, average). Think of it as a Bloomberg Terminal for sports betting intelligence.

The concept originated from my collaborator Hesam. I need to build a working prototype he can access via URL and give feedback on.

## Tech Stack

- **Backend:** Python + FastAPI
- **Database:** SQLite (migrate to Postgres later)
- **Scraping:** httpx + BeautifulSoup, scheduled via APScheduler
- **Narrative Generation:** Anthropic Claude API (claude-sonnet-4-20250514) — called only for generating the 3 narrative modes, NOT for data gathering
- **Frontend:** React (Vite) with Tailwind CSS
- **Deployment target:** Backend on Railway or Fly.io, Frontend on Vercel

## Project Structure

```
edgelayer/
├── backend/
│   ├── main.py              # FastAPI app + CORS
│   ├── config.py            # API keys (env vars), scrape intervals
│   ├── db.py                # SQLite setup, schema creation, query helpers
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── understat.py     # Player stats, xG, shot data, match logs
│   │   ├── injuries.py      # Scrape premierinjuries.com for injury table
│   │   ├── fixtures.py      # football-data.org API for fixtures/results
│   │   └── odds.py          # The Odds API for betting lines
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── dimensions.py    # Calculate scores for each of the 13 dimensions
│   │   ├── scorer.py        # Aggregate dimension scores into Edge Score
│   │   └── narrative.py     # Claude API call — pass structured data, get narratives
│   ├── scheduler.py         # APScheduler config for periodic scraping
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js           # Axios calls to backend
│   │   ├── components/
│   │   │   ├── PlayerSearch.jsx    # Search bar with autocomplete
│   │   │   ├── Dashboard.jsx       # Main report layout
│   │   │   ├── EdgeScore.jsx       # Circular score ring
│   │   │   ├── MatchStrip.jsx      # Next match context bar
│   │   │   ├── MetricsGrid.jsx     # Key stats cards
│   │   │   ├── MatchLog.jsx        # Recent match table
│   │   │   ├── ShotProfile.jsx     # Shot distribution bars
│   │   │   ├── DimensionCard.jsx   # Individual dimension analysis
│   │   │   ├── RiskIndicators.jsx  # Risk grid
│   │   │   └── NarrativePanel.jsx  # Tabbed narrative (agg/avg/con)
│   │   └── styles/
│   └── package.json
├── .env.example
└── README.md
```

## Database Schema (SQLite)

```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    team TEXT,
    position TEXT,
    understat_id INTEGER UNIQUE,
    fotmob_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER REFERENCES players(id),
    season TEXT,          -- '2025-2026'
    goals INTEGER,
    assists INTEGER,
    xG REAL,
    xA REAL,
    shots INTEGER,
    shots_on_target INTEGER,
    key_passes INTEGER,
    minutes INTEGER,
    appearances INTEGER,
    npxG REAL,
    yellow_cards INTEGER,
    red_cards INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE match_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER REFERENCES players(id),
    date TEXT,
    opponent TEXT,
    home_away TEXT,       -- 'H' or 'A'
    competition TEXT,     -- 'Premier League', 'Champions League', etc.
    result TEXT,          -- '2-1 W', '0-0 D', etc.
    minutes INTEGER,
    goals INTEGER,
    assists INTEGER,
    shots INTEGER,
    xG REAL,
    rating REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE injuries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team TEXT,
    player_name TEXT,
    injury_type TEXT,
    status TEXT,          -- 'Out', 'Doubt', 'Suspended'
    expected_return TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fixtures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team TEXT,
    away_team TEXT,
    date TEXT,
    competition TEXT,
    status TEXT,          -- 'scheduled', 'completed'
    score TEXT,           -- '2-1' or NULL
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE odds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_id INTEGER REFERENCES fixtures(id),
    market TEXT,          -- 'h2h', 'totals', 'player_goals'
    outcome TEXT,         -- 'home', 'away', 'draw', 'over_2.5'
    odds REAL,
    bookmaker TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reports_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER REFERENCES players(id),
    fixture_id INTEGER REFERENCES fixtures(id),
    edge_score INTEGER,
    confidence TEXT,
    risk_level TEXT,
    dimensions_json TEXT,  -- JSON blob of all 13 dimension scores + details
    narrative_avg TEXT,
    narrative_agg TEXT,
    narrative_con TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Sources & Scraping

### 1. Understat (understat.com) — Player Stats & xG
- No API key needed
- Player pages return JSON embedded in HTML: `understat.com/player/{id}`
- Data available: goals, xG, xA, shots, shot locations, per-match logs, home/away splits
- **Scrape every 6 hours** (data only changes after matches)
- Start with Premier League players only
- To find player IDs: scrape `understat.com/league/EPL` for the player index

### 2. Premier Injuries (premierinjuries.com) — Injury Table
- Scrape the injury table HTML
- Gives: player name, team, injury type, status, expected return
- **Scrape every 2 hours**

### 3. football-data.org — Fixtures & Results
- Free API, requires API key (free registration)
- Endpoint: `api.football-data.org/v4/competitions/PL/matches`
- **Scrape daily**

### 4. The Odds API (the-odds-api.com) — Betting Lines
- Free tier: 500 requests/month
- Endpoint: gives h2h, totals, spreads from multiple bookmakers
- **Scrape every 30min on matchday, every 4hr otherwise**

### 5. Claude API — Narrative Generation Only
- Model: claude-sonnet-4-20250514
- Called ONLY when generating a report, NOT for scraping
- Pass in the structured dimension data as context
- Ask for 3 narratives: aggressive, average, conservative
- Cost target: ~$0.02-0.05 per report

## The 13 Dimensions (Scoring Engine)

Each dimension gets a score from 0-100 and a short analysis text. Here's what feeds into each:

1. **Player Performance & Form** (weight: 15%) — season stats, recent form (last 3/5/10), G-xG delta, goals/90, shot accuracy
2. **Team Context & Support** (weight: 10%) — team position, attacking stats, key teammate availability
3. **Opponent Analysis** (weight: 12%) — opponent defensive record, goals conceded, xGA, H2H record
4. **Schedule & Fatigue** (weight: 8%) — days rest, fixture congestion, upcoming important games, sub patterns
5. **Injuries & Lineup** (weight: 10%) — player fitness, teammate injuries, lineup certainty
6. **Manager & Tactical Signals** (weight: 5%) — (stub this for now — hard to automate, can add news scraping later)
7. **Market Intelligence** (weight: 10%) — odds movement, implied probabilities, value vs model probability
8. **Role & Usage Changes** (weight: 5%) — (stub this — requires heatmap data not easily available)
9. **Psychological & Narrative** (weight: 5%) — (stub this — can derive from streaks, rivalry flags, title race context)
10. **External Conditions** (weight: 3%) — (stub this — weather API easy to add later)
11. **Change Detection** (weight: 7%) — what changed since last match in form, teammates, opponent type
12. **Risk Indicators** (weight: 5%) — rotation risk, injury risk, early sub probability
13. **Output Metrics** (weight: 5%) — synthesized edge score, confidence, risk level

For MVP, fully implement dimensions 1, 2, 3, 4, 5, 7, 11, 12. Stub the rest with reasonable defaults.

**Edge Score formula:**
```
edge_score = sum(dimension_score * weight for each dimension)
```

Confidence = HIGH if edge_score >= 75, MEDIUM if >= 55, LOW if < 55
Risk = LOW if few risk flags, MEDIUM if 1-2, HIGH if 3+

## Claude API Narrative Prompt (for narrative.py)

When generating narratives, send this to Claude:

```
System: You are EdgeLayer's narrative engine. Given structured pre-bet intelligence data for a player's upcoming match, generate three betting narratives:

1. AGGRESSIVE — emphasizes upside, suggests higher-risk props (multi-goal, first scorer, parlays), acknowledges risks briefly
2. AVERAGE — balanced assessment, highlights the strongest angle, notes key risks, gives a clear verdict
3. CONSERVATIVE — emphasizes risks and caveats, suggests safer bets (shots on target, team totals), warns against high-variance props

Each narrative should be 2-4 paragraphs. Use specific numbers from the data. Mention the edge score and confidence level. Be direct and opinionated — this is decision support, not a textbook.

Do NOT include any disclaimers about gambling. The app already has those.

User: [structured JSON of all 13 dimensions + scores + player data + fixture data]
```

## API Endpoints

```
GET  /api/search?q={query}           — Search players by name, return matches
GET  /api/player/{player_id}         — Player profile + season stats
GET  /api/report/{player_id}         — Full EdgeLayer report for next fixture
POST /api/report/{player_id}/refresh — Force regenerate report (bust cache)
GET  /api/fixtures                   — Upcoming PL fixtures
GET  /api/health                     — Health check + last scrape timestamps
```

## Frontend Design

The frontend should match the aesthetic of the HTML prototype I already built. Key design tokens:

- **Background:** #0b0e11 (near-black)
- **Surface cards:** #131720
- **Accent color:** #06b6d4 (cyan) for highlights, #22c55e (green) for positive signals, #ef4444 (red) for negative, #f59e0b (amber) for warnings
- **Typography:** JetBrains Mono for numbers/data, Outfit for headings/body
- **Style:** Dark, data-dense, terminal/Bloomberg aesthetic. No rounded friendly UI — this is an intelligence tool.

The main flow:
1. Landing page with search bar (centered, minimal)
2. User types player name → autocomplete from our DB
3. Click player → full dashboard report loads
4. Dashboard matches the layout from the HTML prototype: player banner with edge score ring, match strip, key metrics grid, recent match log table, shot profile bars, 13 dimension cards grid, risk indicators, and tabbed narrative panel (aggressive/average/conservative)

## Build Order

Please build in this order:
1. Backend skeleton: FastAPI app, SQLite schema, config
2. Understat scraper: fetch all EPL players + stats + match logs
3. API endpoints: search + player profile
4. Scoring engine: implement the computable dimensions
5. Claude narrative integration
6. Full /report endpoint that assembles everything
7. React frontend with search and dashboard
8. Injury scraper
9. APScheduler for automated scraping
10. Odds scraper (if time permits)

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=your-key-here
FOOTBALL_DATA_API_KEY=your-key-here
ODDS_API_KEY=your-key-here
DATABASE_URL=sqlite:///edgelayer.db
FRONTEND_URL=http://localhost:5173
```

## HTML Prototype Reference

The React frontend should match this HTML prototype EXACTLY in aesthetic and layout. This is the target design — replicate every visual detail. The prototype uses real Haaland data as an example of what a generated report looks like.

Save this as `design-reference.html` in the project root for reference while building:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EdgeLayer — Erling Haaland Intel Report</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0b0e11;
  --surface: #131720;
  --surface-2: #1a1f2e;
  --surface-3: #222838;
  --border: rgba(255,255,255,0.06);
  --text: #e8eaf0;
  --text-dim: #8892a4;
  --text-muted: #4a5568;
  --green: #22c55e;
  --green-bg: rgba(34,197,94,0.08);
  --red: #ef4444;
  --red-bg: rgba(239,68,68,0.08);
  --amber: #f59e0b;
  --amber-bg: rgba(245,158,11,0.08);
  --blue: #3b82f6;
  --blue-bg: rgba(59,130,246,0.08);
  --cyan: #06b6d4;
  --purple: #a855f7;
  --edge-high: #22c55e;
  --edge-mid: #f59e0b;
  --edge-low: #ef4444;
  --mono: 'JetBrains Mono', monospace;
  --sans: 'Outfit', sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--sans); background: var(--bg); color: var(--text); min-height: 100vh; }

.noise {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.03;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.app { max-width: 1280px; margin: 0 auto; padding: 24px; position: relative; z-index: 1; }

/* Header */
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 32px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
.logo { display: flex; align-items: center; gap: 12px; }
.logo-icon { width: 36px; height: 36px; border-radius: 8px; background: linear-gradient(135deg, var(--cyan), var(--blue)); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; color: #fff; }
.logo-text { font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }
.logo-text span { color: var(--cyan); }
.header-meta { text-align: right; }
.header-meta .date { font-family: var(--mono); font-size: 12px; color: var(--text-dim); }
.header-meta .badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; background: var(--green-bg); color: var(--green); margin-top: 4px; border: 1px solid rgba(34,197,94,0.2); }

/* Player Banner */
.player-banner { display: grid; grid-template-columns: 1fr auto; gap: 32px; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px 32px; margin-bottom: 24px; position: relative; overflow: hidden; }
.player-banner::before { content: ''; position: absolute; top: -60px; right: -60px; width: 200px; height: 200px; border-radius: 50%; background: radial-gradient(circle, rgba(6,182,212,0.08), transparent); }
.player-info h1 { font-size: 32px; font-weight: 800; letter-spacing: -1px; margin-bottom: 4px; }
.player-info h1 .num { color: var(--cyan); font-family: var(--mono); }
.player-sub { font-size: 14px; color: var(--text-dim); display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; }
.player-sub span { display: flex; align-items: center; gap: 4px; }
.player-sub .dot { width: 4px; height: 4px; border-radius: 50%; background: var(--text-muted); }

/* Edge Score */
.edge-ring { width: 140px; height: 140px; position: relative; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.edge-ring svg { position: absolute; inset: 0; transform: rotate(-90deg); }
.edge-ring .score-value { font-family: var(--mono); font-size: 40px; font-weight: 700; color: var(--green); }
.edge-ring .score-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; }
.edge-center { text-align: center; }

/* Match Context */
.match-strip { display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; margin-bottom: 24px; text-align: center; }
.match-team { font-size: 18px; font-weight: 700; }
.match-team.away { text-align: right; }
.match-team.home { text-align: left; }
.match-vs { font-family: var(--mono); font-size: 12px; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; gap: 4px; }
.match-vs .time { font-size: 14px; color: var(--amber); font-weight: 600; }

/* Metric Grid */
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
.metric { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; }
.metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-dim); margin-bottom: 8px; font-weight: 500; }
.metric-value { font-family: var(--mono); font-size: 26px; font-weight: 700; }
.metric-sub { font-size: 12px; color: var(--text-dim); margin-top: 4px; }
.metric-value.green { color: var(--green); }
.metric-value.amber { color: var(--amber); }
.metric-value.blue { color: var(--blue); }

/* Sections */
.section { margin-bottom: 24px; }
.section-title { font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-dim); font-weight: 600; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
.section-title .icon { font-size: 14px; }

/* Dimension Cards */
.dim-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.dim-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; }
.dim-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.dim-title { font-size: 14px; font-weight: 600; }
.dim-score { font-family: var(--mono); font-size: 13px; padding: 3px 8px; border-radius: 6px; font-weight: 600; }
.dim-score.high { background: var(--green-bg); color: var(--green); border: 1px solid rgba(34,197,94,0.15); }
.dim-score.mid { background: var(--amber-bg); color: var(--amber); border: 1px solid rgba(245,158,11,0.15); }
.dim-score.low { background: var(--red-bg); color: var(--red); border: 1px solid rgba(239,68,68,0.15); }
.dim-score.info { background: var(--blue-bg); color: var(--blue); border: 1px solid rgba(59,130,246,0.15); }
.dim-body { font-size: 13px; color: var(--text-dim); line-height: 1.6; }
.dim-body strong { color: var(--text); font-weight: 500; }

/* Bar Chart */
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.bar-label { font-size: 12px; color: var(--text-dim); width: 100px; text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; height: 22px; background: var(--surface-3); border-radius: 4px; overflow: hidden; position: relative; }
.bar-fill { height: 100%; border-radius: 4px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; font-family: var(--mono); font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.9); min-width: 32px; transition: width 0.6s ease; }

/* Risk Indicators */
.risk-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.risk-item { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; text-align: center; }
.risk-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-dim); margin-bottom: 6px; }
.risk-value { font-family: var(--mono); font-size: 18px; font-weight: 700; }
.risk-value.green { color: var(--green); }
.risk-value.amber { color: var(--amber); }
.risk-value.red { color: var(--red); }

/* Narrative */
.narrative { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 24px 28px; }
.narrative h3 { font-size: 16px; font-weight: 700; margin-bottom: 14px; }
.narrative p { font-size: 14px; color: var(--text-dim); line-height: 1.75; margin-bottom: 12px; }
.narrative p:last-child { margin-bottom: 0; }
.narrative .highlight { color: var(--cyan); font-weight: 500; }
.narrative .warn { color: var(--amber); font-weight: 500; }
.narrative .pos { color: var(--green); font-weight: 500; }

/* Modes */
.mode-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.mode-tab { padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; background: var(--surface); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; transition: all 0.2s; }
.mode-tab.active { background: var(--cyan); color: #0b0e11; border-color: var(--cyan); font-weight: 600; }
.mode-tab:hover:not(.active) { border-color: rgba(255,255,255,0.15); color: var(--text); }

/* Recent Form */
.form-row { display: flex; gap: 6px; margin-top: 8px; }
.form-dot { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 11px; font-weight: 700; }
.form-dot.goal { background: var(--green-bg); color: var(--green); border: 1px solid rgba(34,197,94,0.2); }
.form-dot.assist { background: var(--blue-bg); color: var(--blue); border: 1px solid rgba(59,130,246,0.2); }
.form-dot.blank { background: var(--surface-3); color: var(--text-muted); border: 1px solid var(--border); }

/* Footer */
.footer { text-align: center; padding: 32px 0 16px; font-size: 11px; color: var(--text-muted); }

@media (max-width: 768px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
  .dim-grid { grid-template-columns: 1fr; }
  .risk-grid { grid-template-columns: 1fr; }
  .player-banner { grid-template-columns: 1fr; }
  .edge-ring { margin: 0 auto; }
}
</style>
</head>
<body>
<div class="noise"></div>
<div class="app">

<!-- Header -->
<div class="header">
  <div class="logo">
    <div class="logo-icon">EL</div>
    <div class="logo-text">Edge<span>Layer</span></div>
  </div>
  <div class="header-meta">
    <div class="date">APR 07, 2026 — PRE-MATCH INTEL</div>
    <div class="badge">LIVE DATA</div>
  </div>
</div>

<!-- Player Banner -->
<div class="player-banner">
  <div class="player-info">
    <h1>Erling Haaland <span class="num">#9</span></h1>
    <div class="player-sub">
      <span>Manchester City</span>
      <span class="dot"></span>
      <span>Striker · Left-footed</span>
      <span class="dot"></span>
      <span>Age 25</span>
      <span class="dot"></span>
      <span>Next: Chelsea (A) — Apr 12</span>
    </div>
  </div>
  <div class="edge-ring">
    <svg viewBox="0 0 140 140">
      <circle cx="70" cy="70" r="62" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="8"/>
      <circle cx="70" cy="70" r="62" fill="none" stroke="#22c55e" stroke-width="8" stroke-dasharray="389.56" stroke-dashoffset="74" stroke-linecap="round"/>
    </svg>
    <div class="edge-center">
      <div class="score-value">81</div>
      <div class="score-label">Edge Score</div>
    </div>
  </div>
</div>

<!-- Match Strip -->
<div class="match-strip">
  <div class="match-team away">Chelsea</div>
  <div class="match-vs">
    <div class="time">16:30 BST</div>
    <div>Stamford Bridge</div>
    <div>Matchday 32</div>
  </div>
  <div class="match-team home">Man City</div>
</div>

<!-- Key Metrics -->
<div class="metrics">
  <div class="metric">
    <div class="metric-label">Season Goals (PL)</div>
    <div class="metric-value green">22</div>
    <div class="metric-sub">in 29 apps · 0.82/90</div>
  </div>
  <div class="metric">
    <div class="metric-label">Shots / 90</div>
    <div class="metric-value blue">3.79</div>
    <div class="metric-sub">102 total · 46% accuracy</div>
  </div>
  <div class="metric">
    <div class="metric-label">xG (Season)</div>
    <div class="metric-value green">21.87</div>
    <div class="metric-sub">npxG/90: 0.70 · 99th %ile</div>
  </div>
  <div class="metric">
    <div class="metric-label">Last 5 Form</div>
    <div class="metric-value amber">4G 1A</div>
    <div class="metric-sub">3W 1D 1L · see below</div>
  </div>
</div>

<!-- The rest of the dashboard includes: -->
<!-- - Recent Match Log table (10 rows with date, opponent, result, mins, G, A, rating) -->
<!-- - Shot Profile bars (left foot, headers, right foot, in-box %, SOT rate) -->
<!-- - 8 Dimension Cards in a 2-col grid, each with title, score badge (high/mid/low), and body text -->
<!-- - Risk Indicators grid (6 items: rotation risk, injury risk, early sub prob, lineup certainty, market adjusted, edge remaining) -->
<!-- - Narrative Panel with 3 tabs (Average, Aggressive, Conservative) -->
<!-- - Output Summary metrics (Edge Score, Confidence, Risk Level, Best Angle, Scenario) -->
<!-- - Footer with disclaimer -->

<!-- SEE THE FULL HTML FILE (design-reference.html) FOR COMPLETE MARKUP -->

</div>
<script>
function showMode(mode) {
  document.querySelectorAll('.narrative').forEach(n => n.style.display = 'none');
  document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('narrative-' + mode).style.display = 'block';
  event.target.classList.add('active');
}
</script>
</body>
</html>
```

Key design elements to replicate in React:
- **Noise texture overlay** on the background (the SVG filter trick)
- **Edge Score ring** — SVG circle with stroke-dashoffset animation, green/amber/red based on score
- **Dimension cards** — 2-column grid, each with a header (title + score badge) and body text
- **Score badges** use `.high` (green), `.mid` (amber), `.low` (red) classes
- **Bar charts** for shot profile — custom CSS bars, not a chart library
- **Mode tabs** for narrative — simple state toggle, active tab gets cyan background
- **Match log table** — inline styles on rows for win/loss/draw coloring
- **Responsive** — stack to 1 column on mobile

The React components should map 1:1 to sections of this HTML. Use Tailwind for utility classes but keep the CSS variables for the color system — define them in your global CSS or tailwind config.

## Important Notes

- Start with Premier League only
- The Understat scraper is the foundation — get this right first
- Cache reports for 2 hours before regenerating
- The narrative Claude call should request JSON output with three keys: aggressive, average, conservative
- Error handling: if a data source is down, use stale data + flag it in the report
- CORS: allow the frontend origin
- I use Claude Code in VS Code on a Mac
```

