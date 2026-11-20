# Roteiro — apresentação (10 min) e vídeo (≤ 5 min)

> Ambos os integrantes precisam falar (item 1 da avaliação). Marque abaixo quem apresenta cada bloco.
> A avaliação pesa a **interpretação dos resultados**, não só a execução: prepare o "porquê" de cada gráfico.

## Apresentação de 10 minutos (sugestão)

| Tempo | Conteúdo | Quem | Material |
|---|---|---|---|
| 0:00–1:00 | Objetivo e cadeia completa (diagrama do README, seção 4) | A | diagrama mermaid |
| 1:00–2:30 | Codificação de linha (Manchester, AMI) **e diferença para correção de erros** | A | fig01 + tabela da seção 5 |
| 2:30–3:30 | Modulações (BPSK/QPSK/16-QAM, Gray, Es=1) e canais (AWGN, rajadas Gilbert-Elliott) | B | fig06 (constelações) |
| 3:30–4:30 | Plano experimental: 16 SNRs, 5 repetições, 10⁶ bits, sementes, IC95 % | B | tabela da seção 7 |
| 4:30–6:00 | Validação: canal ideal = 0 erros; simulação × teoria (BER × SNR) | B | fig02 |
| 6:00–7:00 | Códigos de linha na BER (razão 1 / 1,33 / 1,5) | A | fig03 (painel inferior) |
| 7:00–8:30 | AWGN × rajadas: penalidade 11,4 dB, erros agrupados, recuperação da mensagem | A | fig04, fig07, fig05 |
| 8:30–9:30 | Tabela de compromisso BER × η e quando usar cada modulação | B | fig08 + tabela |
| 9:30–10:00 | Conclusões e limitações (sem FEC; banda base ideal) | A+B | — |

## Vídeo (≤ 5 min) — demonstração + resultados

1. (0:00–0:30) Estrutura do repositório e `pip install -r requirements.txt`.
2. (0:30–1:30) `python scripts/demo_mensagem.py --modulation 16qam --snr 14` → mostrar mensagem recebida, bits incorretos e caracteres com `^`.
   Repetir com `--channel burst` e comentar o agrupamento dos erros.
3. (1:30–2:15) `python scripts/teste_consistencia.py` → canal ideal sem erros.
4. (2:15–3:00) `python scripts/executar_experimentos.py --quick` (ou mostrar `results/raw/config.json`) e explicar a reprodutibilidade.
5. (3:00–4:30) Passar por fig02, fig04, fig05 e a tabela de compromisso com as conclusões.
6. (4:30–5:00) Limitações e próximos passos (FEC + entrelaçamento).

Suba o vídeo no repositório (limite do Git: 100 MB por arquivo; pelo navegador, 25 MB) ou em *Releases*, e coloque o link no README.

## Perguntas prováveis (respostas curtas)

* **Por que QPSK tem o mesmo Eb/N0 do BPSK?** São dois BPSK em quadratura; cada eixo usa metade da energia do símbolo, mas carrega 1 bit; a distância por bit é a mesma.
* **Por que Es/N0 e não Eb/N0 no eixo?** Para comparar com a *mesma potência e a mesma banda*; mostramos Eb/N0 na fig02 (direita).
* **Manchester reduz a BER?** Não. Detecta erros (chips iguais) mas a BER da mensagem é igual à do canal; ele custa o dobro de símbolos. Seu valor é sincronismo e ausência de DC.
* **Por que Manchester em 16-QAM deu ×1,33?** O Gray dá proteção diferente aos 2 bits de cada eixo; o decisor pega o 2º chip, que cai no bit menos protegido.
* **Por que AMI deu ×1,5?** Cada pulso são 2 bits no nosso mapeamento; bit 0 erra se qualquer um dos 2 bits inverter.
* **Para que o embaralhador?** Sem ele, Manchester/AMI deixam a constelação não equiprovável (média ≠ 0, Es ≠ 1) e o SNR nominal deixa de valer (`results/ablacao_scrambler.md`).
* **Por que as rajadas custam ~11 dB?** Com 5 % do tempo em rajada (SNR −15 dB), a BER dentro da rajada domina a média; atingir 10⁻³ exige que a BER na rajada caia a ~2·10⁻², ou seja, ~15 dB acima disso no fundo.
* **Por que o QPSK recupera mais mensagens que o BPSK sob rajadas em 12–16 dB?** A mensagem ocupa metade dos símbolos; a chance de nenhuma rajada atingi-la é ≈ 35 % contra ≈ 13 %.
* **O que falta?** FEC + entrelaçamento, sincronismo real, filtros/ISI, desvanecimento, decisão suave.
