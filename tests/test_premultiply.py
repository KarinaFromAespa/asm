import ctypes
import numpy as np
from PIL import Image
import time

lib = ctypes.CDLL('./premultiply.so')
lib.premultiply_safe.argtypes = [
    ctypes.c_char_p,
    ctypes.c_int, ctypes.c_int, ctypes.c_int
]
lib.premultiply_safe.restype = ctypes.c_int

# create test image: 1920x1080 RGBA
img = np.random.randint(0, 255, (1080, 1920, 4), dtype=np.uint8)
buf = img.tobytes()

# benchmark asm version
start = time.perf_counter()
for _ in range(100):
    data = bytearray(buf)
    result = lib.premultiply_safe(
        ctypes.c_char_p(bytes(data)),
        1920, 1080, 1920*4
    )
elapsed_asm = time.perf_counter() - start

print(f"ASM result code: {result}")
print(f"ASM 100x 1080p: {elapsed_asm*1000:.2f}ms")
print(f"Per frame: {elapsed_asm*10:.2f}ms")
