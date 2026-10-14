"""Render SNES 4bpp tiles from a ROM region to a PNG (grayscale, for locating graphics)."""
import sys
from PIL import Image


def decode_4bpp_tile(data, off):
    """Return 8x8 list of 4-bit pixel values from a 32-byte 4bpp tile."""
    px = [[0] * 8 for _ in range(8)]
    for row in range(8):
        p0, p1 = data[off + row * 2], data[off + row * 2 + 1]
        p2, p3 = data[off + 16 + row * 2], data[off + 16 + row * 2 + 1]
        for col in range(8):
            bit = 7 - col
            v = ((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1) | (((p2 >> bit) & 1) << 2) | (((p3 >> bit) & 1) << 3)
            px[row][col] = v
    return px


def sheet(data, start, count, cols=32, scale=2, out="sheet.png"):
    rows = (count + cols - 1) // cols
    img = Image.new("L", (cols * 8 * scale, rows * 8 * scale), 0)
    for t in range(count):
        off = start + t * 32
        if off + 32 > len(data):
            break
        px = decode_4bpp_tile(data, off)
        tx, ty = (t % cols) * 8 * scale, (t // cols) * 8 * scale
        for r in range(8):
            for c in range(8):
                v = px[r][c] * 17
                for dy in range(scale):
                    for dx in range(scale):
                        img.putpixel((tx + c * scale + dx, ty + r * scale + dy), v)
    img.save(out)
    return out


if __name__ == "__main__":
    path, start, count, out = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4]
    with open(path, "rb") as f:
        data = f.read()
    print(sheet(data, start, count, out=out))
