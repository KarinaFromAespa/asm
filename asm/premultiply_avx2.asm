section .text
global premultiply_alpha_avx2

premultiply_alpha_avx2:
    test    rsi, rsi
    jz      .done
    vpxor   ymm5, ymm5, ymm5

.loop:
    cmp     rsi, 8
    jl      .scalar_tail

    vmovdqu ymm0, [rdi]

    vextracti128 xmm2, ymm0, 1
    vpunpcklbw xmm1, xmm0, xmm5
    vpunpckhbw xmm3, xmm0, xmm5
    vpunpcklbw xmm6, xmm2, xmm5
    vpunpckhbw xmm7, xmm2, xmm5

    vpshuflw xmm4, xmm1, 0xFF
    vpshufhw xmm4, xmm4, 0xFF
    vpshuflw xmm8, xmm3, 0xFF
    vpshufhw xmm8, xmm8, 0xFF
    vpshuflw xmm9,  xmm6, 0xFF
    vpshufhw xmm9,  xmm9, 0xFF
    vpshuflw xmm10, xmm7, 0xFF
    vpshufhw xmm10, xmm10, 0xFF

    vpmullw xmm1, xmm1, xmm4
    vpmullw xmm3, xmm3, xmm8
    vpmullw xmm6, xmm6, xmm9
    vpmullw xmm7, xmm7, xmm10

    ; divide by 255: t = x*a+128; (t + (t>>8)) >> 8
    vpaddw  xmm1, xmm1, [rel round128]
    vpsrlw  xmm4, xmm1, 8
    vpaddw  xmm1, xmm1, xmm4
    vpsrlw  xmm1, xmm1, 8

    vpaddw  xmm3, xmm3, [rel round128]
    vpsrlw  xmm4, xmm3, 8
    vpaddw  xmm3, xmm3, xmm4
    vpsrlw  xmm3, xmm3, 8

    vpaddw  xmm6, xmm6, [rel round128]
    vpsrlw  xmm4, xmm6, 8
    vpaddw  xmm6, xmm6, xmm4
    vpsrlw  xmm6, xmm6, 8

    vpaddw  xmm7, xmm7, [rel round128]
    vpsrlw  xmm4, xmm7, 8
    vpaddw  xmm7, xmm7, xmm4
    vpsrlw  xmm7, xmm7, 8

    vpackuswb xmm1, xmm1, xmm3
    vpackuswb xmm6, xmm6, xmm7
    vinserti128 ymm1, ymm1, xmm6, 1

    ; restore original alpha
    vmovdqu ymm2, [rel alpha_mask_avx]
    vpand   ymm3, ymm0, ymm2
    vpandn  ymm2, ymm2, ymm1
    vpor    ymm1, ymm2, ymm3
    vmovdqu [rdi], ymm1

    add     rdi, 32
    sub     rsi, 8
    jmp     .loop

.scalar_tail:
    test    rsi, rsi
    jz      .done

.scalar_loop:
    movzx   eax, byte [rdi+3]
    test    al, al
    jz      .zero_pixel

    movzx   ecx, byte [rdi]
    imul    ecx, eax
    add     ecx, 128
    mov     edx, ecx
    shr     edx, 8
    add     ecx, edx
    shr     ecx, 8
    mov     [rdi], cl

    movzx   ecx, byte [rdi+1]
    imul    ecx, eax
    add     ecx, 128
    mov     edx, ecx
    shr     edx, 8
    add     ecx, edx
    shr     ecx, 8
    mov     [rdi+1], cl

    movzx   ecx, byte [rdi+2]
    imul    ecx, eax
    add     ecx, 128
    mov     edx, ecx
    shr     edx, 8
    add     ecx, edx
    shr     ecx, 8
    mov     [rdi+2], cl
    jmp     .next

.zero_pixel:
    mov     byte [rdi],   0
    mov     byte [rdi+1], 0
    mov     byte [rdi+2], 0

.next:
    add     rdi, 4
    dec     rsi
    jnz     .scalar_loop

.done:
    vzeroupper
    ret

section .data
align 16
round128:      dw 128,128,128,128, 128,128,128,128
align 32
alpha_mask_avx: db 0,0,0,255, 0,0,0,255, 0,0,0,255, 0,0,0,255
                db 0,0,0,255, 0,0,0,255, 0,0,0,255, 0,0,0,255

section .note.GNU-stack noalloc noexec nowrite progbits
