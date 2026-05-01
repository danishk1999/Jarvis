import base64
import io
import edge_tts

VOICE = "en-GB-RyanNeural"
RATE = "-5%"
PITCH = "-12Hz"


async def synthesize_speech(text: str) -> str:
    """Return base64-encoded MP3 of text spoken in JARVIS voice."""
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    data = buf.read()
    if not data:
        return ""
    return base64.b64encode(data).decode()
