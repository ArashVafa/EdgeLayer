import os
from dotenv import load_dotenv

load_dotenv()

# API keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")

# Auth
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-please-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@edgelayer.app")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///edgelayer.db")
DB_PATH = DATABASE_URL.replace("sqlite:///", "")

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Scrape intervals (seconds)
UNDERSTAT_INTERVAL = 6 * 3600       # 6 hours
INJURIES_INTERVAL = 2 * 3600        # 2 hours
FIXTURES_INTERVAL = 24 * 3600       # daily
ODDS_INTERVAL_MATCHDAY = 30 * 60    # 30 min on matchday
ODDS_INTERVAL_DEFAULT = 4 * 3600    # 4 hours otherwise

# Report cache TTL (seconds)
REPORT_CACHE_TTL = 2 * 3600         # 2 hours

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# football-data.org
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

# The Odds API
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Understat
UNDERSTAT_BASE = "https://understat.com"

# Premier Injuries
PREMIER_INJURIES_URL = "https://www.premierinjuries.com/injury-table.php"
