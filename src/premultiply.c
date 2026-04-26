#include <stdint.h>
#include <cpuid.h>

extern void premultiply_alpha_sse4(uint8_t *pixels, int count);
extern void premultiply_alpha_avx2(uint8_t *pixels, int count);

static int has_avx2() {
    unsigned int eax, ebx, ecx, edx;
    if (__get_cpuid_max(0, 0) < 7) return 0;
    __cpuid_count(7, 0, eax, ebx, ecx, edx);
    return (ebx >> 5) & 1;
}

int premultiply_safe(uint8_t *buf, int width, int height, int stride) {
    if (!buf)                        return -1;
    if (width <= 0 || height <= 0)   return -1;
    if (stride < width * 4)          return -1;
    if (width > 65535 || height > 65535) return -1;

    int use_avx2 = has_avx2();

    for (int row = 0; row < height; row++) {
        if (use_avx2)
            premultiply_alpha_avx2(buf + (row * stride), width);
        else
            premultiply_alpha_sse4(buf + (row * stride), width);
    }
    return 0;
}
