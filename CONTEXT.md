# EdgeLayer — Project Context

> Updated: June 2026. If the chat breaks, resume from this file.

---

## What Is This?
EdgeLayer is a data-driven pre-bet intelligence platform for Premier League football.
- User searches any Premier League player
- System pulls live data from 4 sources, scores 13 analytical dimensions
- Produces an Edge Score (0–100), confidence level, risk level, and 3 narrative modes (aggressive / average / conservative) via LLM
- Also has a player-specific AI chatbot for free-form questions
- Think: Bloomberg Terminal for sports betting

## Collaborators
- **Owner:** Arash Vafanejad
- **Concept originator:** Hesam
- **GitHub:** github.com/ArashVafa/EdgeLayer

---

## Live URLs
| Service | URL |
|---|---|
| Backend (Render) | https://edgelayer-h1qd.onrender.com |
| Frontend (Vercel) | https://edgelayer.vercel.app |
| Health check | https://edgelayer-h1qd.onrender.com/api/health |

---

## Tech Stack
| Layer | Tech |
|---|---|
| Backend | Python 3.11.9, FastAPI, uvicorn |
| DB | SQLite with WAL mode (`/data/edgelayer.db` on Render persistent disk) |
| Scraping | httpx (sync + async), BeautifulSoup, APScheduler |
| LLM | Groq API (free, default) → Anthropic (fallback). Unified wrapper in `engine/llm.py` |
| Frontend | React 18, Vite, Tailwind CSS, Axios |
| Deployment | Backend → Render (root dir: `backend/`), Frontend → Vercel |

---

## Deployment Details

### Render
- Root directory: `backend/`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Persistent disk: mounted at `/data`, 1GB
- Python version: locked to 3.11.9 via `backend/.python-version`

### Vercel
- Root: `frontend/`
- Build: `npm run build`
- `VITE_API_URL` set in `frontend/vercel.json` under `build.env` (NOT `env`) so Vite bakes it in at build time

### Environment Variables (Render)
```
DATABASE_URL=sqlite:////data/edgelayer.db   # 4 slashes = absolute path
ANTHROPIC_API_KEY=...                        # optional if GROQ_API_KEY set
GROQ_API_KEY=...                             # free at console.groq.com — primary LLM
LLM_PROVIDER=groq                            # auto-detected; override if needed
SECRET_KEY=...                               # for auth (generate: python3 -c "import secrets; print(secrets.token_hex(32))")
FOOTBALL_DATA_API_KEY=...                    # free at football-data.org — for live fixtures
ODDS_API_KEY=...                             # optional, the-odds-api.com
FRONTEND_URL=https://edgelayer.vercel.app
RESEND_API_KEY=...                           # optional, for forgot-password emails
```

---

## Data Sources & What's Actually Live

| Source | Data | Frequency | Status |
|---|---|---|---|
| understat.com | Player stats, xG, assists, shots, key_passes | Every 6h | ✅ Live (POST API) |
| FPL bootstrap-static API | Ownership, price, ICT, starts, transfers, clean sheets, saves, bonus, element_type, team FDR | Every 6h | ✅ Live |
| premierinjuries.com | Injury table | Every 2h | ❌ Blocked on Render IPs |
| football-data.org | Fixtures & results | Daily | ✅ Live (needs free API key) |
| the-odds-api.com | Betting lines | 30min matchday / 4h otherwise | ⚙️ Ready (needs API key) |

### FPL Bootstrap data available per player
`fpl_stats` table: ownership_pct, price, form, points_per_game, total_points, ict_index, influence, creativity, threat, expected_goals (xG), expected_assists (xA), expected_goal_involvements (xGI), minutes, starts, clean_sheets, goals_conceded, yellow_cards, red_cards, saves, bonus, element_type (1=GK/2=DEF/3=MID/4=FWD), transfers_in_event, transfers_out_event, chance_of_playing_next_round

`team_fdr` table: strength_overall_home/away, strength_attack_home/away, strength_defence_home/away — all 20 PL teams

