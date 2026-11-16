"""Real check of voice2txt.audiofocus using a helper child that plays a quiet loop."""
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from voice2txt import audiofocus, sounds  # noqa: E402

CHILD = r"""
import os, sys, time, winsound
winsound.PlaySound(sys.argv[1], winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC)
print(os.getpid(), flush=True)
time.sleep(30)
"""


def state(pid):
    rows, _ = audiofocus.snapshot()
    return [r["muted"] for r in rows if r["pid"] == pid]


def main():
    report = {"ok": False, "own_pid": os.getpid()}
    wav = os.path.join(tempfile.gettempdir(), "v2t_quiet_loop.wav")
    with open(wav, "wb") as f:
        f.write(sounds.tone_wav(440, 1000, volume=0.02))
    child = subprocess.Popen([sys.executable, "-c", CHILD, wav], stdout=subprocess.PIPE)
    handle = None
    try:
        pid = int(child.stdout.readline().decode().strip())
        report["child_pid"] = pid
        deadline = time.time() + 4
        while time.time() < deadline and not state(pid):
            time.sleep(0.2)
        report["child_session_found"] = bool(state(pid))
        report["getmute_before"] = state(pid)
        handle = audiofocus.mute_others(os.getpid())
        report["sessions_seen"] = handle.sessions_seen
        report["muted_pids"] = handle.muted_pids
        report["getmute_during"] = state(pid)
        audiofocus.restore(handle)
        audiofocus.restore(handle)  # idempotent
        report["getmute_after"] = state(pid)
        report["errors"] = handle.errors
        report["ok"] = (report["child_session_found"]
                        and report["getmute_before"] == [False]
                        and pid in report["muted_pids"]
                        and os.getpid() not in report["muted_pids"]
                        and report["getmute_during"] == [True]
                        and report["getmute_after"] == [False])
    except Exception as exc:
        report["exception"] = repr(exc)
    finally:
        if handle is not None:
            audiofocus.restore(handle)
        child.terminate()
        try:
            child.wait(timeout=5)
        except Exception:
            child.kill()
        report["child_running_after"] = child.poll() is None
        report["ok"] = bool(report["ok"]) and not report["child_running_after"]
    out = os.path.join(ROOT, "verification", "audiofocus-2026-11-13.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
