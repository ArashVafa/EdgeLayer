import sqlite3
import json
from contextlib import contextmanager
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_conn():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            team TEXT,
            position TEXT,
            understat_id INTEGER UNIQUE,
            fotmob_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS player_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER REFERENCES players(id),
            season TEXT,
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

        CREATE TABLE IF NOT EXISTS match_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER REFERENCES players(id),
            date TEXT,
            opponent TEXT,
            home_away TEXT,
            competition TEXT,
            result TEXT,
            minutes INTEGER,
            goals INTEGER,
            assists INTEGER,
            shots INTEGER,
            xG REAL,
            rating REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS injuries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT,
            player_name TEXT,
            injury_type TEXT,
            status TEXT,
            expected_return TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fixtures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team TEXT,
            away_team TEXT,
            date TEXT,
            competition TEXT,
            status TEXT,
            score TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS odds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER REFERENCES fixtures(id),
            market TEXT,
            outcome TEXT,
            odds REAL,
            bookmaker TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reports_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER REFERENCES players(id),
            fixture_id INTEGER,
            edge_score INTEGER,
            confidence TEXT,
            risk_level TEXT,
            dimensions_json TEXT,
            narrative_avg TEXT,
            narrative_agg TEXT,
            narrative_con TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            ran_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS llm_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            use_case TEXT NOT NULL,
            player_id INTEGER,
            user_message TEXT,
            response TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            latency_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS llm_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER REFERENCES llm_log(id),
            rating INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);
        CREATE INDEX IF NOT EXISTS idx_players_fpl ON players(fpl_id);
        CREATE INDEX IF NOT EXISTS idx_match_logs_player ON match_logs(player_id, date);
        CREATE INDEX IF NOT EXISTS idx_reports_cache_player ON reports_cache(player_id, created_at);
        """)

    # Safe migration: add fpl_id if not present on older DBs
    with db_conn() as conn:
        try:
            conn.execute("ALTER TABLE players ADD COLUMN fpl_id INTEGER")
        except Exception:
            pass  # column already exists


# ── Players ──────────────────────────────────────────────────────────────────

def search_players(query: str, limit: int = 10):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, team, position FROM players WHERE name LIKE ? ORDER BY name LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
    return [dict(r) for r in rows]


def get_player(player_id: int):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        ).fetchone()
    return dict(row) if row else None


def get_all_players_for_fpl_match():
    """Return all players for FPL name-matching (id, name)."""
    with db_conn() as conn:
        rows = conn.execute("SELECT id, name FROM players").fetchall()
    return [dict(r) for r in rows]


def update_player_fpl_id(player_id: int, fpl_id: int):
    with db_conn() as conn:
        conn.execute(
            "UPDATE players SET fpl_id=? WHERE id=?", (fpl_id, player_id)
        )


def get_players_with_fpl_id():
    """Return players that have a known FPL ID (for match history scraping)."""
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, team, fpl_id FROM players WHERE fpl_id IS NOT NULL"
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_player(name: str, team: str, position: str, understat_id: int) -> int:
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO players (name, team, position, understat_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(understat_id) DO UPDATE SET
                name=excluded.name,
                team=excluded.team,
                position=excluded.position
        """, (name, team, position, understat_id))
        row = conn.execute(
            "SELECT id FROM players WHERE understat_id = ?", (understat_id,)
        ).fetchone()
    return row["id"]


# ── Player Stats ──────────────────────────────────────────────────────────────

def upsert_player_stats(player_id: int, season: str, stats: dict):
    with db_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM player_stats WHERE player_id = ? AND season = ?",
            (player_id, season)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE player_stats SET
                    goals=?, assists=?, xG=?, xA=?, shots=?, shots_on_target=?,
                    key_passes=?, minutes=?, appearances=?, npxG=?,
                    yellow_cards=?, red_cards=?, updated_at=CURRENT_TIMESTAMP
                WHERE player_id=? AND season=?
            """, (
                stats.get("goals", 0), stats.get("assists", 0),
                stats.get("xG", 0), stats.get("xA", 0),
                stats.get("shots", 0), stats.get("shots_on_target", 0),
                stats.get("key_passes", 0), stats.get("minutes", 0),
                stats.get("appearances", 0), stats.get("npxG", 0),
                stats.get("yellow_cards", 0), stats.get("red_cards", 0),
                player_id, season
            ))
        else:
            conn.execute("""
                INSERT INTO player_stats
                    (player_id, season, goals, assists, xG, xA, shots, shots_on_target,
                     key_passes, minutes, appearances, npxG, yellow_cards, red_cards)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                player_id, season,
                stats.get("goals", 0), stats.get("assists", 0),
                stats.get("xG", 0), stats.get("xA", 0),
                stats.get("shots", 0), stats.get("shots_on_target", 0),
                stats.get("key_passes", 0), stats.get("minutes", 0),
                stats.get("appearances", 0), stats.get("npxG", 0),
                stats.get("yellow_cards", 0), stats.get("red_cards", 0),
            ))


