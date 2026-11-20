#!/usr/bin/env python3
"""Demonstração automática para gravar vídeo SEM narração.

O script mostra legendas na tela, "digita" cada comando e executa o simulador, com pausas para leitura.
Basta iniciar a gravação de tela e rodar:

    python scripts/demo_video.py                # ~4 min com as pausas padrão
    python scripts/demo_video.py --pausa 1.5    # pausas 50% maiores (leitura mais calma)
    python scripts/demo_video.py --abrir-figuras  # ao final, abre os gráficos no navegador, um a um

Dica: terminal em tela cheia, fonte >= 16 pt e janela limpa (rode `cls`/`clear` antes).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

P = 1.0  # multiplicador de pausas


def pausa(seg: float):
    time.sleep(seg * P)


def legenda(titulo: str, linhas: list[str] | None = None, seg: float = 3.5):
    larg = 78
    print("\n" + "=" * larg)
    print(f"  {titulo}")
    for ln in linhas or []:
        print(f"  {ln}")
    print("=" * larg + "\n", flush=True)
    pausa(seg)


def digitar(cmd: str, atraso: float = 0.035):
    sys.stdout.write("$ ")
    for ch in cmd:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(atraso * (1 if P > 0 else 0))
    print(flush=True)
    pausa(0.8)


def executar(args: list[str], espera: float = 7.0):
    shown = "python " + " ".join(a.replace(str(ROOT) + os.sep, "") for a in args)
    digitar(shown)
    subprocess.run([PY, *args], cwd=ROOT, env=ENV, check=False)
    pausa(espera)


def arvore():
    legenda("1/7  O projeto", ["Pacote do simulador, scripts, testes e resultados reprodutíveis"], 3)
    itens = [
        "commdigital/        fonte, codificação de linha, embaralhador, modulação, canal, métricas, teoria",
        "scripts/            demo, consistência, experimentos, figuras",
        "tests/              44 testes automatizados",
        "results/raw/        resultados brutos (CSV) + config.json",
        "results/figures/    gráficos BER x SNR, constelações, rajadas...",
        "README.md           arquitetura, parâmetros, resultados",
    ]
    for it in itens:
        print("  " + it, flush=True)
        pausa(0.9)
    pausa(3)


def main():
    global P
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pausa", type=float, default=1.0, help="multiplicador das pausas (0 = sem pausas, p/ teste)")
    ap.add_argument("--abrir-figuras", action="store_true", help="abre os gráficos principais no navegador ao final")
    a = ap.parse_args()
    P = a.pausa

    legenda("SIMULADOR DE TRANSMISSÃO DIGITAL",
            ["Redes de Computadores - UNISINOS - Trabalho II",
             "ASCII -> codificação de linha -> modulação -> canal -> demodulação -> mensagem"], 5)
    arvore()

    legenda("2/7  Canal ideal: a mensagem tem que chegar idêntica",
            ["Manchester + QPSK, sem ruído"])
    executar(["scripts/demo_mensagem.py", "--channel", "ideal"], 8)

    legenda("3/7  AWGN com 16-QAM a 14 dB: aparecem erros",
            ["Os caracteres errados são marcados com ^ e os bits incorretos são listados"])
    executar(["scripts/demo_mensagem.py", "--modulation", "16qam", "--snr", "14", "--seed", "3"], 10)

    legenda("4/7  Canal com rajadas (AMI + QPSK, 12 dB)",
            ["Os erros se concentram em trechos; o código de linha detecta violações"])
    executar(["scripts/demo_mensagem.py", "--line-code", "ami", "--modulation", "qpsk",
              "--channel", "burst", "--snr", "12", "--seed", "4"], 10)

    legenda("5/7  Teste de consistência",
            ["Canal ideal e SNR alto: 0 erros em todas as combinações de código x modulação"])
    digitar("python scripts/teste_consistencia.py")
    r = subprocess.run([PY, "scripts/teste_consistencia.py"], cwd=ROOT, env=ENV, capture_output=True, text=True)
    saida = r.stdout.strip().splitlines()
    for ln in saida[-3:]:
        print(ln, flush=True)
    pausa(6)

    legenda("6/7  Testes automatizados", ["Cadeia, modulações, canais e BER simulada x teoria"])
    executar(["-m", "pytest", "-q"], 5)

    legenda("7/7  Reprodutibilidade",
            ["Parâmetros, sementes e versões registrados em results/raw/config.json"])
    cfg = ROOT / "results" / "raw" / "config.json"
    if cfg.exists():
        import json
        c = json.loads(cfg.read_text(encoding="utf-8"))
        p = c["parametros"]
        digitar("resumo de results/raw/config.json")
        print(f"  bits por ensaio : {p['n_bits']:,}".replace(",", "."))
        print(f"  repetições      : {p['reps']}")
        print(f"  SNR (dB)        : {p['snrs'][0]:g} a {p['snrs'][-1]:g}  ({len(p['snrs'])} valores)")
        print(f"  semente base    : {p['seed']}")
        print(f"  rajadas         : duty {p['burst_duty']:.0%}, {p['burst_len']:g} símbolos, +{p['burst_extra_db']:g} dB")
        print(f"  Python/NumPy    : {c['python']} / {c['numpy']}", flush=True)
        pausa(7)

    legenda("Resultados completos: ./run_all.sh  (~2 min)  ->  results/figures/ e results/*.md", None, 4)

    if a.abrir_figuras:
        figs = ["fig02_ber_awgn", "fig03_codigos_de_linha", "fig04_awgn_vs_rajadas",
                "fig05_recuperacao_mensagem", "fig08_compromisso"]
        for f in figs:
            path = ROOT / "results" / "figures" / f"{f}.png"
            if path.exists():
                webbrowser.open(path.as_uri())
                pausa(10)


if __name__ == "__main__":
    main()
