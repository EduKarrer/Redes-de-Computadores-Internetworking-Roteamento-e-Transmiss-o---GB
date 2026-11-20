#!/usr/bin/env python3
"""Ablação: o que acontece sem o embaralhador? (Manchester/AMI + modulações de ordem superior)

Gera results/ablacao_scrambler.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from commdigital import theory  # noqa: E402
from commdigital.line_coding import LINE_CODES  # noqa: E402
from commdigital.pipeline import LinkConfig, simulate_link  # noqa: E402
from commdigital.source import random_bits  # noqa: E402

SNR = {"bpsk": 6.0, "qpsk": 9.0, "16qam": 15.0}


def main():
    rng = np.random.default_rng(7)
    info = random_bits(400_000, rng)
    rows = ["# Ablação do embaralhador", "",
            "Mesma SNR, com e sem embaralhador. `Média(s)` = média dos símbolos transmitidos (deveria ser 0); "
            "`Es` = energia média por símbolo (deveria ser 1). BER teórica = AWGN com bits equiprováveis.", "",
            "| Código | Modulação | Es/N0 (dB) | Embaralhador | Média(s) | Es | BER do canal | BER teórica |",
            "|---|---|---|---|---|---|---|---|"]
    for lc in ("nrz", "manchester", "ami"):
        for m, snr in SNR.items():
            teo = float(theory.ber_awgn(m, snr))
            for scr in (True, False):
                r = simulate_link(info, LinkConfig(lc, m, "awgn", snr, scramble=scr), rng)
                mean = r.tx_symbols.mean()
                es = float(np.mean(np.abs(r.tx_symbols) ** 2))
                rows.append(f"| {LINE_CODES[lc].label} | {m.upper()} | {snr:g} | {'sim' if scr else 'não'} | "
                            f"{mean.real:+.2f}{mean.imag:+.2f}j | {es:.2f} | {r.ber_raw:.2e} | {teo:.2e} |")
    rows += ["", "**Leitura.** Com o embaralhador, a média dos símbolos é ~0, Es = 1 e a BER coincide com a "
             "teoria em todas as combinações. Sem ele, a estrutura do código de linha faz certos pontos da "
             "constelação aparecerem mais que outros: Manchester e AMI deslocam a média dos símbolos (componente "
             "DC na constelação, p.ex. +0,32+0,32j em 16-QAM e +0,50 em BPSK com AMI) e, no caso AMI + 16-QAM, "
             "a energia média sobe para ~1,40 — o SNR real deixa de ser o SNR nominal e a BER medida (3,8e-3) "
             "fica abaixo da teórica (4,5e-3), ou seja, a comparação entre configurações deixa de ser justa. "
             "Em NRZ-L os dados já são equiprováveis e o embaralhador não muda nada."]
    out = ROOT / "results" / "ablacao_scrambler.md"
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
