# EdgeLayer — Project Context

> Auto-updated as the project is built. If the chat breaks, resume from here.

## What Is This?
EdgeLayer is a data-driven pre-bet intelligence platform for Premier League sports betting.
- User searches a player name
- System pulls data from 4 sources and scores 13 dimensions
- Produces Edge Score (0-100), confidence, risk level, and 3 narrative modes (aggressive / average / conservative)
- Think: Bloomberg Terminal for sports betting

## Collaborators
- **Owner:** Arash Vafanejad
- **Concept originator:** Hesam
- **Goal:** Working prototype accessible via URL for Hesam to review

---

## Tech Stack
| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI |
| DB | SQLite (file: `edgelayer.db`) → migrate to Postgres later |
| Scraping | httpx + BeautifulSoup, APScheduler |
| AI | Anthropic Claude API (`claude-sonnet-4-20250514`) — narratives only |
| Frontend | React (Vite) + Tailwind CSS |
| Deployment | Backend → Render, Frontend → Vercel |

---

## Deployment
- **Backend:** Render (free tier web service, `render.yaml` at root)
- **Frontend:** Vercel (`vercel.json` at root of `frontend/`)
- Env vars must be set in Render dashboard + Vercel dashboard

---

## Data Sources
| Source | What | Frequency | Key |
|---|---|---|---|
| understat.com | Player stats, xG, match logs | Every 6h | None (scrape HTML) |
| premierinjuries.com | Injury table | Every 2h | None (scrape HTML) |
| football-data.org | Fixtures & results | Daily | Free API key |
| the-odds-api.com | Betting lines | Every 30min matchday / 4h otherwise | Free API key |

---

## API Endpoints
```
GET  /api/search?q={query}
GET  /api/player/{player_id}
GET  /api/report/{player_id}
POST /api/report/{player_id}/refresh
GET  /api/fixtures
GET  /api/health
```

---

## Build Progress

- [x] Project structure created
- [x] Context file (this file)
- [x] Design reference HTML (`design-reference.html`)
- [x] Backend skeleton (`main.py`, `config.py`, `db.py`)
- [x] Database schema (all 7 tables)
- [x] Understat scraper (`backend/scrapers/understat.py`)
- [x] Injury scraper (`backend/scrapers/injuries.py`)
- [x] Fixtures scraper (`backend/scrapers/fixtures.py`)
- [x] Odds scraper (`backend/scrapers/odds.py`)
- [x] Scoring engine — dimensions (`backend/engine/dimensions.py`)
- [x] Scoring engine — scorer (`backend/engine/scorer.py`)
- [x] Claude narrative integration (`backend/engine/narrative.py`)
- [x] All API endpoints in `main.py`
- [x] APScheduler (`backend/scheduler.py`)
- [x] React frontend (all components)
- [x] Deployment config (`render.yaml`, `frontend/vercel.json`)
- [x] `requirements.txt`, `.env.example`, `README.md`

---

## Key File Locations
```
EdgeLayer/
├── CONTEXT.md                  ← you are here
├── design-reference.html       ← HTML prototype (design target)
├── render.yaml                 ← Render deploy config
├── .env.example
├── README.md
├── backend/
│   ├── main.py                 ← FastAPI app + all routes
│   ├── config.py               ← env vars, constants
│   ├── db.py                   ← SQLite setup + query helpers
│   ├── scheduler.py            ← APScheduler jobs
│   ├── scrapers/
│   │   ├── understat.py        ← Player stats, xG, match logs
│   │   ├── injuries.py         ← premierinjuries.com
│   │   ├── fixtures.py         ← football-data.org
│   │   └── odds.py             ← the-odds-api.com
│   ├── engine/
│   │   ├── dimensions.py       ← 13 dimension calculators
│   │   ├── scorer.py           ← Edge Score aggregation
│   │   └── narrative.py        ← Claude API narrative generation
│   └── requirements.txt
└── frontend/
    ├── vercel.json
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        ├── api.js
        ├── index.css
        ├── main.jsx
        └── components/
            ├── PlayerSearch.jsx
            ├── Dashboard.jsx
            ├── EdgeScore.jsx
            ├── MatchStrip.jsx
            ├── MetricsGrid.jsx
            ├── MatchLog.jsx
            ├── ShotProfile.jsx
            ├── DimensionCard.jsx
            ├── RiskIndicators.jsx
            └── NarrativePanel.jsx
```

---

## 13 Dimensions & Weights
| # | Dimension | Weight | MVP Status |
|---|---|---|---|
| 1 | Player Performance & Form | 15% | Full |
| 2 | Team Context & Support | 10% | Full |
| 3 | Opponent Analysis | 12% | Full |
| 4 | Schedule & Fatigue | 8% | Full |
| 5 | Injuries & Lineup | 10% | Full |
| 6 | Manager & Tactical Signals | 5% | Stub |
| 7 | Market Intelligence | 10% | Full |
| 8 | Role & Usage Changes | 5% | Stub |
| 9 | Psychological & Narrative | 5% | Stub |
| 10 | External Conditions | 3% | Stub |
| 11 | Change Detection | 7% | Full |
| 12 | Risk Indicators | 5% | Full |
| 13 | Output Metrics | 5% | Full |

---

## Edge Score Formula
```python
edge_score = sum(dim_score * weight for each dimension)
confidence = "HIGH" if score >= 75 else "MEDIUM" if score >= 55 else "LOW"
risk = "LOW" | "MEDIUM" | "HIGH"  # based on risk flag count
```

---

## Environment Variables
```
ANTHROPIC_API_KEY=
FOOTBALL_DATA_API_KEY=
ODDS_API_KEY=
DATABASE_URL=sqlite:///edgelayer.db
FRONTEND_URL=http://localhost:5173
```

---

## Notes
- Premier League only for MVP
- Reports cached for 2 hours (`reports_cache` table)
- Claude called only for narrative generation (~$0.02-0.05/report)
- If a data source is down, use stale data + flag in report
- CORS configured to allow frontend origin
