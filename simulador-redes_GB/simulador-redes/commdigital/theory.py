"""Curvas teóricas de BER (AWGN, detecção coerente, mapeamento Gray) — SNR = Es/N0.

* BPSK : Pb = Q( sqrt(2 Es/N0) )
* QPSK : Pb = Q( sqrt(Es/N0) )            (cada eixo é um BPSK com metade da energia)
* 16-QAM (exato por posição de bit, 4-PAM Gray por eixo, níveis ±1,±3):
    s = sqrt(5/SNR)
    P(b0, bit de sinal)       = 1/2 [ Q(3/s) + Q(1/s) ]
    P(b1, bit interno/externo) = 1/2 [ 2 Q(1/s) + Q(3/s) - Q(5/s) ]
  (o bit b1 é menos protegido que b0: "proteção desigual" do Gray em QAM)

Cenário de rajadas: BER = (1-duty) BER(SNR) + duty BER(SNR - extra_db), pois dentro de
cada estado o canal é AWGN.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.special import erfc

from .line_coding import get_line_code


def qfunc(x):
    return 0.5 * erfc(np.asarray(x, dtype=float) / np.sqrt(2.0))


def ber_by_bit(modulation: str, esn0_db) -> np.ndarray:
    """BER de cada posição de bit dentro do símbolo; shape (bits_por_simbolo, *shape(esn0))."""
    snr = 10.0 ** (np.asarray(esn0_db, dtype=float) / 10.0)
    m = modulation.lower()
    if m == "bpsk":
        return np.stack([qfunc(np.sqrt(2.0 * snr))])
    if m == "qpsk":
        p = qfunc(np.sqrt(snr))
        return np.stack([p, p])
    if m == "16qam":
        s = np.sqrt(5.0 / snr)
        pb0 = 0.5 * (qfunc(3.0 / s) + qfunc(1.0 / s))
        pb1 = 0.5 * (2.0 * qfunc(1.0 / s) + qfunc(3.0 / s) - qfunc(5.0 / s))
        return np.stack([pb0, pb1, pb0, pb1])
    raise ValueError(f"Modulação desconhecida: {modulation!r}")


def ber_awgn(modulation: str, esn0_db) -> np.ndarray:
    """BER média por bit transmitido (antes da decodificação de linha)."""
    return ber_by_bit(modulation, esn0_db).mean(axis=0)


def ber_burst(modulation: str, esn0_db, duty: float, extra_db: float) -> np.ndarray:
    esn0_db = np.asarray(esn0_db, dtype=float)
    return (1 - duty) * ber_awgn(modulation, esn0_db) + duty * ber_awgn(modulation, esn0_db - extra_db)


def _ber_message_awgn(line_code: str, modulation: str, esn0_db):
    """BER dos bits de MENSAGEM após decodificação de linha (AWGN, dados equiprováveis).

    Retorna None quando não há expressão fechada simples (AMI em 16-QAM: bits da palavra correlacionados).
    """
    lc = get_line_code(line_code).name
    v = ber_by_bit(modulation, esn0_db)
    bps = v.shape[0]
    if lc == "nrz":
        return v.mean(axis=0)
    if lc == "manchester":
        # decisão pelo 2º chip de cada par; os pares alinham com as posições 0-1 e 2-3 do símbolo
        return v[1::2].mean(axis=0) if bps >= 2 else v.mean(axis=0)
    if lc == "ami":
        if bps == 4:
            return None
        pa = v[0]
        pb = v[1] if bps >= 2 else v[0]
        # bit 0 (palavra 00): erro se qualquer bit inverter; bit 1: erro se o único bit '1' inverter e o outro não
        return 0.5 * (1 - (1 - pa) * (1 - pb)) + 0.25 * (pb * (1 - pa) + pa * (1 - pb))
    raise ValueError(line_code)


def ber_message(line_code: str, modulation: str, esn0_db, duty: float = 0.0, extra_db: float = 0.0):
    f = _ber_message_awgn(line_code, modulation, esn0_db)
    if f is None or duty <= 0:
        return f
    g = _ber_message_awgn(line_code, modulation, np.asarray(esn0_db, dtype=float) - extra_db)
    return (1 - duty) * f + duty * g


def required_esn0_db(modulation: str, target_ber: float, duty: float = 0.0, extra_db: float = 0.0) -> float:
    """Es/N0 (dB) necessário para atingir `target_ber` (teoria)."""
    fn = (lambda x: float(ber_awgn(modulation, x))) if duty <= 0 else \
         (lambda x: float(ber_burst(modulation, x, duty, extra_db)))
    return brentq(lambda x: fn(x) - target_ber, -20.0, 80.0)


def shannon_ebn0_db(eta) -> np.ndarray:
    """Limite de Shannon: Eb/N0 mínimo (dB) para eficiência espectral eta (bit/s/Hz)."""
    eta = np.asarray(eta, dtype=float)
    return 10.0 * np.log10((2.0 ** eta - 1.0) / eta)
