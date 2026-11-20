#!/usr/bin/env python3
"""Plano experimental completo (fatorial) -> results/raw/*.csv + config.json.

Fatores: código de linha (3) x modulação (3) x canal (2) x SNR (>= 8 valores) x repetições (>= 5).
Para cada ponto: n_bits de mensagem aleatórios (padrão 1.000.000; o trabalho exige >= 100.000) + ensaios com a mensagem ASCII.

Reprodutibilidade: todas as sementes derivam de --seed; os bits de mensagem dependem só de
(seed, repetição) — mesmos dados em todas as configurações (comparação pareada) — e o ruído
depende de (seed, repetição, código, modulação, canal, SNR).

Uso:  python scripts/executar_experimentos.py [--quick]
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from commdigital.channel import DEFAULT_BURST  # noqa: E402
from commdigital.line_coding import LINE_CODES  # noqa: E402
from commdigital.metrics import char_errors, error_clustering, spectral_efficiency  # noqa: E402
from commdigital.modulation import MODULATIONS  # noqa: E402
from commdigital.pipeline import LinkConfig, simulate_link  # noqa: E402
from commdigital.source import DEFAULT_MESSAGE, random_bits, text_to_bits  # noqa: E402

LC_NAMES = list(LINE_CODES)
MOD_NAMES = list(MODULATIONS)
CH_NAMES = ["awgn", "burst"]


def run_combo(task):
    """Executa todas as (SNR x repetições) de uma combinação (código, modulação, canal)."""
    lc, mod, ch, p = task
    li, mi, ci = LC_NAMES.index(lc), MOD_NAMES.index(mod), CH_NAMES.index(ch)
    bps = MODULATIONS[mod].bits_per_symbol
    eff = spectral_efficiency(mod, lc)
    msg_bits = text_to_bits(DEFAULT_MESSAGE)
    msg_stream = np.tile(msg_bits, p["msg_trials"])
    rows, msg_rows = [], []
    for rep in range(p["reps"]):
        info = random_bits(p["n_bits"], np.random.default_rng([p["seed"], rep, 0]))
        for si, snr in enumerate(p["snrs"]):
            cfg = LinkConfig(line_code=lc, modulation=mod, channel=ch, snr_db=float(snr),
                             burst_duty=p["burst_duty"], burst_len=p["burst_len"], burst_extra_db=p["burst_extra_db"])
            # --- ensaio principal: bits aleatórios ---
            rng = np.random.default_rng([p["seed"], rep, 1, li, mi, ci, si])
            r = simulate_link(info, cfg, rng)
            clus = error_clustering(np.flatnonzero(r.stream != r.rx_stream))
            rows.append(dict(
                line_code=lc, modulation=mod, channel=ch, snr_db=float(snr), rep=rep,
                n_info_bits=info.size, n_stream_bits=r.stream.size, n_symbols=r.tx_symbols.size,
                err_raw=r.errors_raw, ber_raw=r.ber_raw, err_msg=r.errors_msg, ber_msg=r.ber_msg,
                violations=r.violations,
                burst_symbol_frac=float(r.burst_mask.mean()) if r.burst_mask is not None else 0.0,
                err_cluster_frac=clus, bits_per_symbol=bps,
                eta_nominal=eff["nominal"], eta_liquida=eff["liquida"],
                ebn0_tx_db=float(snr) - 10 * np.log10(bps),
            ))
            # --- ensaios com a mensagem ASCII (taxa de recuperação) ---
            rng = np.random.default_rng([p["seed"], rep, 2, li, mi, ci, si])
            rm = simulate_link(msg_stream, cfg, rng)
            tx = msg_stream.reshape(p["msg_trials"], -1)
            rx = rm.rx_info_bits.reshape(p["msg_trials"], -1)
            bad_bits = (tx != rx)
            ok = ~bad_bits.any(axis=1)
            cerr = np.mean([char_errors(tx[t], rx[t]).mean() for t in range(p["msg_trials"])])
            msg_rows.append(dict(
                line_code=lc, modulation=mod, channel=ch, snr_db=float(snr), rep=rep,
                trials=p["msg_trials"], msg_bits=msg_bits.size, n_exact=int(ok.sum()),
                exact_rate=float(ok.mean()), char_err_rate=float(cerr), msg_ber=float(bad_bits.mean()),
            ))
    return rows, msg_rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-bits", type=int, default=1_000_000, help="bits de mensagem por ensaio (mínimo do trabalho: 100000)")
    ap.add_argument("--reps", type=int, default=5, help="repetições aleatórias (>= 5)")
    ap.add_argument("--snr-min", type=float, default=0.0)
    ap.add_argument("--snr-max", type=float, default=30.0)
    ap.add_argument("--snr-step", type=float, default=2.0)
    ap.add_argument("--msg-trials", type=int, default=100, help="transmissões da mensagem ASCII por ponto")
    ap.add_argument("--seed", type=int, default=20261119)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "raw")
    ap.add_argument("--quick", action="store_true", help="teste rápido (NÃO atende aos mínimos do trabalho)")
    a = ap.parse_args()
    if a.quick:
        a.n_bits, a.reps, a.snr_step, a.msg_trials = 20_000, 2, 6.0, 20

    snrs = np.arange(a.snr_min, a.snr_max + 1e-9, a.snr_step)
    params = dict(n_bits=a.n_bits, reps=a.reps, snrs=[float(s) for s in snrs], msg_trials=a.msg_trials,
                  seed=a.seed, burst_duty=DEFAULT_BURST["duty"], burst_len=DEFAULT_BURST["mean_len"],
                  burst_extra_db=DEFAULT_BURST["extra_db"])
    tasks = [(lc, m, ch, params) for lc in LC_NAMES for m in MOD_NAMES for ch in CH_NAMES]
    print(f"{len(tasks)} combinações x {len(snrs)} SNRs x {a.reps} repetições; {a.n_bits} bits/ensaio")

    t0 = time.time()
    all_rows, all_msg = [], []
    if a.workers > 1:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            results = list(ex.map(run_combo, tasks))
    else:
        results = []
        for i, t in enumerate(tasks, 1):
            results.append(run_combo(t))
            print(f"  [{i:2d}/{len(tasks)}] {t[0]:10s} {t[1]:6s} {t[2]:5s}  ({time.time() - t0:5.1f}s)", flush=True)
    for rows, msg_rows in results:
        all_rows += rows
        all_msg += msg_rows

    a.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_rows).to_csv(a.out / "ber_runs.csv", index=False)
    pd.DataFrame(all_msg).to_csv(a.out / "mensagem_runs.csv", index=False)
    config = dict(
        gerado_em=datetime.now().isoformat(timespec="seconds"), duracao_s=round(time.time() - t0, 1),
        parametros=params, mensagem_ascii=DEFAULT_MESSAGE, codigos_de_linha=LC_NAMES, modulacoes=MOD_NAMES,
        canais=CH_NAMES, definicao_snr="Es/N0 (dB) do ruido de fundo, Es=1",
        quick=a.quick, python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        pandas=pd.__version__,
    )
    (a.out / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: {len(all_rows)} ensaios -> {a.out}  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
