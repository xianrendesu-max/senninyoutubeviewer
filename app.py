from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
import logging
from urllib.parse import urlencode

app = FastAPI(title="仙人YouTubeビュアー")
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INSTANCES = {
    "video": [
        "https://invidious.exma.de",
        "https://invidious.f5.si",
        "https://siawaseok-wakame-server2.glitch.me",
        "https://lekker.gay",
        "https://id.420129.xyz",
        "https://invid-api.poketube.fun",
        "https://eu-proxy.poketube.fun",
        "https://cal1.iv.ggtyler.dev",
        "https://pol1.iv.ggtyler.dev",
    ],
    "search": [
        "https://pol1.iv.ggtyler.dev",
        "https://youtube.mosesmang.com",
        "https://iteroni.com",
        "https://invidious.0011.lt",
        "https://iv.melmac.space",
        "https://rust.oskamp.nl",
    ],
    "comments": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
    ],
}

async def fetch_json(category: str, path: str):
    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(12.0)
    ) as client:

        for base in INSTANCES.get(category, []):
            try:
                r = await client.get(base + path)

                if r.status_code != 200:
                    logging.warning(f"{base} -> {r.status_code}")
                    continue

                if "application/json" not in r.headers.get("content-type", ""):
                    logging.warning(f"{base} -> not json")
                    continue

                return r.json(), base

            except Exception as e:
                logging.warning(f"{base} -> error {e}")
                continue

    return None, None

# ===== 検索 =====
@app.get("/api/search")
async def search(q: str = Query(...)):
    params = urlencode({"q": q, "type": "video"})
    data, _ = await fetch_json("search", f"/api/v1/search?{params}")

    if not data:
        return JSONResponse(status_code=503, content={"error": "search failed"})

    return {
        "results": [{
            "videoId": v["videoId"],
            "title": v["title"],
            "author": v["author"],
            "thumbnail": f"https://img.youtube.com/vi/{v['videoId']}/hqdefault.jpg"
        } for v in data]
    }

# ===== 動画情報 =====
@app.get("/api/video")
async def video(video_id: str):
    data, base = await fetch_json("video", f"/api/v1/videos/{video_id}")

    if not data:
        return JSONResponse(status_code=503, content={"error": "video failed"})

    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "instance": base,
        "instances": INSTANCES["video"]
    }

# ===== コメント =====
@app.get("/api/comments")
async def comments(video_id: str):
    data, _ = await fetch_json("comments", f"/api/v1/comments/{video_id}")
    if not data:
        return {"comments": []}

    return {
        "comments": [{
            "author": c.get("author"),
            "content": c.get("content"),
        } for c in data.get("comments", [])]
    }

# ===== ダウンロード（stream URLへ遷移） =====
@app.get("/api/download")
async def download(video_id: str):
    data, base = await fetch_json("video", f"/api/v1/videos/{video_id}")

    if not data:
        return JSONResponse(status_code=503, content={"error": "download failed"})

    streams = data.get("formatStreams", []) + data.get("adaptiveFormats", [])
    for s in streams:
        if s.get("url"):
            return {
                "stream_url": s["url"],
                "used_instance": base
            }

    return JSONResponse(status_code=500, content={"error": "no stream"})

app.mount("/", StaticFiles(directory="statics", html=True), name="statics")
