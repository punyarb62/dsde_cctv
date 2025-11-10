import os, time, asyncio, urllib.parse
from typing import Optional
import numpy as np
import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

BASE = os.getenv("BMA_BASE", "http://www.bmatraffic.com")
UA = os.getenv("BMA_UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
REWARM_SECONDS = int(os.getenv("REWARM_SECONDS", "25"))
TIMEOUT = float(os.getenv("TIMEOUT", "10"))

app = FastAPI(title="BMA Snapshot Microservice", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

client = httpx.AsyncClient(
    headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Connection": "keep-alive",
    },
    timeout=httpx.Timeout(TIMEOUT),
    follow_redirects=True,
)

_last_warm = {}
_warm_locks = {}
def _lock_for(play_id: str) -> asyncio.Lock:
    if play_id not in _warm_locks:
        _warm_locks[play_id] = asyncio.Lock()
    return _warm_locks[play_id]

async def warmup(play_id: str) -> str:
    async with _lock_for(play_id):
        now = time.time()
        if now - _last_warm.get(play_id, 0) < 2:
            return f"{BASE}/PlayVideo.aspx?ID={play_id}"
        await client.get(f"{BASE}/index.aspx")
        play_url = f"{BASE}/PlayVideo.aspx?ID={urllib.parse.quote(str(play_id))}"
        r = await client.get(play_url)
        r.raise_for_status()
        _last_warm[play_id] = time.time()
        return play_url

async def ensure_fresh(play_id: str):
    if time.time() - _last_warm.get(play_id, 0) > REWARM_SECONDS:
        await warmup(play_id)

async def fetch_frame(play_url: str, image_id: str) -> Optional[bytes]:
    headers = {
        "User-Agent": UA,
        "Referer": play_url,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    params = {"image": image_id, "time": int(time.time() * 1000)}
    r = await client.get(f"{BASE}/show.aspx", params=params, headers=headers)
    if r.status_code != 200 or "image" not in (r.headers.get("Content-Type") or ""):
        return None
    return r.content

def is_white_placeholder(img_bytes: bytes) -> bool:
    arr = np.frombuffer(img_bytes, np.uint8)
    return (float(arr.mean()) if arr.size else 255.0) > 250.0

@app.get("/health")
async def health():
    return {"ok": True, "base": BASE}

# Case 1: play_id == image_id
@app.get("/snapshot/{id}")
async def snapshot_same(id: str):
    return await _snapshot(id, id)

# Case 2: play_id != image_id
@app.get("/snapshot/{play_id}/{image_id}")
async def snapshot_pair(play_id: str, image_id: str):
    return await _snapshot(play_id, image_id)

async def _snapshot(play_id: str, image_id: str):
    await ensure_fresh(play_id)
    play_url = f"{BASE}/PlayVideo.aspx?ID={play_id}"

    img = await fetch_frame(play_url, image_id)

    if not img or is_white_placeholder(img):
        play_url = await warmup(play_id)
        img = await fetch_frame(play_url, image_id)

    if not img:
        raise HTTPException(502, f"Failed to fetch snapshot (play_id={play_id}, image_id={image_id})")

    return Response(
        content=img,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "X-Source": "bma_min_flow_microservice",
            "X-Ids": f"{play_id}/{image_id}",
        },
    )

@app.on_event("shutdown")
async def _shutdown():
    await client.aclose()
#uvicorn app:app --reload --port 9000