"""Modulações digitais em banda base equivalente (símbolos complexos I + jQ).

Hipóteses (padrão em simulações de camada física):
* energia média por símbolo normalizada: Es = 1;
* pulso de Nyquist ideal + filtro casado -> 1 amostra por símbolo sem ISI;
* largura de banda ocupada B = Rs (taxa de símbolos), logo
  eficiência espectral nominal = log2(M) bits/s/Hz.

Mapeamento Gray (vizinhos na constelação diferem em 1 bit).
Demodulação: decisão por distância mínima (detector ML para AWGN), eixo a eixo.
"""
from __future__ import annotations

import numpy as np


class Modulator:
    name = ""
    label = ""
    bits_per_symbol = 1

    @property
    def M(self) -> int:
        return 2 ** self.bits_per_symbol

    def modulate(self, bits: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def demodulate(self, symbols: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def constellation(self) -> tuple[np.ndarray, np.ndarray]:
        """Todos os pontos e seus rótulos de bits (MSB primeiro)."""
        k = self.bits_per_symbol
        idx = np.arange(2 ** k)
        bits = ((idx[:, None] >> np.arange(k - 1, -1, -1)) & 1).astype(np.uint8)
        return self.modulate(bits.reshape(-1)), bits


class BPSK(Modulator):
    name = "bpsk"
    label = "BPSK"
    bits_per_symbol = 1

    def modulate(self, bits):
        return (1.0 - 2.0 * np.asarray(bits, dtype=np.float64)).astype(np.complex128)

    def demodulate(self, symbols):
        return (symbols.real < 0).astype(np.uint8)


class QPSK(Modulator):
    name = "qpsk"
    label = "QPSK"
    bits_per_symbol = 2

    def modulate(self, bits):
        b = np.asarray(bits, dtype=np.float64).reshape(-1, 2)
        return ((1.0 - 2.0 * b[:, 0]) + 1j * (1.0 - 2.0 * b[:, 1])) / np.sqrt(2.0)

    def demodulate(self, symbols):
        out = np.empty((symbols.size, 2), dtype=np.uint8)
        out[:, 0] = symbols.real < 0
        out[:, 1] = symbols.imag < 0
        return out.reshape(-1)


class QAM16(Modulator):
    """16-QAM quadrado, Gray por eixo: 00->-3, 01->-1, 11->+1, 10->+3 (normalizado por sqrt(10))."""

    name = "16qam"
    label = "16-QAM"
    bits_per_symbol = 4
    _NORM = np.sqrt(10.0)

    @staticmethod
    def _level(hi: np.ndarray, lo: np.ndarray) -> np.ndarray:
        g = 2 * hi + lo
        k = g ^ (g >> 1)          # Gray -> índice binário (0..3)
        return 2 * k - 3          # -3, -1, +1, +3

    def modulate(self, bits):
        b = np.asarray(bits, dtype=np.int64).reshape(-1, 4)
        i = self._level(b[:, 0], b[:, 1])
        q = self._level(b[:, 2], b[:, 3])
        return (i + 1j * q) / self._NORM

    def _axis_bits(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        a = x * self._NORM
        k = np.clip(np.rint((a + 3.0) / 2.0), 0, 3).astype(np.int64)
        g = k ^ (k >> 1)          # índice binário -> Gray
        return g >> 1, g & 1

    def demodulate(self, symbols):
        out = np.empty((symbols.size, 4), dtype=np.uint8)
        out[:, 0], out[:, 1] = self._axis_bits(symbols.real)
        out[:, 2], out[:, 3] = self._axis_bits(symbols.imag)
        return out.reshape(-1)


MODULATIONS = {m.name: m for m in (BPSK(), QPSK(), QAM16())}


def get_modulation(name: str) -> Modulator:
    try:
        return MODULATIONS[name.lower()]
    except KeyError as exc:
        raise ValueError(f"Modulação desconhecida: {name!r}. Opções: {list(MODULATIONS)}") from exc