def get_player_stats(player_id: int, season: str = None):
    with db_conn() as conn:
        if season:
            row = conn.execute(
                "SELECT * FROM player_stats WHERE player_id=? AND season=?",
                (player_id, season)
            ).fetchone()
            return dict(row) if row else None
        rows = conn.execute(
            "SELECT * FROM player_stats WHERE player_id=? ORDER BY season DESC",
            (player_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Match Logs ────────────────────────────────────────────────────────────────

def upsert_match_log(player_id: int, log: dict):
    with db_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM match_logs WHERE player_id=? AND date=? AND opponent=?",
            (player_id, log["date"], log["opponent"])
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE match_logs SET
                    home_away=?, competition=?, result=?, minutes=?,
                    goals=?, assists=?, shots=?, xG=?, rating=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                log.get("home_away"), log.get("competition"), log.get("result"),
                log.get("minutes", 0), log.get("goals", 0), log.get("assists", 0),
                log.get("shots", 0), log.get("xG", 0), log.get("rating"),
                existing["id"]
            ))
        else:
            conn.execute("""
                INSERT INTO match_logs
                    (player_id, date, opponent, home_away, competition, result,
                     minutes, goals, assists, shots, xG, rating)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                player_id, log["date"], log["opponent"],
                log.get("home_away"), log.get("competition"), log.get("result"),
                log.get("minutes", 0), log.get("goals", 0), log.get("assists", 0),
                log.get("shots", 0), log.get("xG", 0), log.get("rating")
            ))


def get_match_logs(player_id: int, limit: int = 20):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM match_logs WHERE player_id=? ORDER BY date DESC LIMIT ?",
            (player_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Injuries ──────────────────────────────────────────────────────────────────

def replace_injuries(injury_list: list):
    with db_conn() as conn:
        conn.execute("DELETE FROM injuries")
        conn.executemany("""
            INSERT INTO injuries (team, player_name, injury_type, status, expected_return)
            VALUES (?,?,?,?,?)
        """, [
            (i["team"], i["player_name"], i["injury_type"], i["status"], i["expected_return"])
            for i in injury_list
        ])


def get_injuries(team: str = None):
    with db_conn() as conn:
        if team:
            rows = conn.execute(
                "SELECT * FROM injuries WHERE team=?", (team,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM injuries").fetchall()
    return [dict(r) for r in rows]


# ── Fixtures ──────────────────────────────────────────────────────────────────

def upsert_fixture(home_team: str, away_team: str, date: str,
                   competition: str, status: str, score: str = None) -> int:
    with db_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM fixtures WHERE home_team=? AND away_team=? AND date=?",
            (home_team, away_team, date)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE fixtures SET status=?, score=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (status, score, existing["id"]))
            return existing["id"]
        else:
            cur = conn.execute("""
                INSERT INTO fixtures (home_team, away_team, date, competition, status, score)
                VALUES (?,?,?,?,?,?)
            """, (home_team, away_team, date, competition, status, score))
            return cur.lastrowid


def get_upcoming_fixtures(team: str = None, limit: int = 10):
    now = __import__('datetime').datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    with db_conn() as conn:
        if team:
            rows = conn.execute("""
                SELECT * FROM fixtures
                WHERE (home_team=? OR away_team=?) AND status='scheduled' AND date >= ?
                ORDER BY date ASC LIMIT ?
            """, (team, team, now, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM fixtures WHERE status='scheduled' AND date >= ?
                ORDER BY date ASC LIMIT ?
            """, (now, limit)).fetchall()
    return [dict(r) for r in rows]


