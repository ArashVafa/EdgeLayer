# EdgeLayer — Project Context

> Updated: April 2026. If the chat breaks, resume from this file.

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
| understat.com | Player stats, xG, assists, shots | Every 6h | ✅ Live (POST API) |
| premierinjuries.com | Injury table | Every 2h | ❌ Blocked on Render IPs |
| football-data.org | Fixtures & results | Daily | ✅ Live (needs free API key) |
| the-odds-api.com | Betting lines | 30min matchday / 4h otherwise | ⚙️ Ready (needs API key) |

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
POST /api/admin/scrape/{source}            Manual scrape trigger (understat/injuries/fixtures/odds)
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

Tables: `players`, `player_stats`, `match_logs`, `injuries`, `fixtures`, `odds`, `reports_cache`, `scrape_log`, `llm_log`, `llm_feedback`, `users`, `password_reset_tokens`

### New tables added (April 2026)
```sql
llm_log       — every LLM call: provider, model, use_case, player_id, user_message,
                response, input_tokens, output_tokens, latency_ms
llm_feedback  — thumbs up/down ratings on LLM outputs (for future fine-tuning)
users         — auth table (email, hashed_password) — built but currently disabled
password_reset_tokens — time-limited reset tokens for forgot-password flow
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
├── backend/
│   ├── main.py                     ← FastAPI app, all routes, lifespan (auto-seed)
│   ├── config.py                   ← all env vars + constants
│   ├── db.py                       ← SQLite schema + all CRUD helpers
│   ├── auth.py                     ← JWT auth router (built, currently disabled)
│   ├── scheduler.py                ← APScheduler jobs (all 4 scrapers)
│   ├── seed.py                     ← 31 hardcoded players + GW36-38 fixtures fallback
│   ├── .python-version             ← 3.11.9 (prevents Render using Python 3.14)
│   ├── requirements.txt
│   ├── scrapers/
│   │   ├── understat.py            ← POST API, 3x retry+backoff, sync+async variants
│   │   ├── injuries.py             ← premierinjuries.com (full browser HEADERS)
│   │   ├── fixtures.py             ← football-data.org free API
│   │   └── odds.py                 ← the-odds-api.com
│   └── engine/
│       ├── llm.py                  ← unified LLM wrapper (Groq + Anthropic)
│       ├── dimensions.py           ← 13 dimension scoring functions
│       ├── scorer.py               ← Edge Score aggregation + report builder
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
            ├── Dashboard.jsx        ← full report page, includes ChatPanel
            ├── ChatPanel.jsx        ← player chatbot UI
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
