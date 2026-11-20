"""Métricas: BER, posições de erro, agrupamento de erros, caracteres errados, eficiência espectral."""
from __future__ import annotations

import numpy as np

from .line_coding import get_line_code
from .modulation import get_modulation


def count_errors(tx: np.ndarray, rx: np.ndarray) -> int:
    return int(np.count_nonzero(np.asarray(tx) != np.asarray(rx)))


def ber(tx: np.ndarray, rx: np.ndarray) -> float:
    n = len(tx)
    return count_errors(tx, rx) / n if n else 0.0


def error_positions(tx: np.ndarray, rx: np.ndarray) -> np.ndarray:
    return np.flatnonzero(np.asarray(tx) != np.asarray(rx))


def error_clustering(positions: np.ndarray, window: int = 8) -> float:
    """Fração dos erros que têm outro erro a até `window` bits de distância.

    Erros independentes (AWGN, BER baixo) -> valor pequeno; erros em rajada -> próximo de 1.
    """
    positions = np.asarray(positions)
    if positions.size < 2:
        return 0.0
    close = np.diff(positions) <= window
    near = np.zeros(positions.size, dtype=bool)
    near[1:] |= close
    near[:-1] |= close
    return float(near.mean())


def char_errors(tx_bits: np.ndarray, rx_bits: np.ndarray) -> np.ndarray:
    """Vetor booleano por caractere (True = caractere com ao menos 1 bit errado)."""
    n = (min(len(tx_bits), len(rx_bits)) // 8) * 8
    diff = (np.asarray(tx_bits[:n]) != np.asarray(rx_bits[:n])).reshape(-1, 8)
    return diff.any(axis=1)


def spectral_efficiency(modulation: str, line_code: str = "nrz", rolloff: float = 0.0) -> dict:
    """Eficiência espectral em bits/s/Hz.

    nominal  = log2(M) / (1 + rolloff)   (rolloff = 0 -> pulso de Nyquist ideal, B = Rs)
    liquida  = nominal * taxa do código de linha (bits de MENSAGEM por bit transmitido)
    """
    mod = get_modulation(modulation)
    lc = get_line_code(line_code)
    nominal = mod.bits_per_symbol / (1.0 + rolloff)
    return {"nominal": nominal, "liquida": nominal * lc.rate}