### Important: What is real vs synthetic
- **Player season stats** (xG, goals, assists, shots, minutes): **REAL** — scraped from Understat POST API every 6h. Currently 589 players.
- **Match logs** (per-game breakdown): **SYNTHETIC** — generated from season totals using weighted random distribution. Understat's per-match API is no longer public.
- **Fixtures**: Real from football-data.org if `FOOTBALL_DATA_API_KEY` set; otherwise falls back to seed data (GW36–38 May 2026 dates).
- **Injuries**: Seed data (10 hardcoded). premierinjuries.com blocks Render server IPs.

### Understat Implementation Note
Understat migrated to client-side rendering. The scraper uses a **POST API endpoint**:
```
POST https://understat.com/main/getPlayersStats/
Body: league=EPL&season=2024
```
Returns JSON with all 562+ EPL players' season stats. No HTML parsing needed.

---

## Key API Endpoints

```
GET  /api/search?q={query}                  Player search
GET  /api/player/{player_id}               Full profile + stats + injury
GET  /api/report/{player_id}               Full EdgeLayer report (cached 2h)
GET  /api/report/{player_id}?refresh=true  Bust cache and regenerate
POST /api/report/{player_id}/refresh       Background regeneration
GET  /api/fixtures?team={team}             Upcoming fixtures
GET  /api/health                           DB counts + last scrape timestamps
POST /api/chat/{player_id}                 Player chatbot (body: {message, history[]})
POST /api/admin/scrape/{source}            Manual scrape trigger (understat/injuries/fixtures/odds/fpl_history/fpl_bootstrap)
POST /api/admin/reseed-fixtures            Replace fixtures with seed data (fallback)
```

---

## LLM Architecture

### Unified wrapper: `backend/engine/llm.py`
Single `chat_complete()` function used by both narratives and chatbot:
- Auto-selects provider: Groq if `GROQ_API_KEY` set, else Anthropic, else error
- Override via `LLM_PROVIDER` env var (`"groq"` or `"anthropic"`)
- Logs every call to `llm_log` table (provider, model, tokens, latency, player_id, input, output)

### Models
- Groq: `llama-3.3-70b-versatile` (free, 14k req/day limit)
- Anthropic: `claude-sonnet-4-6` (paid, ~$0.005/narrative)
- Override Groq model via `GROQ_MODEL` env var

### Narrative generation: `backend/engine/narrative.py`
- Sends structured report data (stats, form, fixture, dimensions) to LLM
- Expects JSON response: `{"aggressive": "...", "average": "...", "conservative": "..."}`
- Robust JSON extraction via regex fallback (handles markdown fences from Llama)
- Reports cached 2h in `reports_cache` table — LLM called once per player per 2h

### Chatbot: `backend/engine/chatbot.py`
- Stateless — frontend sends full conversation history each request
- System prompt built dynamically from live DB data (stats, form, injuries, fixture)
- Users can inject context in natural language ("Salah is leaving at end of season...")
- Every call logged to `llm_log` for training data collection

---

## Database Schema

Tables: `players`, `player_stats`, `match_logs`, `injuries`, `fixtures`, `odds`, `reports_cache`, `scrape_log`, `llm_log`, `llm_feedback`, `users`, `password_reset_tokens`, `fpl_stats`, `team_fdr`

### New tables added (April 2026)
```sql
llm_log       — every LLM call: provider, model, use_case, player_id, user_message,
                response, input_tokens, output_tokens, latency_ms
llm_feedback  — thumbs up/down ratings on LLM outputs (for future fine-tuning)
users         — auth table (email, hashed_password) — built but currently disabled
password_reset_tokens — time-limited reset tokens for forgot-password flow
```

