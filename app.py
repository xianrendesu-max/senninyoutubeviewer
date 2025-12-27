from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
import asyncio

app = FastAPI(title="仙人YouTubeビュアー")

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

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# ===============================
# 最速インスタンス探索
# ===============================
async def probe_instance(client, base):
    try:
        r = await client.get(
            base + "/api/v1/search?q=test&type=video",
            timeout=4
        )
        if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
            return base
    except:
        pass
    return None

@app.get("/api/instances")
async def get_fast_instances():
    async with httpx.AsyncClient(headers=HEADERS) as client:
        tasks = [probe_instance(client, i) for i in INSTANCES["video"]]
        results = await asyncio.gather(*tasks)

    alive = [r for r in results if r]
    if not alive:
        return {"fastest": None, "instances": []}

    return {
        "fastest": alive[0],
        "instances": alive
    }

# ===============================
# 共通 fetch
# ===============================
async def fetch_json(category, path):
    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        for base in INSTANCES.get(category, []):
            try:
                r = await client.get(base + path)
                if r.status_code != 200:
                    continue
                if "application/json" not in r.headers.get("content-type", ""):
                    continue
                return r.json(), base
            except:
                continue
    return None, None

# ===============================
# 検索
# ===============================
@app.get("/api/search")
async def search(q: str):
    data, _ = await fetch_json("search", f"/api/v1/search?q={q}&type=video")
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

# ===============================
# 動画情報
# ===============================
@app.get("/api/video")
async def video(video_id: str):
    data, base = await fetch_json("video", f"/api/v1/videos/{video_id}")
    if not data:
        return JSONResponse(status_code=503, content={"error": "video failed"})

    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "instance": base
    }

# ===============================
# コメント
# ===============================
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

# ===============================
# ダウンロード（即リダイレクト）
# ===============================
@app.get("/api/download")
async def download(video_id: str):
    data, _ = await fetch_json("video", f"/api/v1/videos/{video_id}")
    if not data:
        return JSONResponse(status_code=503, content={"error": "download failed"})

    streams = data.get("formatStreams", []) + data.get("adaptiveFormats", [])
    for s in streams:
        url = s.get("url")
        if url and url.startswith("http"):
            return RedirectResponse(url=url, status_code=302)

    return JSONResponse(status_code=500, content={"error": "no stream"})

app.mount("/", StaticFiles(directory="statics", html=True), name="statics")
