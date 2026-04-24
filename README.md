# EdgeLayer

Pre-bet intelligence platform for Premier League. Enter a player name, get a 13-dimension Edge Score, risk assessment, and AI-generated betting narratives.

## Quick Start (Local)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

Start the API server:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

The server starts and immediately runs all scrapers in the background. Wait ~60 seconds for the Understat scrape to populate the player database.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## API Keys Needed

| Service | Free? | Where to get |
|---|---|---|
| Anthropic | No (pay-per-use, ~$0.02/report) | console.anthropic.com |
| football-data.org | Yes (free tier) | football-data.org/client/register |
| The Odds API | Yes (500 req/month free) | the-odds-api.com |

The app works without API keys — you just won't get narrative generation (placeholders instead) or betting odds.

---

## Architecture

```
Browser → React (Vite) → FastAPI (Python)
                              ↓
                    ┌─────────────────┐
                    │  SQLite DB      │
                    │  (edgelayer.db) │
                    └─────────────────┘
                              ↑
              ┌───────────────┼───────────────┐
         Understat        Injuries        football-data
         (6h scrape)      (2h scrape)     (daily scrape)
```

---

## Deploy to Render + Vercel

### Backend → Render

1. Push this repo to GitHub
2. Go to render.com → New → Web Service
3. Connect your GitHub repo
4. Set root directory: `backend`
5. Build command: `pip install -r requirements.txt`
6. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Add a **Disk** (1GB, mount at `/opt/render/project/src`) for SQLite persistence
8. Set environment variables in Render dashboard:
   - `ANTHROPIC_API_KEY`
   - `FOOTBALL_DATA_API_KEY`
   - `ODDS_API_KEY`
   - `FRONTEND_URL` = your Vercel URL (add after deploying frontend)

**OR** use the included `render.yaml` — connect the repo in Render and it auto-configures.

### Frontend → Vercel

1. Go to vercel.com → New Project → Import your GitHub repo
2. Set root directory: `frontend`
3. Set environment variable: `VITE_API_URL` = your Render backend URL (e.g. `https://edgelayer-backend.onrender.com`)
4. Deploy

Update `FRONTEND_URL` in Render to your Vercel URL after deployment.

---

## API Endpoints

```
GET  /api/search?q={query}           Search players by name
GET  /api/player/{id}                Player profile + stats
GET  /api/report/{id}                Full report (cached 2h)
GET  /api/report/{id}?refresh=true   Force fresh report
POST /api/report/{id}/refresh        Queue background refresh
GET  /api/fixtures                   Upcoming PL fixtures
GET  /api/health                     System health + scrape status
POST /api/admin/scrape/{source}      Manual scrape trigger
```

---

## Seeding Data

After first deploy, trigger an initial scrape:

```bash
curl -X POST https://your-render-url.onrender.com/api/admin/scrape/understat
curl -X POST https://your-render-url.onrender.com/api/admin/scrape/fixtures
curl -X POST https://your-render-url.onrender.com/api/admin/scrape/injuries
```

Or just wait — the scheduler runs all three automatically on startup.

---

## 13 Dimensions

| # | Dimension | Weight | Status |
|---|---|---|---|
| 1 | Player Performance & Form | 15% | Live |
| 2 | Team Context & Support | 10% | Live |
| 3 | Opponent Analysis | 12% | Live |
| 4 | Schedule & Fatigue | 8% | Live |
| 5 | Injuries & Lineup | 10% | Live |
| 6 | Manager & Tactical Signals | 5% | Stub |
| 7 | Market Intelligence | 10% | Live |
| 8 | Role & Usage Changes | 5% | Stub |
| 9 | Psychological & Narrative | 5% | Partial |
| 10 | External Conditions | 3% | Stub |
| 11 | Change Detection | 7% | Live |
| 12 | Risk Indicators | 5% | Live |
| 13 | Output Metrics | 5% | Live |