### New tables added (June 2026)
```sql
fpl_stats     — per-player FPL data: ownership_pct, price, form, points_per_game,
                total_points, ict_index, influence, creativity, threat,
                expected_goals, expected_assists, expected_goal_involvements,
                minutes, starts, clean_sheets, goals_conceded, yellow_cards,
                red_cards, saves, bonus, element_type (1=GK/2=DEF/3=MID/4=FWD),
                transfers_in_event, transfers_out_event, chance_of_playing_next_round,
                value_form, value_season, ep_next (FPL's own next-GW xPts),
                news (FPL injury/availability text — replaces blocked premierinjuries.com),
                news_added (timestamp of news)
team_fdr      — FPL team strength ratings: strength_overall/attack/defence home/away
                for all 20 PL teams — used for Fixture Adjusted Form calculation
fpl_events    — per-GW event data: most_captained_fpl_id/name, most_transferred_in,
                top_element, average_entry_score, chip_plays_json
                Used for EO estimation (captaincy proxy)
```

### Training data strategy
`llm_log` accumulates automatically. Each row = one training example:
- Input: player context + user question
- Output: LLM response
- Metadata: provider, model, latency, tokens, player_id, use_case

When enough rows accumulate, plan:
1. Export rated rows (llm_feedback.rating > 0)
2. Fine-tune Llama 3.1 8B on domain-specific narrative style
3. Self-host on a cheap GPU instance or use Together AI fine-tuning

---

## File Structure

