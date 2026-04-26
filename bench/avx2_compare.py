import ctypes
import numpy as np
import time

lib = ctypes.CDLL('./premultiply.so')
lib.premultiply_safe.argtypes = [
    ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int
]
lib.premultiply_safe.restype = ctypes.c_int

img_np = np.random.randint(0, 255, (1080, 1920, 4), dtype=np.uint8)
buf = img_np.tobytes()
RUNS = 100

# numpy baseline
start = time.perf_counter()
for _ in range(RUNS):
    arr = img_np.copy().astype(np.float32)
    alpha = arr[:,:,3:4] / 255.0
    arr[:,:,:3] *= alpha
elapsed_numpy = time.perf_counter() - start

# our asm (now auto-dispatches to AVX2)
start = time.perf_counter()
for _ in range(RUNS):
    data = bytearray(buf)
    lib.premultiply_safe(ctypes.c_char_p(bytes(data)), 1920, 1080, 1920*4)
elapsed_asm = time.perf_counter() - start

print(f"{'Method':<20} {'100x total':>12} {'per frame':>12} {'vs ASM':>10}")
print("-" * 58)
print(f"{'NumPy':<20} {elapsed_numpy*1000:>10.1f}ms {elapsed_numpy*10:>10.1f}ms {elapsed_numpy/elapsed_asm:>9.1f}x")
print(f"{'ASM AVX2':<20} {elapsed_asm*1000:>10.1f}ms {elapsed_asm*10:>10.1f}ms {'(baseline)':>10}")
