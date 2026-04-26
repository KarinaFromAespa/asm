section .text
global premultiply_alpha_sse4

premultiply_alpha_sse4:
    test    rsi, rsi
    jz      .done
    pxor    xmm5, xmm5

.loop:
    cmp     rsi, 4
    jl      .scalar_tail

    movdqu  xmm0, [rdi]

    movdqa  xmm1, xmm0
    punpcklbw xmm1, xmm5
    movdqa  xmm2, xmm0
    punpckhbw xmm2, xmm5

    pshuflw xmm3, xmm1, 0xFF
    pshufhw xmm3, xmm3, 0xFF
    pshuflw xmm4, xmm2, 0xFF
    pshufhw xmm4, xmm4, 0xFF

    pmullw  xmm1, xmm3
    pmullw  xmm2, xmm4

    ; divide by 255: t = x*a+128; (t + (t>>8)) >> 8
    paddw   xmm1, [rel round128]
    movdqa  xmm3, xmm1
    psrlw   xmm3, 8
    paddw   xmm1, xmm3
    psrlw   xmm1, 8

    paddw   xmm2, [rel round128]
    movdqa  xmm4, xmm2
    psrlw   xmm4, 8
    paddw   xmm2, xmm4
    psrlw   xmm2, 8

    packuswb xmm1, xmm2

    ; restore original alpha
    movdqa  xmm2, [rel alpha_mask]
    movdqa  xmm3, xmm0
    pand    xmm3, xmm2
    pandn   xmm2, xmm1
    por     xmm2, xmm3
    movdqu  [rdi], xmm2

    add     rdi, 16
    sub     rsi, 4
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
    jmp     .next_scalar

.zero_pixel:
    mov     byte [rdi],   0
    mov     byte [rdi+1], 0
    mov     byte [rdi+2], 0

.next_scalar:
    add     rdi, 4
    dec     rsi
    jnz     .scalar_loop

.done:
    vzeroupper
    ret

section .data
align 16
alpha_mask: db 0,0,0,255, 0,0,0,255, 0,0,0,255, 0,0,0,255
round128:   dw 128,128,128,128, 128,128,128,128

section .note.GNU-stack noalloc noexec nowrite progbits
