"""以標準函式庫產生 voice2txt/assets/voice2txt.ico（16x16 與 32x32，32 位元 BMP + AND mask）。

圖案：靛藍實心圓，中央白色膠囊（麥克風）與底座。使用 4x4 超取樣做邊緣平滑。
"""
import math
import struct
from pathlib import Path

INDIGO = (0x4F, 0x46, 0xE5)
WHITE = (255, 255, 255)
SAMPLES = 4


def _in_capsule(x, y, cx, top, bottom, radius):
    """膠囊：兩端半圓、中間矩形。top/bottom 為圓心的 y。"""
    if top <= y <= bottom:
        return abs(x - cx) <= radius
    cy = top if y < top else bottom
    return math.hypot(x - cx, y - cy) <= radius


def _pixel(size, px, py):
    """回傳 (r, g, b, a) 的 0..1 覆蓋率平均，座標為單位正方形 0..1。"""
    r = g = b = a = 0.0
    for sy in range(SAMPLES):
        for sx in range(SAMPLES):
            x = (px + (sx + 0.5) / SAMPLES) / size
            y = (py + (sy + 0.5) / SAMPLES) / size
            if math.hypot(x - 0.5, y - 0.5) > 0.5:
                continue
            color = INDIGO
            if _in_capsule(x, y, 0.5, 0.33, 0.50, 0.12):
                color = WHITE
            elif abs(x - 0.5) <= 0.035 and 0.62 <= y <= 0.74:
                color = WHITE
            elif abs(x - 0.5) <= 0.14 and 0.74 <= y <= 0.79:
                color = WHITE
            elif 0.23 <= (math.hypot(x - 0.5, y - 0.50)) <= 0.27 and y >= 0.50:
                color = WHITE
            r, g, b, a = r + color[0], g + color[1], b + color[2], a + 1
    if a == 0:
        return 0, 0, 0, 0
    n = SAMPLES * SAMPLES
    return round(r / a), round(g / a), round(b / a), round(255 * a / n)


def _image(size):
    pixels = bytearray()
    mask = bytearray()
    row_bytes = ((size + 31) // 32) * 4
    for py in range(size - 1, -1, -1):  # BMP 由下往上
        row_mask = bytearray(row_bytes)
        for px in range(size):
            r, g, b, a = _pixel(size, px, py)
            pixels += bytes((b, g, r, a))
            if a == 0:
                row_mask[px // 8] |= 0x80 >> (px % 8)
        mask += row_mask
    header = struct.pack('<IiiHHIIiiII', 40, size, size * 2, 1, 32, 0, len(pixels) + len(mask), 0, 0, 0, 0)
    return header + bytes(pixels) + bytes(mask)


def build_ico(sizes=(16, 32)):
    images = [_image(s) for s in sizes]
    out = bytearray(struct.pack('<HHH', 0, 1, len(images)))
    offset = 6 + 16 * len(images)
    for size, data in zip(sizes, images):
        out += struct.pack('<BBBBHHII', size, size, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    for data in images:
        out += data
    return bytes(out)


def main():
    path = Path(__file__).resolve().parent.parent / 'voice2txt' / 'assets' / 'voice2txt.ico'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_ico())
    print(path, path.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
