from supabase import Client, create_client

from app.config import get_settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        s = get_settings()
        _client = create_client(s.supabase_url, s.supabase_service_key)
    return _client


def upsert_best_score(
    *,
    corp_name: str,
    user_id: str,
    user_name: str,
    score: int,
) -> dict:
    """
    Always refresh user_name (display name can change when employee API starts working).
    best_score is max(previous, submitted session score).
    """
    sb = get_supabase()
    existing = (
        sb.table("leaderboard_scores")
        .select("best_score")
        .eq("corp_name", corp_name)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    prior_best = int(rows[0]["best_score"]) if rows else 0
    new_best = max(prior_best, score)

    row = {
        "corp_name": corp_name,
        "user_id": user_id,
        "user_name": user_name,
        "best_score": new_best,
    }
    res = (
        sb.table("leaderboard_scores")
        .upsert(row, on_conflict="corp_name,user_id")
        .execute()
    )
    data = res.data or []
    return data[0] if data else row


def refresh_display_name_only(
    *,
    corp_name: str,
    user_id: str,
    user_name: str,
) -> dict:
    """
    Upsert display name for this user. Preserves existing best_score when a row exists;
    otherwise inserts a row with best_score 0 so the name is stored before the first game.
    """
    sb = get_supabase()
    existing = (
        sb.table("leaderboard_scores")
        .select("best_score")
        .eq("corp_name", corp_name)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    prior = int(rows[0]["best_score"]) if rows else 0
    row = {
        "corp_name": corp_name,
        "user_id": user_id,
        "user_name": user_name,
        "best_score": prior,
    }
    res = (
        sb.table("leaderboard_scores")
        .upsert(row, on_conflict="corp_name,user_id")
        .execute()
    )
    data = res.data or []
    return data[0] if data else row


def fetch_leaderboard(corp_name: str, limit: int) -> list[dict]:
    """Returns JSON-serializable rows only (avoids 500s from date/Decimal types)."""
    sb = get_supabase()
    res = (
        sb.table("leaderboard_scores")
        .select("user_id,user_name,best_score")
        .eq("corp_name", corp_name)
        .gt("best_score", 0)
        .order("best_score", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "user_id": str(r.get("user_id", "")),
                "user_name": str(r.get("user_name", "")),
                "best_score": int(r.get("best_score", 0)),
            }
        )
    return out
