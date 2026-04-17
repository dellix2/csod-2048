import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


def _base_url(settings: Settings) -> str:
    corp = settings.csod_corp.strip().lower().replace(".csod.com", "")
    return f"https://{corp}.csod.com"


def userinfo_url(settings: Settings) -> str:
    """Public URL used for GET (documented as /services/api/oauth2/userinfo)."""
    return f"{_base_url(settings)}/services/api/oauth2/userinfo"


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


def _flatten_userinfo(userinfo: dict) -> dict:
    """Merge common nested shapes (only dict nests; skip list `data` — handled elsewhere)."""
    flat = dict(userinfo)
    for nest_key in (
        "user",
        "User",
        "profile",
        "Profile",
        "properties",
        "Properties",
        "result",
        "Result",
    ):
        nested = userinfo.get(nest_key)
        if isinstance(nested, dict):
            flat.update(nested)
    inner = userinfo.get("data")
    if isinstance(inner, dict):
        flat.update(inner)
    return flat


def extract_user_id(userinfo: dict) -> str:
    """
    Internal user id from CSOD userinfo.
    Many tenants return: { "data": ["1026"], "status": 200, ... }.
    """
    if not isinstance(userinfo, dict):
        raise ValueError("userinfo JSON is not an object")

    raw = userinfo.get("data")
    if isinstance(raw, list) and len(raw) > 0 and raw[0] is not None:
        return str(raw[0])

    u = _flatten_userinfo(userinfo)

    uid = (
        u.get("userId")
        or u.get("user_id")
        or u.get("UserId")
        or u.get("personId")
        or u.get("PersonId")
        or u.get("externalId")
        or u.get("ExternalId")
        or u.get("coreUserId")
        or u.get("CoreUserId")
        or u.get("employeeId")
        or u.get("EmployeeId")
        or u.get("candidateId")
        or u.get("CandidateId")
        or u.get("empId")
        or u.get("EmpId")
        or u.get("userGuid")
        or u.get("UserGuid")
        or u.get("UserGUID")
        or u.get("sub")
        or u.get("SUB")
        or u.get("id")
        or u.get("Id")
    )

    if uid is None:
        id_like = (
            "userid",
            "personid",
            "employeeid",
            "candidateid",
            "externalid",
            "coreuserid",
            "empid",
            "guid",
        )
        for k, v in u.items():
            if v is None or isinstance(v, bool) or isinstance(v, (list, dict)):
                continue
            kl = "".join(c for c in k.lower() if c.isalnum())
            if kl in id_like or kl.endswith("userid") or kl == "sub":
                uid = v
                break

    if uid is None:
        keys = sorted(userinfo.keys())
        raise ValueError(
            "userinfo did not contain a recognizable user id field. "
            f"Top-level JSON keys were: {keys!s}"
        )
    return str(uid)


def _name_from_userinfo_flat(u: dict, uid: str) -> str:
    return str(
        u.get("name")
        or u.get("Name")
        or u.get("preferred_username")
        or u.get("displayName")
        or u.get("DisplayName")
        or u.get("userName")
        or u.get("UserName")
        or u.get("fullName")
        or u.get("FullName")
        or u.get("email")
        or u.get("Email")
        or f"User {uid}"
    )


def _extract_first_last_from_dict(d: dict) -> tuple[str | None, str | None]:
    """CSOD / OData-style field names."""
    fn = (
        d.get("firstName")
        or d.get("FirstName")
        or d.get("first_name")
        or d.get("givenName")
        or d.get("GivenName")
        or d.get("preferredFirstName")
        or d.get("PreferredFirstName")
    )
    ln = (
        d.get("lastName")
        or d.get("LastName")
        or d.get("last_name")
        or d.get("familyName")
        or d.get("FamilyName")
        or d.get("surname")
        or d.get("Surname")
    )
    return (
        str(fn).strip() if fn is not None else None,
        str(ln).strip() if ln is not None else None,
    )


def _deep_find_names(obj: object, depth: int = 0) -> tuple[str | None, str | None]:
    """Walk JSON to find first/last name objects (CSOD nesting varies)."""
    if depth > 8:
        return None, None
    if isinstance(obj, dict):
        fn, ln = _extract_first_last_from_dict(obj)
        if fn or ln:
            return fn, ln
        for v in obj.values():
            a, b = _deep_find_names(v, depth + 1)
            if a or b:
                return a, b
    elif isinstance(obj, list):
        for item in obj:
            a, b = _deep_find_names(item, depth + 1)
            if a or b:
                return a, b
    return None, None


async def fetch_employee_display_name(
    settings: Settings, access_token: str, employee_id: str
) -> str | None:
    """
    GET /services/api/x/users/v2/employees/employees/{id} → first + last name for leaderboard.
    """
    base = _base_url(settings)
    urls = [
        f"{base}/services/api/x/users/v2/employees/employees/{employee_id}",
        f"{base}/services/api/x/users/v2/employees/{employee_id}",
    ]
    body: dict | None = None
    last_err: str | None = None
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json, text/plain, */*",
                    },
                )
                r.raise_for_status()
                ct = (r.headers.get("content-type") or "").lower()
                if "json" not in ct:
                    logger.warning("Employee profile non-JSON (%s) for id=%s", ct, employee_id)
                    continue
                parsed = r.json()
                if isinstance(parsed, dict):
                    body = parsed
                    break
                last_err = "response not a JSON object"
        except httpx.HTTPStatusError as e:
            last_err = f"{e.response.status_code}: {e.response.text[:300]}"
            logger.warning("Employee profile %s for id=%s: %s", url, employee_id, last_err)
            continue
        except Exception as e:
            last_err = str(e)
            logger.warning("Employee profile request %s failed for id=%s: %s", url, employee_id, e)
            continue

    if body is None:
        return None

    merged: dict = dict(body)
    inner = body.get("data")
    if isinstance(inner, dict):
        merged.update(inner)
    elif isinstance(inner, list) and len(inner) > 0 and isinstance(inner[0], dict):
        merged.update(inner[0])

    fn, ln = _extract_first_last_from_dict(merged)
    if not fn and not ln:
        fn, ln = _deep_find_names(body)

    parts = [p for p in (fn, ln) if p]
    if parts:
        name = " ".join(parts)
        logger.info("Resolved employee display name for id=%s", employee_id)
        return name
    logger.warning("Employee JSON had no first/last fields for id=%s keys=%s", employee_id, list(body.keys()))
    return None


async def resolve_user_profile(
    settings: Settings, access_token: str, userinfo: dict
) -> tuple[str, str]:
    """
    Returns (user_id, display_name) for leaderboard /me using userinfo + employees API when needed.
    """
    uid = extract_user_id(userinfo)
    display = await fetch_employee_display_name(settings, access_token, uid)
    if not display:
        u = _flatten_userinfo(userinfo)
        display = _name_from_userinfo_flat(u, uid)
    return uid, display


def parse_csod_user(userinfo: dict) -> tuple[str, str]:
    """Sync parse (userinfo only, no employees call). Prefer resolve_user_profile in API routes."""
    uid = extract_user_id(userinfo)
    u = _flatten_userinfo(userinfo)
    return uid, _name_from_userinfo_flat(u, uid)
