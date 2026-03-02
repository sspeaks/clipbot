import os
import subprocess

from aiohttp import web

from pogbot.config import dir_path
from pogbot.clipping.detector import pending_clips

TRIMMER_HTML_PATH = os.path.join(os.path.dirname(__file__), "trimmer.html")


async def handle_trim_page(request):
    clip_id = request.match_info["clip_id"]
    if clip_id not in pending_clips:
        return web.Response(text="Clip not found or expired.", status=404)

    with open(TRIMMER_HTML_PATH, "r") as f:
        html = f.read().replace("{{CLIP_ID}}", clip_id)
    return web.Response(text=html, content_type="text/html")


async def handle_get_audio(request):
    clip_id = request.match_info["clip_id"]
    clip_info = pending_clips.get(clip_id)
    if clip_info is None:
        return web.Response(text="Clip not found.", status=404)

    # Prefer compressed OGG for fast browser download, fall back to WAV
    ogg_path = clip_info.get("ogg_path")
    if ogg_path and os.path.exists(ogg_path):
        return web.FileResponse(ogg_path, headers={
            "Content-Type": "audio/ogg",
            "Access-Control-Allow-Origin": "*",
        })

    if not os.path.exists(clip_info["path"]):
        return web.Response(text="Clip not found.", status=404)

    return web.FileResponse(clip_info["path"], headers={
        "Content-Type": "audio/wav",
        "Access-Control-Allow-Origin": "*",
    })


async def handle_post_trim(request):
    clip_id = request.match_info["clip_id"]
    clip_info = pending_clips.get(clip_id)
    if clip_info is None or not os.path.exists(clip_info["path"]):
        return web.json_response({"error": "Clip not found."}, status=404)

    clip_path = clip_info["path"]
    text_channel = clip_info["text_channel"]

    data = await request.json()
    start_sec = float(data.get("start", 0))
    end_sec = float(data.get("end", 30))
    filename = data.get("filename", clip_id)

    # Sanitize filename
    filename = "".join(c for c in filename if c.isalnum() or c in "-_ ")
    if not filename:
        filename = clip_id
    if not filename.endswith(".mp3"):
        filename += ".mp3"

    output_path = os.path.join(dir_path, "assets", "audio", filename)
    if os.path.exists(output_path):
        return web.json_response({"error": "A clip with that name already exists."}, status=409)

    # Use ffmpeg to extract and convert the subrange
    duration = end_sec - start_sec
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-ss", str(start_sec),
                "-t", str(duration),
                "-q:a", "2",
                output_path,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        return web.json_response({"error": f"ffmpeg error: {e.stderr.decode()}"}, status=500)

    # Clean up temp files
    os.remove(clip_path)
    ogg_path = clip_info.get("ogg_path")
    if ogg_path and os.path.exists(ogg_path):
        os.remove(ogg_path)
    del pending_clips[clip_id]

    # Notify the Discord channel where !listen was typed
    if text_channel:
        try:
            await text_channel.send(
                f"✅ New clip **{filename}** saved! Play it with `!playclip {filename}`"
            )
        except Exception:
            pass

    return web.json_response({"ok": True, "filename": filename})


def create_web_app():
    app = web.Application()
    app.router.add_get("/trim/{clip_id}", handle_trim_page)
    app.router.add_get("/audio/{clip_id}", handle_get_audio)
    app.router.add_post("/trim/{clip_id}", handle_post_trim)
    return app


async def start_web_server(port=8080):
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Clip trimmer web server running on http://0.0.0.0:{port}")
