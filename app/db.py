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
    if rows and int(rows[0]["best_score"]) >= score:
        return rows[0]

    row = {
        "corp_name": corp_name,
        "user_id": user_id,
        "user_name": user_name,
        "best_score": score,
    }
    res = (
        sb.table("leaderboard_scores")
        .upsert(row, on_conflict="corp_name,user_id")
        .execute()
    )
    data = res.data or []
    return data[0] if data else row


def fetch_leaderboard(corp_name: str, limit: int) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("leaderboard_scores")
        .select("user_id,user_name,best_score,updated_at")
        .eq("corp_name", corp_name)
        .order("best_score", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []
