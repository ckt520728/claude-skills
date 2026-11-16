"""Mute other applications' audio sessions while dictating (Core Audio via ctypes).

No comtypes/pycaw.  Every failure is swallowed into ``handle.errors`` so the
app never breaks because of audio.  ``restore`` is idempotent and also runs
from an atexit hook.

Limitation: a process that is force-killed (Task Manager "End task",
``taskkill /F``, a crash) cannot run atexit, so the sessions it muted stay
muted, and Windows remembers per-app session mute across restarts of those
apps.  Unmute them in the Volume Mixer (documented in USER_MANUAL.md (T18)).
"""
import atexit
import ctypes
import os
import threading
import uuid
from ctypes import POINTER, WINFUNCTYPE, byref, c_int, c_long, c_ulong, c_void_p

CLSCTX_ALL = 23
E_RENDER = 0    # EDataFlow.eRender
E_CONSOLE = 0   # ERole.eConsole
COINIT_MULTITHREADED = 0
S_OK = 0

# --- GUIDs -----------------------------------------------------------------
CLSID_MMDeviceEnumerator = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
IID_IMMDeviceEnumerator = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
IID_IAudioSessionManager2 = "{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}"
IID_IAudioSessionControl2 = "{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}"
IID_ISimpleAudioVolume = "{87CE5498-68D6-44E5-9215-6DA47EF883D8}"

# --- vtable indices (0..2 are always QueryInterface, AddRef, Release) ------
VT_QUERY_INTERFACE = 0
VT_ADD_REF = 1
VT_RELEASE = 2
# IMMDeviceEnumerator: 3 EnumAudioEndpoints, 4 GetDefaultAudioEndpoint
VT_ENUM_GET_DEFAULT_AUDIO_ENDPOINT = 4
# IMMDevice: 3 Activate
VT_DEVICE_ACTIVATE = 3
# IAudioSessionManager2: 3 GetAudioSessionControl, 4 GetSimpleAudioVolume,
#                        5 GetSessionEnumerator
VT_MGR_GET_SESSION_ENUMERATOR = 5
# IAudioSessionEnumerator: 3 GetCount, 4 GetSession
VT_SESSENUM_GET_COUNT = 3
VT_SESSENUM_GET_SESSION = 4
# IAudioSessionControl2 extends IAudioSessionControl:
#   3 GetState, 4 GetDisplayName, 5 SetDisplayName, 6 GetIconPath,
#   7 SetIconPath, 8 GetGroupingParam, 9 SetGroupingParam,
#   10 RegisterAudioSessionNotification, 11 UnregisterAudioSessionNotification
# then its own methods:
#   12 GetSessionIdentifier, 13 GetSessionInstanceIdentifier, 14 GetProcessId,
#   15 IsSystemSoundsSession, 16 SetDuckingPreference
VT_CTL2_GET_PROCESS_ID = 14
VT_CTL2_IS_SYSTEM_SOUNDS = 15
# ISimpleAudioVolume: 3 SetMasterVolume, 4 GetMasterVolume, 5 SetMute, 6 GetMute
VT_VOL_SET_MUTE = 5
VT_VOL_GET_MUTE = 6


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, text=None):
        super().__init__()
        if text:
            u = uuid.UUID(text)
            self.Data1, self.Data2, self.Data3 = u.time_low, u.time_mid, u.time_hi_version
            for i, b in enumerate(u.bytes[8:]):
                self.Data4[i] = b


def _method(ptr, index, *argtypes):
    """Bind vtable slot `index` of COM object `ptr` (pointer value)."""
    vtbl = ctypes.cast(ptr, POINTER(POINTER(c_void_p)))[0]
    fn = WINFUNCTYPE(c_long, c_void_p, *argtypes)(vtbl[index])
    return lambda *args: fn(ptr, *args)


def _check(hr, what):
    if hr < 0:
        raise OSError("%s failed: HRESULT 0x%08X" % (what, hr & 0xFFFFFFFF))
    return hr


def _release(ptr):
    try:
        if ptr:
            _method(ptr, VT_RELEASE)()
    except Exception:
        pass


def _query(ptr, iid_text):
    out = c_void_p()
    iid = GUID(iid_text)
    _check(_method(ptr, VT_QUERY_INTERFACE, POINTER(GUID), POINTER(c_void_p))(
        byref(iid), byref(out)), "QueryInterface")
    return out.value


class Handle:
    def __init__(self):
        self.sessions_seen = 0
        self.muted = []        # [(pid, ISimpleAudioVolume pointer)]
        self.errors = []
        self.pids = []         # pids muted (kept after restore)
        self.restored = False
        self._lock = threading.Lock()

    @property
    def muted_pids(self):
        return list(self.pids)


def _com_init():
    # MTA so interface pointers stay usable from any thread.  Deliberately
    # never paired with CoUninitialize: tearing down the MTA would invalidate
    # the pointers kept in the handle.  A changed-mode error is ignored.
    try:
        ctypes.windll.ole32.CoInitializeEx(None, COINIT_MULTITHREADED)
    except Exception:
        pass


