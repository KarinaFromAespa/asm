import ctypes
import numpy as np
from PIL import Image
import sys

lib = ctypes.CDLL('./premultiply.so')
lib.premultiply_safe.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_int, ctypes.c_int, ctypes.c_int
]
lib.premultiply_safe.restype = ctypes.c_int

def reference_premultiply(pixels):
    """Pillow's actual C formula — NOT Python // division"""
    result = bytearray(pixels)
    for i in range(0, len(result), 4):
        a = result[i+3]
        for ch in range(3):
            v = result[i+ch]
            tmp = v * a + 128
            result[i+ch] = (tmp + (tmp >> 8)) >> 8
    return bytes(result)

def pillow_premultiply(pixels, width, height):
    """Ground truth: actual Pillow convert to RGBa (premultiplied)"""
    arr = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 4)
    img = Image.fromarray(arr, 'RGBA')
    img_pre = img.convert('RGBa')  # Pillow's internal premultiply
    return img_pre.tobytes()

def asm_premultiply(pixels, width, height):
    data = bytearray(pixels)
    arr = (ctypes.c_uint8 * len(data)).from_buffer(data)
    lib.premultiply_safe(arr, width, height, width*4)
    return bytes(data)

def run_test(name, pixels, width, height, use_pillow=False):
    if use_pillow:
        ref = pillow_premultiply(pixels, width, height)
    else:
        ref = reference_premultiply(pixels)
    asm = asm_premultiply(pixels, width, height)

    if ref == asm:
        print(f"  PASS: {name}")
        return True

    mismatches = 0
    first = None
    for i in range(0, len(ref), 4):
        r = ref[i:i+4]
        a = asm[i:i+4]
        if r != a:
            mismatches += 1
            if first is None:
                first = (i//4, r, a)

    print(f"  FAIL: {name} — {mismatches} mismatches")
    if first:
        px, r, a = first
        print(f"    pixel {px}: ref={tuple(r)} asm={tuple(a)}")
    return False

print("=== Correctness Tests (reference = Pillow C formula) ===\n")
passed = 0
total = 0

pixels = bytes([200, 100, 50, 255] * 64)
total += 1
if run_test("fully opaque (alpha=255)", pixels, 8, 8): passed += 1

pixels = bytes([200, 100, 50, 0] * 64)
total += 1
if run_test("fully transparent (alpha=0)", pixels, 8, 8): passed += 1

pixels = bytes([200, 100, 50, 128] * 64)
total += 1
if run_test("half alpha (alpha=128)", pixels, 8, 8): passed += 1

np.random.seed(42)
pixels = bytes(np.random.randint(0, 255, 4*64, dtype=np.uint8))
total += 1
if run_test("random 8x8", pixels, 8, 8): passed += 1

pixels = bytes(np.random.randint(0, 255, 4*1920*1080, dtype=np.uint8))
total += 1
if run_test("random 1920x1080", pixels, 1920, 1080): passed += 1

pixels = bytes(np.random.randint(0, 255, 4*13*7, dtype=np.uint8))
total += 1
if run_test("odd dimensions 13x7 (tail test)", pixels, 13, 7): passed += 1

pixels = bytes([127, 64, 32, 200])
total += 1
if run_test("single pixel", pixels, 1, 1): passed += 1

print("\n  Testing all 256 alpha values...")
all_pass = True
for alpha in range(256):
    pixels = bytes([200, 150, 100, alpha] * 8)
    ref = reference_premultiply(pixels)
    asm = asm_premultiply(pixels, 8, 1)
    if ref != asm:
        print(f"  FAIL: alpha={alpha} ref={tuple(ref[:4])} asm={tuple(asm[:4])}")
        all_pass = False
        break
total += 1
if all_pass:
    print(f"  PASS: all 256 alpha values")
    passed += 1

print("\n  Testing safety validation...")
dummy = (ctypes.c_uint8 * 16)()
r1 = lib.premultiply_safe(None, 100, 100, 400)
r2 = lib.premultiply_safe(dummy, -1, 100, 400)
r3 = lib.premultiply_safe(dummy, 100, 100, 10)
total += 1
if r1 == -1 and r2 == -1 and r3 == -1:
    print(f"  PASS: safety validation (null, negative, bad stride)")
    passed += 1
else:
    print(f"  FAIL: safety r1={r1} r2={r2} r3={r3}")

print("\n=== Ground Truth: validate against actual Pillow output ===\n")
np.random.seed(99)
for name, w, h in [("8x8", 8, 8), ("100x100", 100, 100), ("1920x1080", 1920, 1080)]:
    pixels = bytes(np.random.randint(0, 255, 4*w*h, dtype=np.uint8))
    total += 1
    if run_test(f"vs actual Pillow {name}", pixels, w, h, use_pillow=True):
        passed += 1

print(f"\n=== Results: {passed}/{total} passed ===")
if passed == total:
    print("All tests passed — ASM matches Pillow exactly.")
else:
    print("FAILURES detected — do not ship.")
    sys.exit(1)
