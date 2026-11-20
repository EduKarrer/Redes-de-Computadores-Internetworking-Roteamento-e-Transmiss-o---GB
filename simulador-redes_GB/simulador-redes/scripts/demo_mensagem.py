#!/usr/bin/env python3
"""Demonstração ponta a ponta com a mensagem ASCII: mostra bits errados e a mensagem recebida.

Exemplos:
  python scripts/demo_mensagem.py --modulation 16qam --snr 14
  python scripts/demo_mensagem.py --line-code ami --modulation qpsk --channel burst --snr 10
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commdigital.line_coding import LINE_CODES, get_line_code  # noqa: E402
from commdigital.metrics import char_errors, spectral_efficiency  # noqa: E402
from commdigital.modulation import MODULATIONS, get_modulation  # noqa: E402
from commdigital.pipeline import LinkConfig, simulate_link  # noqa: E402
from commdigital.source import DEFAULT_MESSAGE, bits_to_string, bits_to_text, text_to_bits  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--message", default=DEFAULT_MESSAGE)
    ap.add_argument("--line-code", default="manchester", choices=list(LINE_CODES))
    ap.add_argument("--modulation", default="qpsk", choices=list(MODULATIONS))
    ap.add_argument("--channel", default="awgn", choices=["ideal", "awgn", "burst"])
    ap.add_argument("--snr", type=float, default=10.0, help="Es/N0 em dB")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    rng = np.random.default_rng(a.seed)
    bits = text_to_bits(a.message)
    cfg = LinkConfig(a.line_code, a.modulation, a.channel, a.snr)
    r = simulate_link(bits, cfg, rng)
    lc, mod = get_line_code(a.line_code), get_modulation(a.modulation)
    eff = spectral_efficiency(a.modulation, a.line_code)
    rx_text = bits_to_text(r.rx_info_bits)

    print("=" * 78)
    print(f"Código de linha: {lc.label} | Modulação: {mod.label} | Canal: {a.channel}"
          + (f" | Es/N0 = {a.snr:.1f} dB" if a.channel != "ideal" else ""))
    print("=" * 78)
    print(f"Mensagem TX ({len(a.message)} caracteres, {bits.size} bits):\n  {a.message}")
    print(f"Bits TX (primeiros 64):         {bits_to_string(bits, 8, 64)}")
    print(f"Fluxo após {lc.label} ({r.stream.size} bits; 64 primeiros):\n  {bits_to_string(r.stream, 8, 64)}")
    print(f"Símbolos {mod.label}: {r.tx_symbols.size} ({mod.bits_per_symbol} bit/símbolo; "
          f"preenchimento: {r.n_pad} bit)")
    if r.burst_mask is not None:
        print(f"Símbolos dentro de rajada: {r.burst_mask.sum()} ({100 * r.burst_mask.mean():.1f}%)")
    print(f"\nMensagem RX:\n  {rx_text}")

    pos = r.error_positions_msg()
    bad_chars = char_errors(bits, r.rx_info_bits)
    marks = "".join("^" if b else " " for b in bad_chars)
    if bad_chars.any():
        print(f"  {marks}")
    print("\nResultado:")
    print(f"  BER do canal (fluxo antes da decodificação de linha): {r.ber_raw:.3e} ({r.errors_raw} erros em {r.stream.size} bits)")
    print(f"  BER da mensagem (ponta a ponta):                      {r.ber_msg:.3e} ({pos.size} erros em {bits.size} bits)")
    print(f"  Caracteres errados: {int(bad_chars.sum())} de {bad_chars.size}")
    print(f"  Violações de código de linha detectadas: {r.violations}")
    if pos.size:
        shown = ", ".join(f"{p} (car. {p // 8}, bit {p % 8})" for p in pos[:20])
        print(f"  Posições dos bits incorretos (índice na mensagem): {shown}" + (" ..." if pos.size > 20 else ""))
    else:
        print("  Nenhum bit incorreto: mensagem recuperada sem erros.")
    print(f"  Eficiência espectral nominal: {eff['nominal']:.2f} bit/s/Hz | líquida (após {lc.label}): {eff['liquida']:.2f} bit/s/Hz")


if __name__ == "__main__":
    main()
