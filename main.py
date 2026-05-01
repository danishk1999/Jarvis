import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from jarvis import JarvisAgent
from voice import synthesize_speech
from tools import set_notification_callback

active_ws: list[WebSocket] = []
event_loop: asyncio.AbstractEventLoop = None


def push_notification(text: str):
    """Sync callback for background threads (e.g. reminders) to push to the UI."""
    if event_loop and active_ws:
        for ws in active_ws[:]:
            asyncio.run_coroutine_threadsafe(
                ws.send_json({"type": "notification", "text": text}),
                event_loop,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_loop
    event_loop = asyncio.get_event_loop()
    set_notification_callback(push_notification)
    yield


app = FastAPI(lifespan=lifespan)
agent = JarvisAgent()  # requires ANTHROPIC_API_KEY in .env

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    active_ws.append(ws)
    await ws.send_json({"type": "status", "state": "ready"})
    try:
        while True:
            raw = await ws.receive_json()
            msg_type = raw.get("type")

            if msg_type == "message":
                text = raw.get("text", "").strip()
                if not text:
                    continue
                await ws.send_json({"type": "status", "state": "processing"})
                loop = asyncio.get_event_loop()
                reply = await loop.run_in_executor(None, agent.chat, text)
                await ws.send_json({"type": "response", "text": reply})
                await ws.send_json({"type": "status", "state": "speaking"})
                audio = await synthesize_speech(reply)
                if audio:
                    await ws.send_json({"type": "audio", "data": audio})
                else:
                    await ws.send_json({"type": "status", "state": "ready"})

            elif msg_type == "speak":
                # Client asking to speak a notification aloud
                text = raw.get("text", "").strip()
                if text:
                    audio = await synthesize_speech(text)
                    if audio:
                        await ws.send_json({"type": "audio", "data": audio})

    except WebSocketDisconnect:
        if ws in active_ws:
            active_ws.remove(ws)
    except Exception:
        if ws in active_ws:
            active_ws.remove(ws)


if __name__ == "__main__":
    import uvicorn
    print("\n  ◈ J.A.R.V.I.S. starting — open http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
