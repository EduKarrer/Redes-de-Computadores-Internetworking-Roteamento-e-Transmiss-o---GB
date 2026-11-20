"""Modelos de canal (banda base equivalente, Es = 1).

SNR = Es/N0 (relação sinal-ruído por símbolo), em dB. Com Es = 1,
N0 = 1/SNR e o ruído complexo tem variância N0/2 por dimensão (I e Q).

Cenários:
* ``ideal``  — sem ruído (teste de consistência);
* ``awgn``   — ruído gaussiano branco aditivo;
* ``burst``  — AWGN de fundo + rajadas de interferência modeladas por uma
  cadeia de Markov de dois estados (Gilbert-Elliott). No estado RUIM a potência
  de ruído é multiplicada por 10^(extra_db/10), isto é, o SNR cai ``extra_db`` dB.
  Parâmetros: fração de tempo em rajada (duty), duração média da rajada (em
  símbolos) e ``extra_db``. O eixo de SNR dos gráficos refere-se ao ruído de fundo.
"""
from __future__ import annotations

import numpy as np

DEFAULT_BURST = dict(duty=0.05, mean_len=50.0, extra_db=15.0)


def _complex_noise(n: int, sigma: float | np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return sigma * (rng.standard_normal(n) + 1j * rng.standard_normal(n))


def sigma_per_dim(snr_db: float) -> float:
    snr = 10.0 ** (snr_db / 10.0)
    return float(np.sqrt(1.0 / (2.0 * snr)))


def awgn(symbols: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    return symbols + _complex_noise(symbols.size, sigma_per_dim(snr_db), rng)


def burst_mask(n: int, duty: float, mean_len: float, rng: np.random.Generator) -> np.ndarray:
    """Máscara booleana (True = símbolo dentro de uma rajada) — Markov de 2 estados."""
    if not 0.0 < duty < 1.0:
        raise ValueError("duty deve estar em (0, 1)")
    p_bg = 1.0 / mean_len                       # P(ruim -> bom)
    p_gb = p_bg * duty / (1.0 - duty)           # P(bom -> ruim), fração estacionária = duty
    mask = np.zeros(n, dtype=bool)
    bad = bool(rng.random() < duty)             # estado inicial ~ distribuição estacionária
    pos = 0
    while pos < n:
        length = int(rng.geometric(p_bg if bad else p_gb))
        if bad:
            mask[pos:pos + length] = True
        pos += length
        bad = not bad
    return mask


def burst_awgn(symbols: np.ndarray, snr_db: float, rng: np.random.Generator,
               duty: float, mean_len: float, extra_db: float) -> tuple[np.ndarray, np.ndarray]:
    mask = burst_mask(symbols.size, duty, mean_len, rng)
    scale = np.where(mask, 10.0 ** (extra_db / 20.0), 1.0)
    noise = _complex_noise(symbols.size, sigma_per_dim(snr_db) * scale, rng)
    return symbols + noise, mask


def apply_channel(symbols: np.ndarray, kind: str, snr_db: float, rng: np.random.Generator,
                  duty: float = DEFAULT_BURST["duty"], mean_len: float = DEFAULT_BURST["mean_len"],
                  extra_db: float = DEFAULT_BURST["extra_db"]) -> tuple[np.ndarray, np.ndarray | None]:
    """Aplica o canal; devolve (símbolos recebidos, máscara de rajada ou None)."""
    kind = kind.lower()
    if kind == "ideal":
        return symbols.copy(), None
    if kind == "awgn":
        return awgn(symbols, snr_db, rng), None
    if kind == "burst":
        return burst_awgn(symbols, snr_db, rng, duty, mean_len, extra_db)
    raise ValueError(f"Canal desconhecido: {kind!r}. Opções: ideal, awgn, burst")
