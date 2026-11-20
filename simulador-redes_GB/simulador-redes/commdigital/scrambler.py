"""Embaralhador (scrambler) aditivo síncrono — PRBS-15 (x^15 + x^14 + 1).

Por que existe? Códigos de linha como Manchester e AMI produzem fluxos com
estrutura (p.ex. Manchester só gera pares 01/10). Em modulações de ordem
superior (16-QAM) isso faria alguns pontos da constelação serem usados mais do
que outros, deslocando a média e a energia média do sinal e invalidando o
SNR nominal. O embaralhador "branqueia" o fluxo antes do modulador. É uma
operação XOR com uma sequência conhecida: aplicar duas vezes devolve o original
e NÃO propaga erros (um bit errado no canal = um bit errado depois).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

PRBS15_PERIOD = 2 ** 15 - 1


@lru_cache(maxsize=1)
def prbs15_period() -> np.ndarray:
    reg = 0x7FFF
    out = np.empty(PRBS15_PERIOD, dtype=np.uint8)
    for i in range(PRBS15_PERIOD):
        new = ((reg >> 14) ^ (reg >> 13)) & 1
        out[i] = new
        reg = ((reg << 1) | new) & 0x7FFF
    out.setflags(write=False)
    return out


def scramble(bits) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.uint8)
    return bits ^ np.resize(prbs15_period(), bits.size)


descramble = scramble  # XOR é involutivo
