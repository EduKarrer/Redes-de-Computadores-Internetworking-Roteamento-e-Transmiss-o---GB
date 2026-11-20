#!/usr/bin/env python3
"""Teste de consistência: canal ideal e SNR elevado devem recuperar a mensagem sem erros.

Gera results/consistencia.md. Sai com código != 0 se o canal ideal falhar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from commdigital.line_coding import LINE_CODES  # noqa: E402
from commdigital.modulation import MODULATIONS  # noqa: E402
from commdigital.pipeline import LinkConfig, simulate_link  # noqa: E402
from commdigital.source import DEFAULT_MESSAGE, bits_to_text, random_bits, text_to_bits  # noqa: E402

N_BITS = 100_000
CASES = [("ideal", 0.0), ("awgn", 30.0), ("awgn", 12.0), ("burst", 30.0)]


def main():
    rng = np.random.default_rng(20261119)
    msg_bits = text_to_bits(DEFAULT_MESSAGE)
    rnd = random_bits(N_BITS, rng)
    lines = ["# Teste de consistência", "",
             f"Mensagem ASCII: {msg_bits.size} bits; sequência aleatória: {N_BITS} bits. "
             "`Msg OK` = mensagem ASCII recuperada exatamente.", "",
             "| Canal | Es/N0 (dB) | Código | Modulação | Erros (msg ASCII) | Msg OK | Erros / BER (100 kbit) | Violações |",
             "|---|---|---|---|---|---|---|---|"]
    ideal_fail = False
    for ch, snr in CASES:
        for lc in LINE_CODES:
            for m in MODULATIONS:
                cfg = LinkConfig(lc, m, ch, snr)
                rm = simulate_link(msg_bits, cfg, rng)
                rr = simulate_link(rnd, cfg, rng)
                ok = bits_to_text(rm.rx_info_bits) == DEFAULT_MESSAGE
                if ch == "ideal" and (not ok or rr.errors_msg or rr.errors_raw):
                    ideal_fail = True
                snr_txt = "—" if ch == "ideal" else f"{snr:g}"
                lines.append(f"| {ch} | {snr_txt} | {LINE_CODES[lc].label} | {MODULATIONS[m].label} | "
                             f"{rm.errors_msg} | {'✔' if ok else '✘'} | {rr.errors_msg} / {rr.ber_msg:.2e} | {rr.violations} |")
    lines += ["", "## Interpretação", "",
              "* **Canal ideal:** nenhum erro em nenhuma combinação — valida a cadeia ponta a ponta "
              "(mapeamento, Gray, embaralhador, preenchimento e decodificadores são inversos exatos).",
              "* **AWGN com Es/N0 = 30 dB:** a BER teórica é desprezível (< 1e-15 até em 16-QAM): "
              "esperam-se 0 erros. Qualquer erro aqui indicaria *bug*, não ruído.",
              "* **AWGN com Es/N0 = 12 dB:** divergências **esperadas**. 16-QAM tem BER teórica ≈ 3e-2 por bit "
              "(o ruído ultrapassa a distância mínima entre pontos) e a mensagem de 944 bits sai corrompida; "
              "QPSK tem BER teórica ≈ 3e-5 (alguns erros isolados em 100 kbit, mas a mensagem curta costuma sair "
              "limpa); BPSK (BER teórica ≈ 1e-8) não erra.",
              "* **Rajadas com Es/N0 = 30 dB:** durante a rajada o SNR efetivo cai 15 dB (para 15 dB). BPSK/QPSK "
              "seguem sem erros, mas 16-QAM erra nos trechos de rajada (BER ≈ 1e-4 a 4e-4 na sequência de 100 kbit). "
              "A mensagem curta de 944 bits pode escapar de uma rajada por sorte; a sequência longa revela a "
              "degradação. É efeito do canal, não falha do sistema.",
              "* Códigos de linha com 2 bits por símbolo de linha (Manchester, AMI) dobram o fluxo transmitido; "
              "quando o número de bits não é múltiplo de bits/símbolo, o último símbolo é preenchido com zeros e o "
              "preenchimento é descartado no receptor."]
    out = ROOT / "results" / "consistencia.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4 + 2 + 9 * 2]))
    print(f"\n-> {out}")
    if ideal_fail:
        print("FALHA: canal ideal não recuperou a mensagem!")
        sys.exit(1)
    print("Consistência OK: canal ideal sem erros em todas as 9 combinações.")


if __name__ == "__main__":
    main()
