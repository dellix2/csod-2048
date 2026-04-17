import httpx

from app.config import Settings


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
    """Merge common nested shapes so lookups see CSOD / OData-style payloads."""
    flat = dict(userinfo)
    for nest_key in (
        "user",
        "User",
        "profile",
        "Profile",
        "data",
        "Data",
        "properties",
        "Properties",
        "result",
        "Result",
    ):
        nested = userinfo.get(nest_key)
        if isinstance(nested, dict):
            flat.update(nested)
    return flat


def parse_csod_user(userinfo: dict) -> tuple[str, str]:
    """
    Returns (user_id, display_name) from CSOD userinfo payload.
    Field names vary by tenant; we accept common OAuth + CSOD variants.
    """
    if not isinstance(userinfo, dict):
        raise ValueError("userinfo JSON is not an object")

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
        # Prefer scalar values on keys that look like identifiers (tenant-specific casing).
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
        keys = sorted({*userinfo.keys(), *u.keys()})
        raise ValueError(
            "userinfo did not contain a recognizable user id field. "
            f"Top-level JSON keys were: {keys!s}"
        )

    name = (
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
        or str(uid)
    )
    return str(uid), str(name)
