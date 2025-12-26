from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
import logging
from urllib.parse import urlencode

app = FastAPI(title="仙人YouTubeビュアー")

logging.basicConfig(level=logging.INFO)

# ===============================
# CORS
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ===============================
# インスタンス定義（指定どおり全部使用）
# ===============================
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
    "channel": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://id.420129.xyz",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
    ],
    "playlist": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
        "https://youtube.mosesmang.com",
        "https://iv.melmac.space",
        "https://lekker.gay",
    ],
    "comments": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
    ],
}

# ===============================
# 共通フェッチ（自動切替）
# ===============================
async def fetch_json(category: str, path: str):
    async with httpx.AsyncClient(headers=HEADERS, timeout=8) as client:
        for base in INSTANCES.get(category, []):
            try:
                r = await client.get(base + path)
                if r.status_code == 200:
                    return r.json(), base
            except Exception as e:
                logging.warning(f"{base} failed: {e}")
    return None, None

# ===============================
# 検索
# ===============================
@app.get("/api/search")
async def search(q: str = Query(...)):
    params = urlencode({"q": q, "type": "video"})
    data, base = await fetch_json("search", f"/api/v1/search?{params}")

    if not data:
        return JSONResponse(status_code=503, content={"error": "search failed"})

    return {
        "results": [{
            "videoId": v.get("videoId"),
            "title": v.get("title"),
            "author": v.get("author"),
            "thumbnail": f"https://i.ytimg.com/vi/{v.get('videoId')}/hqdefault.jpg"
        } for v in data],
        "used_instance": base
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
        "instance": base,
        "instances": INSTANCES["video"]
    }

# ===============================
# コメント
# ===============================
@app.get("/api/comments")
async def comments(video_id: str):
    data, base = await fetch_json("comments", f"/api/v1/comments/{video_id}")

    if not data:
        return {"comments": []}

    return {
        "comments": [{
            "author": c.get("author"),
            "content": c.get("content"),
            "likeCount": c.get("likeCount", 0)
        } for c in data.get("comments", [])],
        "used_instance": base
    }

# ===============================
# ダウンロード（format + adaptive 両対応）
# ===============================
@app.get("/api/download")
async def download(video_id: str):
    data, base = await fetch_json("video", f"/api/v1/videos/{video_id}")

    if not data:
        return JSONResponse(status_code=503, content={"error": "download failed"})

    formats = []
    streams = data.get("formatStreams", []) + data.get("adaptiveFormats", [])

    for f in streams:
        url = f.get("url")
        if not url:
            continue

        quality = (
            f.get("qualityLabel")
            or f.get("quality")
            or ("audio" if "audio" in f.get("mimeType", "") else "unknown")
        )

        mime = f.get("mimeType", "").split(";")[0]

        formats.append({
            "quality": quality,
            "type": mime,
            "url": url
        })

    if not formats:
        return JSONResponse(status_code=500, content={"error": "no formats"})

    return {
        "formats": formats,
        "used_instance": base
    }

# ===============================
# 静的ファイル
# ===============================
app.mount("/", StaticFiles(directory="statics", html=True), name="statics")
