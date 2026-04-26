import ctypes
import numpy as np
import time

lib = ctypes.CDLL('./premultiply.so')
lib.premultiply_safe.argtypes = [
    ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int
]
lib.premultiply_safe.restype = ctypes.c_int

img_np = np.random.randint(0, 255, (1080, 1920, 4), dtype=np.uint8)

# get a persistent writable buffer — no copy overhead
buf = np.ascontiguousarray(img_np)
ptr = buf.ctypes.data_as(ctypes.c_char_p)

RUNS = 1000

# pure asm on same buffer — no python copy
start = time.perf_counter()
for _ in range(RUNS):
    lib.premultiply_safe(ptr, 1920, 1080, 1920*4)
elapsed = time.perf_counter() - start

bytes_processed = 1920 * 1080 * 4 * RUNS
gb = bytes_processed / 1e9
bandwidth = gb / elapsed

print(f"Pure ASM (no copy) {RUNS}x: {elapsed*1000:.1f}ms")
print(f"Per frame: {elapsed/RUNS*1000:.3f}ms")
print(f"Throughput: {bandwidth:.1f} GB/s")
print(f"Pixels/sec: {1920*1080*RUNS/elapsed/1e9:.2f} billion")