def get_fixture_by_id(fixture_id: int):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM fixtures WHERE id=?", (fixture_id,)).fetchone()
    return dict(row) if row else None


# ── Odds ──────────────────────────────────────────────────────────────────────

def upsert_odds(fixture_id: int, market: str, outcome: str, odds_val: float, bookmaker: str):
    with db_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM odds WHERE fixture_id=? AND market=? AND outcome=? AND bookmaker=?",
            (fixture_id, market, outcome, bookmaker)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE odds SET odds=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (odds_val, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO odds (fixture_id, market, outcome, odds, bookmaker) VALUES (?,?,?,?,?)",
                (fixture_id, market, outcome, odds_val, bookmaker)
            )


def get_odds_for_fixture(fixture_id: int):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM odds WHERE fixture_id=?", (fixture_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Reports Cache ─────────────────────────────────────────────────────────────

def get_cached_report(player_id: int, max_age_seconds: int = 7200):
    with db_conn() as conn:
        row = conn.execute("""
            SELECT * FROM reports_cache
            WHERE player_id=?
            AND (UNIXEPOCH('now') - UNIXEPOCH(created_at)) < ?
            ORDER BY created_at DESC LIMIT 1
        """, (player_id, max_age_seconds)).fetchone()
    if not row:
        return None
    r = dict(row)
    if r.get("dimensions_json"):
        r["dimensions"] = json.loads(r["dimensions_json"])
    return r


def save_report_cache(player_id: int, fixture_id: int, edge_score: int,
                      confidence: str, risk_level: str, dimensions: dict,
                      narrative_avg: str, narrative_agg: str, narrative_con: str):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO reports_cache
                (player_id, fixture_id, edge_score, confidence, risk_level,
                 dimensions_json, narrative_avg, narrative_agg, narrative_con)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            player_id, fixture_id, edge_score, confidence, risk_level,
            json.dumps(dimensions), narrative_avg, narrative_agg, narrative_con
        ))


# ── Scrape Log ────────────────────────────────────────────────────────────────

def log_scrape(source: str, status: str, message: str = ""):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO scrape_log (source, status, message) VALUES (?,?,?)",
            (source, status, message)
        )


def get_last_scrape(source: str):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT ran_at, status FROM scrape_log WHERE source=? ORDER BY ran_at DESC LIMIT 1",
            (source,)
        ).fetchone()
    return dict(row) if row else None


# ── LLM Log ──────────────────────────────────────────────────────────────────

def log_llm(provider: str, model: str, use_case: str, player_id: int | None,
            user_message: str, response: str, input_tokens: int,
            output_tokens: int, latency_ms: int):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO llm_log
                (provider, model, use_case, player_id, user_message, response,
                 input_tokens, output_tokens, latency_ms)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (provider, model, use_case, player_id,
              user_message[:2000], response[:8000],
              input_tokens, output_tokens, latency_ms))


def add_llm_feedback(log_id: int, rating: int):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO llm_feedback (log_id, rating) VALUES (?,?)",
            (log_id, rating)
        )


def get_llm_stats():
    with db_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_calls,
                SUM(input_tokens + output_tokens) as total_tokens,
                AVG(latency_ms) as avg_latency_ms,
                provider, use_case
            FROM llm_log
            GROUP BY provider, use_case
        """).fetchall()
    return [dict(r) for r in row]


# ── Users / Auth ──────────────────────────────────────────────────────────────

def create_user(email: str, hashed_password: str) -> int:
    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
            (email.lower().strip(), hashed_password)
        )
        return cur.lastrowid


def get_user_by_email(email: str):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email=? AND is_active=1",
            (email.lower().strip(),)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id=? AND is_active=1", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def update_user_password(user_id: int, hashed_password: str):
    with db_conn() as conn:
        conn.execute(
            "UPDATE users SET hashed_password=? WHERE id=?",
            (hashed_password, user_id)
        )


def create_reset_token(user_id: int, token: str, expires_at: str):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?,?,?)",
            (user_id, token, expires_at)
        )


def get_reset_token(token: str):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE token=? AND used=0",
            (token,)
        ).fetchone()
    return dict(row) if row else None


def mark_reset_token_used(token: str):
    with db_conn() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used=1 WHERE token=?", (token,)
        )
