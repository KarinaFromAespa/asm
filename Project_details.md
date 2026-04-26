# pillow-asm

> Hand-written x86-64 SIMD assembly optimizations for Python image processing — a modern revival and extension of the abandoned Pillow-SIMD project.

---

## Overview

**Pillow** is the most downloaded Python package for image processing, with ~238 million downloads per month. It powers ML training pipelines, Django/Flask thumbnail stacks, and virtually every Python application that touches images. Despite its ubiquity, Pillow's core operations run in generic scalar C with no SIMD optimization.

**Pillow-SIMD** was a drop-in replacement that proved 4–6x performance gains using SSE4/AVX2 — but it was abandoned in 2021 and no longer tracks upstream Pillow.

**pillow-asm** picks up where Pillow-SIMD left off: hand-written NASM assembly targeting SSE4.2, AVX2, and AVX-512, with a safe C validation layer, runtime CPUID dispatch, and pixel-exact correctness against the Pillow reference implementation.

---

## Goals

- Implement core Pillow image operations in hand-written x86-64 NASM assembly
- Target SSE4.2 → AVX2 → AVX-512 with runtime CPU dispatch
- Maintain pixel-exact correctness against Pillow's reference output
- Ship as a drop-in `pip install` replacement requiring zero code changes from users
- Cover the operations most critical to ML pipelines and web image stacks

---

## Why Assembly

Modern compilers are good but not perfect. For tight image processing loops:

- Hand-written SIMD processes 8–16 pixels per clock cycle vs 1 scalar
- No abstraction overhead — zero runtime, zero GC, zero stdlib
- Full control over register allocation, cache behavior, and instruction scheduling
- Proven results: our SSE4.2 prototype beats NumPy by **14x** on premultiply alpha

The key insight: assembly wins not by being clever, but by eliminating every layer between the math and the hardware.

---

## Architecture

```
Python caller
     │
     ▼
C validation layer          ← all safety checks live here
     │                         (bounds, alignment, null, overflow)
     ▼
CPUID dispatch              ← runtime detection: SSE4 / AVX2 / AVX-512
     │
     ├──▶ ASM SSE4.2 path   ← 128-bit XMM, 4 pixels/cycle, fallback
     ├──▶ ASM AVX2 path     ← 256-bit YMM, 8 pixels/cycle, primary target
     └──▶ ASM AVX-512 path  ← 512-bit ZMM, 16 pixels/cycle, stretch goal
```

The C layer validates all inputs before any assembly runs. The assembly itself contains no bounds checks — it operates at full speed on pre-validated data. This gives safety with zero measurable performance overhead (~10 cycles vs millions for the SIMD work).

---

## Environment

| Component | Details |
|---|---|
| OS | Ubuntu 24.04 LTS x86-64 (WSL2) |
| Assembler | NASM 2.16.01 |
| Compiler | GCC 13.3.0 |
| Python | 3.x |
| Pillow | 12.2.0 (benchmark baseline) |
| Host CPU | Intel Core i5-11400H (Tiger Lake) |
| SIMD support | SSE4.1, SSE4.2, AVX2, AVX-512F/DQ/BW/VL/VBMI2/VNNI |

---

## Project Structure

```
pillow-asm/
├── asm/
│   ├── premultiply_alpha.asm     # SSE4.2 RGBA premultiply
│   └── premultiply_avx2.asm      # AVX2 RGBA premultiply
├── src/
│   └── premultiply.c             # C validation wrapper + CPUID dispatch
├── tests/
│   └── correctness.py            # pixel-exact correctness vs reference
├── bench/
│   ├── baseline_compare.py       # Python / NumPy / ASM comparison
│   ├── avx2_compare.py           # NumPy vs AVX2 dispatch
│   └── bandwidth_test.py         # raw throughput, GB/s measurement
└── README.md
```

---

## Roadmap

### Phase 1 — Foundation ✅ In Progress
- [x] Environment setup (WSL2, NASM, GCC, Python toolchain)
- [x] Project structure
- [x] First SSE4.2 routine: RGBA alpha premultiplication
- [x] AVX2 version of premultiply
- [x] C validation + safety wrapper
- [x] CPUID runtime dispatch
- [x] Benchmark harness
- [ ] **Pixel-exact correctness** ← current blocker (see Known Issues)

### Phase 2 — Core Operations
- [ ] RGB ↔ RGBA conversion
- [ ] Bilinear resize (SSE4.2 + AVX2)
- [ ] Bicubic resize
- [ ] Lanczos resampling (hardest — fixed-point convolution kernel)
- [ ] Horizontal + vertical pass separation

### Phase 3 — AVX-512
- [ ] AVX-512 premultiply (16 pixels/cycle)
- [ ] AVX-512 bilinear resize using VBMI2/VNNI
- [ ] CPUID dispatch extended to 3-way (SSE4 / AVX2 / AVX-512)

