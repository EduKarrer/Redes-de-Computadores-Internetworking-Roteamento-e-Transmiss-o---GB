# Ablação do embaralhador

Mesma SNR, com e sem embaralhador. `Média(s)` = média dos símbolos transmitidos (deveria ser 0); `Es` = energia média por símbolo (deveria ser 1). BER teórica = AWGN com bits equiprováveis.

| Código | Modulação | Es/N0 (dB) | Embaralhador | Média(s) | Es | BER do canal | BER teórica |
|---|---|---|---|---|---|---|---|
| NRZ-L | BPSK | 6 | sim | +0.00+0.00j | 1.00 | 2.37e-03 | 2.39e-03 |
| NRZ-L | BPSK | 6 | não | -0.00+0.00j | 1.00 | 2.36e-03 | 2.39e-03 |
| NRZ-L | QPSK | 9 | sim | +0.00+0.00j | 1.00 | 2.48e-03 | 2.41e-03 |
| NRZ-L | QPSK | 9 | não | +0.00-0.00j | 1.00 | 2.35e-03 | 2.41e-03 |
| NRZ-L | 16QAM | 15 | sim | -0.00-0.00j | 1.00 | 4.59e-03 | 4.47e-03 |
| NRZ-L | 16QAM | 15 | não | -0.00-0.00j | 1.00 | 4.66e-03 | 4.47e-03 |
| Manchester | BPSK | 6 | sim | +0.00+0.00j | 1.00 | 2.40e-03 | 2.39e-03 |
| Manchester | BPSK | 6 | não | +0.00+0.00j | 1.00 | 2.49e-03 | 2.39e-03 |
| Manchester | QPSK | 9 | sim | +0.00+0.00j | 1.00 | 2.54e-03 | 2.41e-03 |
| Manchester | QPSK | 9 | não | +0.00-0.00j | 1.00 | 2.37e-03 | 2.41e-03 |
| Manchester | 16QAM | 15 | sim | -0.00-0.00j | 1.00 | 4.52e-03 | 4.47e-03 |
| Manchester | 16QAM | 15 | não | +0.32+0.32j | 1.00 | 4.56e-03 | 4.47e-03 |
| AMI | BPSK | 6 | sim | +0.00+0.00j | 1.00 | 2.47e-03 | 2.39e-03 |
| AMI | BPSK | 6 | não | +0.50+0.00j | 1.00 | 2.38e-03 | 2.39e-03 |
| AMI | QPSK | 9 | sim | -0.00+0.00j | 1.00 | 2.50e-03 | 2.41e-03 |
| AMI | QPSK | 9 | não | +0.35+0.35j | 1.00 | 2.34e-03 | 2.41e-03 |
| AMI | 16QAM | 15 | sim | +0.00+0.00j | 1.00 | 4.45e-03 | 4.47e-03 |
| AMI | 16QAM | 15 | não | -0.32-0.31j | 1.40 | 3.81e-03 | 4.47e-03 |

**Leitura.** Com o embaralhador, a média dos símbolos é ~0, Es = 1 e a BER coincide com a teoria em todas as combinações. Sem ele, a estrutura do código de linha faz certos pontos da constelação aparecerem mais que outros: Manchester e AMI deslocam a média dos símbolos (componente DC na constelação, p.ex. +0,32+0,32j em 16-QAM e +0,50 em BPSK com AMI) e, no caso AMI + 16-QAM, a energia média sobe para ~1,40 — o SNR real deixa de ser o SNR nominal e a BER medida (3,8e-3) fica abaixo da teórica (4,5e-3), ou seja, a comparação entre configurações deixa de ser justa. Em NRZ-L os dados já são equiprováveis e o embaralhador não muda nada.