def _sessions(handle, visit):
    """visit(pid, is_system, ISimpleAudioVolume) -> True to keep the volume pointer."""
    _com_init()
    ole = ctypes.windll.ole32
    ole.CoCreateInstance.argtypes = [POINTER(GUID), c_void_p, c_ulong,
                                     POINTER(GUID), POINTER(c_void_p)]
    ole.CoCreateInstance.restype = c_long
    enum = device = mgr = senum = None
    try:
        out = c_void_p()
        clsid, iid = GUID(CLSID_MMDeviceEnumerator), GUID(IID_IMMDeviceEnumerator)
        _check(ole.CoCreateInstance(byref(clsid), None, CLSCTX_ALL, byref(iid),
                                    byref(out)), "CoCreateInstance")
        enum = out.value
        dev = c_void_p()
        _check(_method(enum, VT_ENUM_GET_DEFAULT_AUDIO_ENDPOINT, c_int, c_int,
                       POINTER(c_void_p))(E_RENDER, E_CONSOLE, byref(dev)),
               "GetDefaultAudioEndpoint")
        device = dev.value
        m = c_void_p()
        miid = GUID(IID_IAudioSessionManager2)
        _check(_method(device, VT_DEVICE_ACTIVATE, POINTER(GUID), c_ulong,
                       c_void_p, POINTER(c_void_p))(byref(miid), CLSCTX_ALL,
                                                    None, byref(m)), "Activate")
        mgr = m.value
        se = c_void_p()
        _check(_method(mgr, VT_MGR_GET_SESSION_ENUMERATOR, POINTER(c_void_p))(
            byref(se)), "GetSessionEnumerator")
        senum = se.value
        count = c_int()
        _check(_method(senum, VT_SESSENUM_GET_COUNT, POINTER(c_int))(byref(count)),
               "GetCount")
        for i in range(count.value):
            ctl = ctl2 = vol = None
            try:
                c = c_void_p()
                _check(_method(senum, VT_SESSENUM_GET_SESSION, c_int,
                               POINTER(c_void_p))(i, byref(c)), "GetSession")
                ctl = c.value
                ctl2 = _query(ctl, IID_IAudioSessionControl2)
                handle.sessions_seen += 1
                system = _method(ctl2, VT_CTL2_IS_SYSTEM_SOUNDS)() == S_OK
                pid = c_ulong()
                _check(_method(ctl2, VT_CTL2_GET_PROCESS_ID, POINTER(c_ulong))(
                    byref(pid)), "GetProcessId")
                vol = _query(ctl, IID_ISimpleAudioVolume)
                if visit(pid.value, system, vol):
                    vol = None  # ownership moved to the handle
            except Exception as exc:
                handle.errors.append("session %d: %s" % (i, exc))
            finally:
                _release(vol)
                _release(ctl2)
                _release(ctl)
    except Exception as exc:
        handle.errors.append(str(exc))
    finally:
        for p in (senum, mgr, device, enum):
            _release(p)


def get_mute(vol):
    b = c_int()
    _check(_method(vol, VT_VOL_GET_MUTE, POINTER(c_int))(byref(b)), "GetMute")
    return bool(b.value)


def set_mute(vol, value):
    _check(_method(vol, VT_VOL_SET_MUTE, c_int, c_void_p)(1 if value else 0, None),
           "SetMute")


def snapshot():
    """Read-only [{'pid','system','muted'}] plus errors (diagnostics / checks)."""
    h = Handle()
    rows = []

    def visit(pid, system, vol):
        rows.append({"pid": pid, "system": system, "muted": get_mute(vol)})
        return False
    _sessions(h, visit)
    return rows, h.errors


_active = []


def mute_others(own_pid=None):
    """Mute every non-system session not owned by own_pid and not already muted."""
    handle = Handle()
    own_pid = os.getpid() if own_pid is None else own_pid

    def visit(pid, system, vol):
        if system or pid == own_pid or pid == 0:
            return False
        if get_mute(vol):
            return False
        set_mute(vol, True)
        handle.muted.append((pid, vol))
        handle.pids.append(pid)
        return True
    try:
        _sessions(handle, visit)
    except Exception as exc:
        handle.errors.append(str(exc))
    _active.append(handle)
    return handle


def restore(handle):
    """Unmute exactly what mute_others muted.  Idempotent, never raises."""
    if handle is None:
        return
    try:
        with handle._lock:
            if handle.restored:
                return
            handle.restored = True
            _com_init()
            for pid, vol in handle.muted:
                try:
                    set_mute(vol, False)
                except Exception as exc:
                    handle.errors.append("restore %s: %s" % (pid, exc))
                _release(vol)
            handle.muted = []
    except Exception as exc:
        handle.errors.append(str(exc))
    finally:
        try:
            _active.remove(handle)  # 已還原的 handle 不再留在清單裡（不會隨錄音次數增長）
        except ValueError:
            pass


def _restore_all():
    for h in list(_active):
        restore(h)


atexit.register(_restore_all)
