"""Short interaction tones generated with the stdlib and played via winsound."""
import io
import math
import os
import struct
import wave

RATE = 22050
TONES = {
    "start": (880, 90),
    "stop": (660, 90),
    "error": (330, 150),
}


def tone_wav(freq, ms, rate=RATE, volume=0.35, fade_ms=10):
    """Return a mono 16-bit PCM WAV (bytes) of a sine tone with linear fades."""
    n = int(rate * ms / 1000)
    fade = max(1, int(rate * fade_ms / 1000))
    frames = bytearray()
    for i in range(n):
        env = min(1.0, i / fade, (n - 1 - i) / fade) if n > 1 else 0.0
        v = volume * env * math.sin(2 * math.pi * freq * i / rate)
        frames += struct.pack("<h", int(v * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def sounds_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Voice2Txt", "sounds")


def ensure(name):
    """Create the wav for `name` if missing; return its path."""
    freq, ms = TONES[name]
    folder = sounds_dir()
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + ".wav")
    if not os.path.exists(path) or os.path.getsize(path) < 44:
        with open(path, "wb") as f:
            f.write(tone_wav(freq, ms))
    return path


def play(name, enabled=True):
    """Play a tone asynchronously.  Never raises; returns True if started."""
    if not enabled:
        return False
    try:
        import winsound
        path = ensure(name)
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC
                           | winsound.SND_NODEFAULT)
        return True
    except Exception:
        return False
