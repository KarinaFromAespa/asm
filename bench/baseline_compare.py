import ctypes
import numpy as np
from PIL import Image
import time

# load our asm lib
lib = ctypes.CDLL('./premultiply.so')
lib.premultiply_safe.argtypes = [
    ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int
]
lib.premultiply_safe.restype = ctypes.c_int

# test image
img_np = np.random.randint(0, 255, (1080, 1920, 4), dtype=np.uint8)
buf = img_np.tobytes()

RUNS = 100

# --- baseline: pure numpy premultiply ---
start = time.perf_counter()
for _ in range(RUNS):
    arr = img_np.copy().astype(np.float32)
    alpha = arr[:,:,3:4] / 255.0
    arr[:,:,:3] *= alpha
    result_np = arr.astype(np.uint8)
elapsed_numpy = time.perf_counter() - start

# --- baseline: pure python loop (small sample) ---
start = time.perf_counter()
for _ in range(10):
    pixels = bytearray(buf)
    for i in range(0, len(pixels), 4):
        a = pixels[i+3]
        pixels[i]   = pixels[i]   * a // 255
        pixels[i+1] = pixels[i+1] * a // 255
        pixels[i+2] = pixels[i+2] * a // 255
elapsed_python = (time.perf_counter() - start) * 10  # scale to 100 runs

# --- our asm ---
start = time.perf_counter()
for _ in range(RUNS):
    data = bytearray(buf)
    lib.premultiply_safe(ctypes.c_char_p(bytes(data)), 1920, 1080, 1920*4)
elapsed_asm = time.perf_counter() - start

print(f"{'Method':<20} {'100x total':>12} {'per frame':>12} {'vs ASM':>10}")
print("-" * 58)
print(f"{'Pure Python':<20} {elapsed_python*1000:>10.1f}ms {elapsed_python*10:>10.1f}ms {elapsed_python/elapsed_asm:>9.1f}x")
print(f"{'NumPy':<20} {elapsed_numpy*1000:>10.1f}ms {elapsed_numpy*10:>10.1f}ms {elapsed_numpy/elapsed_asm:>9.1f}x")
print(f"{'ASM SSE4':<20} {elapsed_asm*1000:>10.1f}ms {elapsed_asm*10:>10.1f}ms {'(baseline)':>10}")
