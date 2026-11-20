# Teste de consistência

Mensagem ASCII: 944 bits; sequência aleatória: 100000 bits. `Msg OK` = mensagem ASCII recuperada exatamente.

| Canal | Es/N0 (dB) | Código | Modulação | Erros (msg ASCII) | Msg OK | Erros / BER (100 kbit) | Violações |
|---|---|---|---|---|---|---|---|
| ideal | — | NRZ-L | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | NRZ-L | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | NRZ-L | 16-QAM | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | Manchester | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | Manchester | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | Manchester | 16-QAM | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | AMI | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | AMI | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| ideal | — | AMI | 16-QAM | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | NRZ-L | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | NRZ-L | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | NRZ-L | 16-QAM | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | Manchester | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | Manchester | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | Manchester | 16-QAM | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | AMI | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | AMI | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 30 | AMI | 16-QAM | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 12 | NRZ-L | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 12 | NRZ-L | QPSK | 0 | ✔ | 6 / 6.00e-05 | 0 |
| awgn | 12 | NRZ-L | 16-QAM | 31 | ✘ | 2796 / 2.80e-02 | 0 |
| awgn | 12 | Manchester | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 12 | Manchester | QPSK | 0 | ✔ | 2 / 2.00e-05 | 4 |
| awgn | 12 | Manchester | 16-QAM | 36 | ✘ | 3680 / 3.68e-02 | 5568 |
| awgn | 12 | AMI | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| awgn | 12 | AMI | QPSK | 0 | ✔ | 5 / 5.00e-05 | 11 |
| awgn | 12 | AMI | 16-QAM | 48 | ✘ | 4285 / 4.28e-02 | 6353 |
| burst | 30 | NRZ-L | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| burst | 30 | NRZ-L | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| burst | 30 | NRZ-L | 16-QAM | 0 | ✔ | 35 / 3.50e-04 | 0 |
| burst | 30 | Manchester | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| burst | 30 | Manchester | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| burst | 30 | Manchester | 16-QAM | 0 | ✔ | 12 / 1.20e-04 | 29 |
| burst | 30 | AMI | BPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| burst | 30 | AMI | QPSK | 0 | ✔ | 0 / 0.00e+00 | 0 |
| burst | 30 | AMI | 16-QAM | 0 | ✔ | 36 / 3.60e-04 | 72 |

## Interpretação

* **Canal ideal:** nenhum erro em nenhuma combinação — valida a cadeia ponta a ponta (mapeamento, Gray, embaralhador, preenchimento e decodificadores são inversos exatos).
* **AWGN com Es/N0 = 30 dB:** a BER teórica é desprezível (< 1e-15 até em 16-QAM): esperam-se 0 erros. Qualquer erro aqui indicaria *bug*, não ruído.
* **AWGN com Es/N0 = 12 dB:** divergências **esperadas**. 16-QAM tem BER teórica ≈ 3e-2 por bit (o ruído ultrapassa a distância mínima entre pontos) e a mensagem de 944 bits sai corrompida; QPSK tem BER teórica ≈ 3e-5 (alguns erros isolados em 100 kbit, mas a mensagem curta costuma sair limpa); BPSK (BER teórica ≈ 1e-8) não erra.
* **Rajadas com Es/N0 = 30 dB:** durante a rajada o SNR efetivo cai 15 dB (para 15 dB). BPSK/QPSK seguem sem erros, mas 16-QAM erra nos trechos de rajada (BER ≈ 1e-4 a 4e-4 na sequência de 100 kbit). A mensagem curta de 944 bits pode escapar de uma rajada por sorte; a sequência longa revela a degradação. É efeito do canal, não falha do sistema.
* Códigos de linha com 2 bits por símbolo de linha (Manchester, AMI) dobram o fluxo transmitido; quando o número de bits não é múltiplo de bits/símbolo, o último símbolo é preenchido com zeros e o preenchimento é descartado no receptor.
