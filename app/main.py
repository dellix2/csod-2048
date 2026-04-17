import asyncio
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import csod, db
from app.config import Settings, get_settings

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="2048 CSOD Widget")


class TokenExchangeBody(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class ScoreBody(BaseModel):
    score: int = Field(ge=0, le=10_000_000)


async def bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return token


@app.post("/api/auth/token")
async def exchange_token(
    body: TokenExchangeBody, settings: Settings = Depends(get_settings)
):
    try:
        data = await csod.exchange_authorization_code(
            settings, code=body.code, state=body.state
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.text
        raise HTTPException(status_code=e.response.status_code, detail=detail) from e
    access = data.get("access_token")
    if not access:
        raise HTTPException(status_code=502, detail="Token response missing access_token")
    return {
        "access_token": access,
        "expires_in": data.get("expires_in"),
        "token_type": data.get("token_type", "Bearer"),
        "scope": data.get("scope"),
    }


@app.get("/api/me")
async def me(
    settings: Settings = Depends(get_settings),
    token: str = Depends(bearer_token),
):
    try:
        userinfo = await csod.fetch_userinfo(settings, token)
        uid, name = csod.parse_csod_user(userinfo)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"user_id": uid, "user_name": name, "corp": settings.csod_corp}


@app.post("/api/scores")
async def submit_score(
    body: ScoreBody,
    settings: Settings = Depends(get_settings),
    token: str = Depends(bearer_token),
):
    try:
        userinfo = await csod.fetch_userinfo(settings, token)
        uid, name = csod.parse_csod_user(userinfo)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    row = await asyncio.to_thread(
        db.upsert_best_score,
        corp_name=settings.csod_corp,
        user_id=uid,
        user_name=name,
        score=body.score,
    )
    return {"saved": True, "best_score": row.get("best_score", body.score)}


@app.get("/api/leaderboard")
async def leaderboard(settings: Settings = Depends(get_settings)):
    rows = await asyncio.to_thread(
        db.fetch_leaderboard,
        settings.csod_corp,
        settings.leaderboard_limit,
    )
    return {"corp": settings.csod_corp, "entries": rows}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


app.mount(
    "/",
    StaticFiles(directory=str(STATIC_DIR), html=True),
    name="static",
)
