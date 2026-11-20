"""Enlace ponta a ponta: bits -> linha -> embaralhador -> modulação -> canal -> demodulação -> bits."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .channel import DEFAULT_BURST, apply_channel
from .line_coding import get_line_code
from .metrics import ber, count_errors, error_positions
from .modulation import get_modulation
from .scrambler import descramble, scramble


@dataclass(frozen=True)
class LinkConfig:
    line_code: str = "manchester"
    modulation: str = "qpsk"
    channel: str = "awgn"            # ideal | awgn | burst
    snr_db: float = 10.0             # Es/N0 do ruído de fundo
    scramble: bool = True
    burst_duty: float = DEFAULT_BURST["duty"]
    burst_len: float = DEFAULT_BURST["mean_len"]
    burst_extra_db: float = DEFAULT_BURST["extra_db"]


@dataclass
class LinkResult:
    cfg: LinkConfig
    info_bits: np.ndarray           # bits de mensagem transmitidos
    rx_info_bits: np.ndarray        # bits de mensagem recuperados
    stream: np.ndarray              # fluxo após codificação de linha (antes do embaralhador)
    rx_stream: np.ndarray           # fluxo recebido (depois do desembaralhador, antes do decodificador de linha)
    tx_symbols: np.ndarray
    rx_symbols: np.ndarray
    burst_mask: np.ndarray | None
    violations: int                 # erros detectados pelo decodificador de linha
    n_pad: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def ber_raw(self) -> float:
        """BER do canal: bits que entram/saem do modulador (antes da decodificação de linha)."""
        return ber(self.stream, self.rx_stream)

    @property
    def ber_msg(self) -> float:
        """BER ponta a ponta: bits da mensagem."""
        return ber(self.info_bits, self.rx_info_bits)

    @property
    def errors_raw(self) -> int:
        return count_errors(self.stream, self.rx_stream)

    @property
    def errors_msg(self) -> int:
        return count_errors(self.info_bits, self.rx_info_bits)

    def error_positions_msg(self) -> np.ndarray:
        return error_positions(self.info_bits, self.rx_info_bits)


def simulate_link(info_bits: np.ndarray, cfg: LinkConfig, rng: np.random.Generator) -> LinkResult:
    lc = get_line_code(cfg.line_code)
    mod = get_modulation(cfg.modulation)
    info_bits = np.asarray(info_bits, dtype=np.uint8)

    # --- transmissor ---
    stream = lc.encode(info_bits)
    tx_stream = scramble(stream) if cfg.scramble else stream
    bps = mod.bits_per_symbol
    n_pad = (-tx_stream.size) % bps                     # completa o último símbolo
    padded = np.concatenate([tx_stream, np.zeros(n_pad, dtype=np.uint8)]) if n_pad else tx_stream
    tx_sym = mod.modulate(padded)

    # --- canal ---
    rx_sym, mask = apply_channel(tx_sym, cfg.channel, cfg.snr_db, rng,
                                 duty=cfg.burst_duty, mean_len=cfg.burst_len, extra_db=cfg.burst_extra_db)

    # --- receptor ---
    rx_padded = mod.demodulate(rx_sym)
    rx_scr = rx_padded[: tx_stream.size]                # descarta o preenchimento
    rx_stream = descramble(rx_scr) if cfg.scramble else rx_scr
    rx_info, violations = lc.decode(rx_stream)

    return LinkResult(cfg=cfg, info_bits=info_bits, rx_info_bits=rx_info, stream=stream, rx_stream=rx_stream,
                      tx_symbols=tx_sym, rx_symbols=rx_sym, burst_mask=mask, violations=violations, n_pad=n_pad)
