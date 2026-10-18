"""以 Windows DPAPI 加密 API key；只有同一 Windows 使用者能解密。"""
import base64
import ctypes
import sys


class _Blob(ctypes.Structure):
    _fields_ = [('size', ctypes.c_uint32), ('data', ctypes.POINTER(ctypes.c_char))]


def _call(function, data):
    buffer = ctypes.create_string_buffer(data, len(data))
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    result = _Blob()
    # 0x1 = CRYPTPROTECT_UI_FORBIDDEN
    if not function(ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(result)):
        raise OSError('Windows DPAPI 無法處理 API key')
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        ctypes.windll.kernel32.LocalFree(result.data)


def protect(text):
    if not text:
        return ''
    if sys.platform != 'win32':
        raise OSError('僅 Windows 可加密保存 API key')
    return base64.b64encode(_call(ctypes.windll.crypt32.CryptProtectData, text.encode())).decode()


def unprotect(token):
    if not token or sys.platform != 'win32':
        return ''
    try:
        return _call(ctypes.windll.crypt32.CryptUnprotectData, base64.b64decode(token)).decode()
    except (OSError, ValueError):
        return ''
