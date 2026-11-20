# Compromisso BER × eficiência espectral (alvo: BER do canal = 0.001)

Cadeia de referência: Manchester. SNR = Es/N0. `η` = eficiência espectral nominal (bits/s/Hz, pulso de Nyquist ideal, B = Rs); `η líquida` = η × taxa do código de linha (0.5). Valores 'sim.' vêm de interpolação log-linear das médias simuladas (passo de SNR = 2 dB, precisão ≈ ±0,3 dB).

| Modulação | bits/símbolo | η nominal | η líquida | Es/N0 p/ BER 1e-3, AWGN (teoria / sim.) | Eb/N0 correspondente (teoria) | Es/N0 p/ BER 1e-3, rajadas (teoria / sim.) | Penalidade das rajadas (sim., dB) |
|---|---|---|---|---|---|---|---|
| BPSK | 1 | 1.0 | 0.5 | 6.8 / 6.7 | 6.8 dB | 18.2 / 18.2 | 11.5 |
| QPSK | 2 | 2.0 | 1.0 | 9.8 / 9.7 | 6.8 dB | 21.3 / 21.1 | 11.4 |
| 16-QAM | 4 | 4.0 | 2.0 | 16.5 / 16.5 | 10.5 dB | 27.7 / 27.7 | 11.3 |