```
EdgeLayer/
├── CONTEXT.md                      ← this file
├── render.yaml                     ← Render deploy config
├── design-reference.html           ← HTML prototype (original design target)
├── feebacks/                       ← feedback docs (All Indexes .docx, Rules and Points.docx)
├── backend/
│   ├── main.py                     ← FastAPI app, all routes, lifespan (auto-seed)
│   ├── config.py                   ← all env vars + constants
│   ├── db.py                       ← SQLite schema + all CRUD helpers (incl. fpl_stats, team_fdr)
│   ├── auth.py                     ← JWT auth router (built, currently disabled)
│   ├── scheduler.py                ← APScheduler jobs (5 scrapers incl. fpl_bootstrap every 6h)
│   ├── seed.py                     ← 31 hardcoded players + GW36-38 fixtures fallback
│   ├── .python-version             ← 3.11.9 (prevents Render using Python 3.14)
│   ├── requirements.txt
│   ├── scrapers/
│   │   ├── understat.py            ← POST API, 3x retry+backoff, sync+async variants
│   │   ├── fpl_bootstrap.py        ← FPL bootstrap-static API → fpl_stats + team_fdr tables
│   │   ├── fpl_history.py          ← FPL per-player history (GW-level)
│   │   ├── injuries.py             ← premierinjuries.com (full browser HEADERS)
│   │   ├── fixtures.py             ← football-data.org free API
│   │   └── odds.py                 ← the-odds-api.com
│   └── engine/
│       ├── llm.py                  ← unified LLM wrapper (Groq + Anthropic)
│       ├── dimensions.py           ← 13 dimension scoring functions (use fpl_stats for risk/market/form)
│       ├── scorer.py               ← Edge Score aggregation + report builder + _build_fpl_analytics()
│       ├── fpl_points.py           ← xFPL calc, captaincy/differential/rotation/form_index/fixture_adj_form
│       ├── narrative.py            ← 3-mode narrative generation via LLM
│       └── chatbot.py              ← player Q&A chatbot via LLM
└── frontend/
    ├── vercel.json                  ← VITE_API_URL under build.env (not env!)
    ├── package.json
    └── src/
        ├── App.jsx                  ← top-level routing (auth disabled, direct app)
        ├── api.js                   ← axios client, all API + auth calls
        ├── index.css                ← CSS variables, dark theme
        ├── context/
        │   └── AuthContext.jsx      ← auth state (built, not active)
        ├── pages/
        │   ├── LoginPage.jsx        ← (built, not active)
        │   ├── RegisterPage.jsx     ← (built, not active)
        │   ├── ForgotPasswordPage.jsx
        │   └── ResetPasswordPage.jsx
        └── components/
            ├── PlayerSearch.jsx
            ├── Dashboard.jsx        ← full report page; scrolls to top on player change
            ├── ChatPanel.jsx        ← player chatbot UI; only auto-scrolls when messages exist
            ├── FplPanel.jsx         ← FPL Intelligence section (6 sub-sections, see below)
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
| # | Dimension | Weight | Status |
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

## Auth System (Built, Currently Disabled)
Full JWT auth was built and then disabled to simplify sharing:
- `backend/auth.py` — register, login, refresh, forgot-password, reset-password endpoints
- `frontend/src/context/AuthContext.jsx` — React context with localStorage JWT management
- `frontend/src/pages/` — Login, Register, ForgotPassword, ResetPassword pages
- DB tables: `users`, `password_reset_tokens`
- Dependencies: `PyJWT`, `passlib[bcrypt]`, `python-multipart`, `resend`

**To re-enable:** In `main.py`, uncomment `from auth import router as auth_router` and `app.include_router(auth_router)`. In `App.jsx`, re-wrap with `<AuthProvider>` and add the auth gate.

---

## FPL Intelligence Panel (FplPanel.jsx)

Sits between MatchStrip and MetricsGrid on the Dashboard. Six sections:
1. **Headline indexes** — xFPL/game, Captaincy Score (/100), Differential Score (/100) with progress bars
2. **Form indexes** — Form Index (/100), Fixture Adjusted Form (/100) with delta vs raw
3. **Availability & Rotation** — Ownership %, Price, Starts/sub apps, Predicted Minutes, Rotation Risk (LOW/MED/HIGH)
4. **Rolling form windows** — xG Last 3/5/10, xA Last 3/5, xGI Last 5 with mini bar charts
5. **ICT Index** — Overall ICT, Influence, Creativity, Threat bars
6. **Season stats + GW transfers + Scoring rules** — Total pts, Pts/game, FPL form, Season xGI; Transfers In/Out/Net; Goal/Assist/CS/Card rule chips

### FPL scoring rules implemented in `engine/fpl_points.py`
- Goal pts by position: GK=10, DEF=6, MID=5, FWD=4
- Assist: 3pts all positions
- Clean sheet: GK/DEF=4, MID=1, FWD=0
- Play <60min: 1pt, 60+: 2pts
- Every 3 saves (GK): 1pt
- Every 2 goals conceded (GK/DEF): −1pt
- Yellow: −1, Red: −3
- Bonus: stored from FPL bootstrap, divided per-game
- **Not implemented** (no data): Penalty miss −2, Own goal −2, CBIT defensive contributions +2

### FPL analytics computed fresh every response (not cached)
`_build_fpl_analytics()` in `scorer.py` runs on both live and cached reports because
ownership/price/transfers change each gameweek — only the edge score & narratives are cached.

---

## Feedback Implementation Status (`feebacks/` directory)

Two feedback files were reviewed (June 2026): "All Indexes .docx" and "Rules and Points.docx".

### ✅ Implemented
- xFPL per game (custom expected fantasy points model)
- Form Index 0-100 (xG/90 35% + xA/90 25% + SOT/90 20% + KeyPass/90 15% + availability 5%)
- Fixture Adjusted Form (form × opponent defence FDR modifier ±25%)
- Captaincy Score 0-100 (2× xFPL scaled to 20pt ceiling)
- Differential Score 0-100 (low ownership × high xFPL × form)
- Rotation Risk label (LOW/MEDIUM/HIGH from starts/avg-mins)
- xG rolling windows: Last 3, Last 5, Last 10
- xA rolling windows: Last 3, Last 5 (using assists as proxy)
- xGI Last 5 (goals + assists), Season xGI
- Sub appearances, Predicted minutes
- Ownership %, Transfers In/Out/Net this GW
- ICT Index, Influence, Creativity, Threat
- Full FPL scoring rules in xFPL calc (goal pts by position, CS, saves, conceded, cards, bonus)
- FDR table (all 20 teams, attack/defence strength home/away)
- Suspension risk flag (one yellow from suspension)
- Injury status / doubt flag (chance_of_playing_next_round)
- Scoring rule chips displayed in UI

### ✅ Implemented (June 2026 — Phase 2)
- Gameweek Planner as default landing tab — sortable table of all players for upcoming GW
  - Columns: name, team, pos, price, own%, EO (est.), xFPL, form, fixture-adj form, next opponent, rotation risk, proj pts
  - Filters: position, max price, min/max ownership (for differential hunting)
  - Row click → Player Report; Compare button → Transfer Planner
- Effective Ownership (estimated) — ownership + captaincy proxy from fpl_events.most_captained
  - Shown in Gameweek Planner, Transfer Planner, and FPL Panel
  - Labelled "estimated" everywhere; tooltip explains captaincy is not from official API
- Transfer Planner verdict: eo_note flags template assets (EO>40%) and differentials (<12% own)
- FPL news / chance_of_playing from bootstrap (replaces blocked premierinjuries.com scraper)
  - Shown as coloured banner in FPL Panel on Player Report
- ep_next (FPL's own expected pts), value_form, value_season stored in fpl_stats
- fpl_events table: most_captained, most_transferred_in, top_element, avg score per GW
- GET /api/gameweek-planner endpoint (bulk DB load, no per-player queries)

### ❌ Not yet implemented (needs new data sources)
- xG/90, xA/90, xGI/90 displayed as standalone stats
- NPxG (non-penalty xG)
- Shots Inside/Outside Box, Big Chances, BCM, Shot Conversion
- Big Chances Created, Through Balls, Crosses, Progressive Passes
- CBIT (Clearances/Blocks/Interceptions/Tackles) — needed for defensive contribution +2pts scoring
- GK: Save %, Penalty Saves, Goals Prevented, xGOT
- Team-level: xGA, Team xG, Team CS %, Shots Conceded
- Home vs Away splits
- Effective Ownership (EO = ownership + captaincy % + TC%)
- Top 10k ownership
- Price history / Price rise/fall %
- Own goal and penalty miss deductions in xFPL (no data)

---

## Planned Next Features

### 1. Probability Engine
- Goal probability: Poisson distribution using per-90 xG as lambda
  - P(0 goals) = e^(-λ), P(1) = λe^(-λ), P(2+) = 1 - P(0) - P(1)
- Shots on/off target, fouls, tackles, clearances: needs richer per-match data
  - Requires football-data.org deeper integration or FBref scraping
- Cold start: positional league-average priors (propensity scores)
- Training: save predictions + actual outcomes → calibrate with logistic regression

### 2. Auth Re-enable + User Features
- All code is already built (see Auth section above)
- Per-user watchlists / saved player reports
- Personal notification preferences

### 3. Model Fine-tuning
- Export `llm_log` rows where `llm_feedback.rating > 0`
- Fine-tune Llama 3.1 8B on domain narrative style
- Host via Together AI fine-tuning or self-hosted

---

## UI Behaviour Notes
- **Page scroll**: Dashboard scrolls to top when a new player is selected (`window.scrollTo(0,0)` in `Dashboard.jsx` useEffect)
- **Chat scroll**: ChatPanel only auto-scrolls to bottom when there are messages — does NOT scroll on initial render (fixed June 2026)

## Known Issues / Gotchas
- **Match logs are synthetic** — per-game data doesn't exist from Understat anymore
- **Injuries blocked** — premierinjuries.com blocks Render server IPs; seed data used
- **Fixtures need API key** — without `FOOTBALL_DATA_API_KEY`, seed fixture dates are used
- **Groq rate limit** — 14,400 requests/day free; sufficient for normal usage
- **Report cache** — reports cached 2h; click "Refresh Report" to regenerate with fresh data
- **Understat rate limit** — first scrape delayed 30min after startup to prevent hammering
- **python-jose incompatibility** — switched to PyJWT (python-jose conflicts with newer cryptography package)
- **VITE_API_URL must be in `build.env`** not `env` in vercel.json — Vite bakes env vars at build time
- **Render disk path** — `/opt/render/project/src` is reserved; use `/data`
