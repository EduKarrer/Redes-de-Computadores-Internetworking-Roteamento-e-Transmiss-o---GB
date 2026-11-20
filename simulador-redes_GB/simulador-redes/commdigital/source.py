"""Fonte de informação: mensagem ASCII <-> bits."""
from __future__ import annotations

import numpy as np

DEFAULT_MESSAGE = (
    "Redes de Computadores - UNISINOS - Trabalho II: "
    "codificacao de linha e modulacao digital. Prof. Cristiano Bonato Both."
)


def text_to_bits(text: str) -> np.ndarray:
    """Converte texto ASCII em bits (8 bits por caractere, MSB primeiro)."""
    try:
        data = text.encode("ascii")
    except UnicodeEncodeError as exc:  # acentos não existem em ASCII
        raise ValueError("A mensagem deve conter apenas caracteres ASCII (sem acentos).") from exc
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_text(bits, placeholder: str = "?") -> str:
    """Converte bits em texto. Bytes que não são ASCII imprimível viram `placeholder`."""
    bits = np.asarray(bits, dtype=np.uint8)
    n = (bits.size // 8) * 8
    values = np.packbits(bits[:n])
    return "".join(chr(v) if 32 <= v < 127 else placeholder for v in values)


def random_bits(n: int, rng: np.random.Generator) -> np.ndarray:
    """n bits equiprováveis e independentes."""
    return rng.integers(0, 2, size=n, dtype=np.uint8)


def bits_to_string(bits, group: int = 8, limit: int | None = None) -> str:
    """Representação legível: '01010010 01100101 ...'."""
    bits = np.asarray(bits, dtype=np.uint8)
    if limit is not None:
        bits = bits[:limit]
    s = "".join(map(str, bits.tolist()))
    return " ".join(s[i:i + group] for i in range(0, len(s), group))
