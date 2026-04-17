import httpx

from app.config import Settings


def _base_url(settings: Settings) -> str:
    corp = settings.csod_corp.strip().lower().replace(".csod.com", "")
    return f"https://{corp}.csod.com"


async def exchange_authorization_code(
    settings: Settings, *, code: str, state: str
) -> dict:
    url = f"{_base_url(settings)}/services/api/oauth2/token"
    payload = {
        "grantType": "authorization_code",
        "code": code,
        "clientId": settings.csod_client_id,
        "clientSecret": settings.csod_client_secret,
        "state": state,
        "scope": settings.csod_scopes,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "cache-control": "no-cache"},
        )
        r.raise_for_status()
        return r.json()


async def fetch_userinfo(settings: Settings, access_token: str) -> dict:
    url = f"{_base_url(settings)}/services/api/oauth2/userinfo"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()


def parse_csod_user(userinfo: dict) -> tuple[str, str]:
    """
    Returns (user_id, display_name) from CSOD userinfo payload.
    Field names vary; we accept common variants.
    """
    uid = (
        userinfo.get("userId")
        or userinfo.get("user_id")
        or userinfo.get("UserId")
        or userinfo.get("sub")
        or userinfo.get("id")
    )
    if uid is None:
        raise ValueError("userinfo did not contain a recognizable user id field")

    name = (
        userinfo.get("name")
        or userinfo.get("preferred_username")
        or userinfo.get("displayName")
        or userinfo.get("DisplayName")
        or userinfo.get("userName")
        or userinfo.get("UserName")
        or str(uid)
    )
    return str(uid), str(name)