### Phase 4 — Safety & Testing
- [ ] AFL++ fuzz testing against C wrapper
- [ ] Malformed input corpus (zero dimensions, misaligned, overflow)
- [ ] Valgrind memcheck clean pass
- [ ] Edge case matrix: all pixel formats, all alpha values, odd dimensions

### Phase 5 — Integration
- [ ] Python C extension (replace ctypes with proper CPython extension)
- [ ] setuptools wheel build with asm objects
- [ ] Drop-in Pillow API compatibility layer
- [ ] PyPI packaging

### Phase 6 — Release
- [ ] Upstream benchmark suite
- [ ] Documentation
- [ ] GitHub release + PyPI publish

---

## Benchmark Results (Current)

### With copy overhead (realistic Python usage)

| Method | 100x total | Per frame | vs ASM |
|---|---|---|---|
| Pure Python | 70,406ms | 704ms | 396x slower |
| NumPy | 2,557ms | 25.6ms | 14x slower |
| ASM SSE4.2 | 178ms | 1.8ms | baseline |

### Without copy overhead (raw SIMD throughput)

| Metric | Value |
|---|---|
| Per frame (1920×1080) | **0.8ms** |
| Throughput | **10.3 GB/s** |
| Pixels/second | **2.58 billion** |
| Theoretical FPS | 1,250 fps |

> We are hitting the memory bandwidth ceiling — the SIMD math is faster than RAM can supply data. This is the correct result for a memory-bound operation.

---

## Known Issues

### ❌ Correctness: divide-by-255 rounding mismatch

**Status:** Active — blocking Phase 1 completion

**Symptom:**
```
FAIL: random 8x8 — 55 mismatches
  pixel 0: ref=(38, 81, 83, 95) asm=(38, 82, 84, 95)
FAIL: single pixel — 1 mismatches
  pixel 0: ref=(99, 50, 25, 200) asm=(100, 50, 25, 200)
FAIL: alpha=1 ref=(0, 0, 0, 1) asm=(1, 1, 0, 1)
```

**Root cause:**
The SIMD divide-by-255 approximation `(x + (x>>8)) >> 8` produces rounding that differs from Python's integer floor division `x * a // 255` by ±1 for certain input values. The `+128` correction brings it closer to nearest-rounding but overshoots floor division in other cases.

**Formula comparison:**

| Method | Formula | Behavior |
|---|---|---|
| Exact | `x * a / 255` | true result |
| Python `//` | `x * a // 255` | floor (truncate) |
| ASM current | `(x*a + 128 + ((x*a+128)>>8)) >> 8` | nearest rounding |
| ASM needed | match Python `//` exactly | truncation |

**Options under investigation:**
1. Use `(x*a * 257) >> 16` — exact for all 8-bit inputs, fits in 16-bit after multiply only if done carefully
2. Use `(x*a) >> 8` — fast but incorrect for many values
3. Match Pillow's actual C source formula exactly rather than Python reference

**Next action:** Read Pillow's actual C source `ImagingPremultiplyAlpha` to determine the canonical formula, then match it — not the Python reference loop which may itself be an approximation.

---

## Building

```bash
# assemble
nasm -f elf64 asm/premultiply_alpha.asm -o asm/premultiply_alpha.o
nasm -f elf64 asm/premultiply_avx2.asm  -o asm/premultiply_avx2.o

# compile C wrapper
gcc -c src/premultiply.c -o src/premultiply.o

# link shared library
gcc -shared -o premultiply.so \
    asm/premultiply_alpha.o \
    asm/premultiply_avx2.o \
    src/premultiply.o
```

## Testing

```bash
# correctness
python3 tests/correctness.py

# benchmarks
python3 bench/baseline_compare.py
python3 bench/bandwidth_test.py
```

---

## Safety Model

All safety enforcement happens at the C boundary before assembly executes:

```c
int premultiply_safe(uint8_t *buf, int width, int height, int stride) {
    if (!buf)                            return -1;  // null pointer
    if (width <= 0 || height <= 0)       return -1;  // invalid dimensions
    if (stride < width * 4)              return -1;  // bad stride
    if (width > 65535 || height > 65535) return -1;  // overflow guard
    // ... dispatch to ASM
}
```

The assembly contains no safety logic — it runs at full speed on pre-validated data. Overhead of the validation layer is ~10 cycles per call, unmeasurable against millions of cycles of SIMD work.

---

## References

- [Agner Fog — Optimizing Assembly](https://agner.org/optimize/) — primary reference
- [Intel Intrinsics Guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/) — instruction reference
- [Pillow-SIMD (abandoned)](https://github.com/uploadcare/pillow-simd) — prior art
- [x86-64 System V ABI](https://gitlab.com/x86-psABIs/x86-64-ABI) — calling convention spec
- [libjpeg-turbo](https://github.com/libjpeg-turbo/libjpeg-turbo) — reference for production SIMD image code

---

## Author(s)

- **NepThunder** — architecture, assembly implementation

---

*This project is in active early development. Do not use in production until Phase 4 (safety + fuzzing) is complete.*
