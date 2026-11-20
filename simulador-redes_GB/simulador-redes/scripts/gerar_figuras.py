#!/usr/bin/env python3
"""Gera figuras e tabelas a partir de results/raw/*.csv (reprodutível, sem simular canal, exceto fig. 6-7 ilustrativas).

Saídas em results/figures/ e results/*.md|csv:
  fig01_formas_de_onda        códigos de linha NRZ-L, Manchester, AMI
  fig02_ber_awgn              BER x SNR (AWGN) das 3 modulações + teoria + IC95%  (Es/N0 e Eb/N0)
  fig03_codigos_de_linha      BER de mensagem x SNR por código de linha
  fig04_awgn_vs_rajadas       AWGN x rajadas (simulado e teórico)
  fig05_recuperacao_mensagem  taxa de recuperação exata da mensagem ASCII
  fig06_constelacoes          constelações antes/depois do canal (AWGN e rajadas)
  fig07_erros_no_tempo        posição dos erros: AWGN x rajadas
  fig08_compromisso           Eb/N0 necessário x eficiência espectral (+ limite de Shannon)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from commdigital import theory  # noqa: E402
from commdigital.line_coding import LINE_CODES  # noqa: E402
from commdigital.modulation import MODULATIONS, get_modulation  # noqa: E402
from commdigital.pipeline import LinkConfig, simulate_link  # noqa: E402
from commdigital.source import random_bits  # noqa: E402

RAW = ROOT / "results" / "raw"
FIG = ROOT / "results" / "figures"
OUT = ROOT / "results"
FIG.mkdir(parents=True, exist_ok=True)

MOD_STYLE = {"bpsk": ("#1f77b4", "o"), "qpsk": ("#ff7f0e", "s"), "16qam": ("#2ca02c", "^")}
LC_STYLE = {"nrz": ("#7f7f7f", "o"), "manchester": ("#9467bd", "s"), "ami": ("#d62728", "^")}
MOD_LABEL = {k: v.label for k, v in MODULATIONS.items()}
LC_LABEL = {k: v.label for k, v in LINE_CODES.items()}
REF_LC = "manchester"      # cadeia de referência para comparar modulações
TARGET_BER = 1e-3

plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 160, "axes.grid": True, "grid.alpha": 0.3,
                     "font.size": 10, "legend.fontsize": 8.5})

cfg = json.loads((RAW / "config.json").read_text(encoding="utf-8"))
P = cfg["parametros"]
DUTY, EXTRA = P["burst_duty"], P["burst_extra_db"]
ber_df = pd.read_csv(RAW / "ber_runs.csv")
msg_df = pd.read_csv(RAW / "mensagem_runs.csv")
SNRS = np.array(P["snrs"])
REPS = P["reps"]


def aggregate(df: pd.DataFrame, value: str, by: list[str]) -> pd.DataFrame:
    out = df.groupby(by)[value].agg(["mean", "std", "count", "min", "max"]).reset_index()
    tcrit = stats.t.ppf(0.975, np.maximum(out["count"] - 1, 1))
    out["ci95"] = tcrit * out["std"].fillna(0) / np.sqrt(out["count"])
    return out


def sel(agg, **kw):
    m = np.ones(len(agg), dtype=bool)
    for k, v in kw.items():
        m &= (agg[k] == v).to_numpy()
    return agg[m].sort_values("snr_db")


def floor_for(n_bits_total: float) -> float:
    return 1.0 / n_bits_total


def plot_ber(ax, a, x, color, marker, label, floor, ls="-"):
    """Média ± IC95% (t de Student, n repetições). Pontos sem erro aparecem como 'v' no limite de medição."""
    mean, ci = a["mean"].to_numpy(), a["ci95"].to_numpy()
    nz = mean > 0
    lo = np.maximum(mean - ci, floor * 0.3)
    ax.errorbar(x[nz], mean[nz], yerr=[(mean - lo)[nz], ci[nz]], color=color, marker=marker, ms=4.5, lw=1.3,
                ls=ls, capsize=2.5, label=label, zorder=3)
    if (~nz).any():
        ax.plot(x[~nz], np.full((~nz).sum(), floor), ls="none", marker="v", mfc="none", color=color, ms=6, zorder=3)


def finish_ber_ax(ax, floor, xlabel, ylabel="BER", ymax=0.7):
    ax.set_yscale("log")
    ax.axhline(floor, color="k", ls=":", lw=0.8)
    ax.text(ax.get_xlim()[1] - 0.3, floor * 1.25, "limite de medição (1 erro)", fontsize=7, va="bottom", ha="right")
    ax.set_ylim(floor / 3, ymax)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


# ------------------------------------------------------------------ fig 1: formas de onda
def fig_waveforms():
    bits = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1, 1], dtype=np.uint8)
    fig, axes = plt.subplots(3, 1, figsize=(8, 5.2), sharex=True)
    for ax, (name, lc) in zip(axes, LINE_CODES.items()):
        lv = lc.levels(bits)
        t = np.arange(lv.size + 1) / lc.slots_per_bit
        ax.step(t, np.append(lv, lv[-1]), where="post", color=LC_STYLE[name][0], lw=2)
        ax.set_ylim(-1.5, 1.5)
        ax.set_yticks([-1, 0, 1])
        ax.set_ylabel(lc.label)
        for k in range(bits.size + 1):
            ax.axvline(k, color="k", lw=0.5, alpha=0.3)
    for k, b in enumerate(bits):
        axes[0].text(k + 0.5, 1.2, str(b), ha="center", fontsize=11, fontweight="bold")
    axes[-1].set_xlabel("tempo (períodos de bit)")
    fig.suptitle("Formas de onda dos códigos de linha (convenção Manchester: 1 = baixo→alto)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig01_formas_de_onda.png")
    plt.close(fig)


# ------------------------------------------------------------------ fig 2: BER x SNR (AWGN)
def fig_ber_awgn(agg_raw):
    n_total = P["n_bits"] * REPS * 2  # Manchester transmite 2 bits por bit de mensagem
    floor = floor_for(n_total)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    xs = np.linspace(SNRS.min(), SNRS.max(), 400)
    for ax, mode in zip(axes, ("esn0", "ebn0")):
        for m in MODULATIONS:
            col, mk = MOD_STYLE[m]
            a = sel(agg_raw, line_code=REF_LC, modulation=m, channel="awgn")
            shift = 0.0 if mode == "esn0" else 10 * np.log10(MODULATIONS[m].bits_per_symbol)
            plot_ber(ax, a, a["snr_db"].to_numpy() - shift, col, mk, f"{MOD_LABEL[m]} (simulado)", floor)
            ax.plot(xs - shift, theory.ber_awgn(m, xs), "--", color=col, lw=1, alpha=0.8)
        ax.plot([], [], "k--", lw=1, label="teoria (AWGN)")
        if mode == "esn0":
            ax.set_xlim(SNRS.min() - 0.5, SNRS.max() + 0.5)
        else:
            ax.set_xlim(-3, 26)
        finish_ber_ax(ax, floor, "SNR = Es/N0 (dB)" if mode == "esn0" else "Eb/N0 por bit transmitido (dB)")
        ax.set_title("BER × SNR por símbolo (Es/N0)" if mode == "esn0" else "mesmos dados em Eb/N0", fontsize=10)
        ax.legend(loc="upper right")
    nb = f"{P['n_bits']:,}".replace(",", ".")
    fig.suptitle(f"Canal AWGN — {REPS} repetições × {nb} bits de mensagem por ponto "
                 f"(barras: IC95%, t de Student) — código de linha: {LC_LABEL[REF_LC]}", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig02_ber_awgn.png")
    plt.close(fig)


# ------------------------------------------------------------------ fig 3: códigos de linha
def fig_line_codes(agg_msg):
    n_total = P["n_bits"] * REPS
    floor = floor_for(n_total)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), gridspec_kw={"height_ratios": [1.5, 1]})
    awgn = ber_df[ber_df.channel == "awgn"]
    for k, m in enumerate(MODULATIONS):
        ax, axr = axes[0, k], axes[1, k]
        lo_snr = {"bpsk": (0, 12), "qpsk": (0, 14), "16qam": (4, 28)}[m]
        xs = np.linspace(*lo_snr, 300)
        for lc in LINE_CODES:
            col, mk = LC_STYLE[lc]
            a = sel(agg_msg, line_code=lc, modulation=m, channel="awgn")
            a = a[(a.snr_db >= lo_snr[0]) & (a.snr_db <= lo_snr[1])]
            plot_ber(ax, a, a["snr_db"].to_numpy(), col, mk, f"{LC_LABEL[lc]} (sim.)", floor)
            t = theory.ber_message(lc, m, xs)
            if t is not None:
                ax.plot(xs, t, "--", color=col, lw=1, alpha=0.8)
            # razão BER_mensagem / BER_canal (só onde há >= 300 erros no canal => razão estável)
            g = awgn[(awgn.line_code == lc) & (awgn.modulation == m)].groupby("snr_db").agg(
                em=("err_msg", "sum"), ni=("n_info_bits", "sum"), er=("err_raw", "sum"), ns=("n_stream_bits", "sum")).reset_index()
            g = g[(g.er >= 300) & (g.snr_db >= lo_snr[0]) & (g.snr_db <= lo_snr[1])]
            axr.plot(g.snr_db, (g.em / g.ni) / (g.er / g.ns), color=col, marker=mk, ms=4.5, lw=1.2, label=LC_LABEL[lc])
            tm = theory.ber_message(lc, m, xs)
            if tm is not None:
                axr.plot(xs, tm / theory.ber_awgn(m, xs), "--", color=col, lw=1, alpha=0.8)
        ax.plot([], [], "k--", lw=1, label="teoria")
        ax.set_xlim(lo_snr[0] - 0.5, lo_snr[1] + 0.5)
        finish_ber_ax(ax, floor, "SNR = Es/N0 (dB)", "BER da mensagem" if k == 0 else "")
        ax.set_title(MOD_LABEL[m], fontsize=10)
        ax.legend(loc="upper right")
        axr.set_xlim(lo_snr[0] - 0.5, lo_snr[1] + 0.5)
        axr.set_ylim(0.8, 2.0)
        axr.set_xlabel("SNR = Es/N0 (dB)")
        axr.set_ylabel("BER mensagem / BER canal" if k == 0 else "")
        axr.legend(loc="upper right", ncol=3, fontsize=8)
    fig.suptitle("Código de linha no enlace (AWGN). Em cima: BER ponta a ponta. Embaixo: razão entre a BER da mensagem "
                 "e a BER do canal (pontilhado: teoria; sem teoria p/ AMI em 16-QAM).", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig03_codigos_de_linha.png")
    plt.close(fig)


# ------------------------------------------------------------------ fig 4: AWGN x rajadas
def fig_awgn_vs_burst(agg_raw):
    n_total = P["n_bits"] * REPS * 2
    floor = floor_for(n_total)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
    xs = np.linspace(SNRS.min(), SNRS.max(), 400)
    for ax, m in zip(axes, MODULATIONS):
        col, _ = MOD_STYLE[m]
        a1 = sel(agg_raw, line_code=REF_LC, modulation=m, channel="awgn")
        a2 = sel(agg_raw, line_code=REF_LC, modulation=m, channel="burst")
        plot_ber(ax, a1, a1["snr_db"].to_numpy(), col, "o", "AWGN (sim.)", floor)
        plot_ber(ax, a2, a2["snr_db"].to_numpy(), "#d62728", "x", "AWGN + rajadas (sim.)", floor)
        ax.plot(xs, theory.ber_awgn(m, xs), "--", color=col, lw=1, label="AWGN (teoria)")
        ax.plot(xs, theory.ber_burst(m, xs, DUTY, EXTRA), ":", color="#d62728", lw=1.4, label="rajadas (teoria)")
        ax.set_xlim(SNRS.min() - 0.5, SNRS.max() + 0.5)
        finish_ber_ax(ax, floor, "SNR de fundo Es/N0 (dB)", "BER do canal" if m == "bpsk" else "")
        ax.set_title(MOD_LABEL[m], fontsize=10)
        ax.legend(loc="upper right")
    fig.suptitle(f"AWGN × rajadas (duty {DUTY:.0%}, duração média {P['burst_len']:.0f} símbolos, "
                 f"+{EXTRA:g} dB de ruído na rajada)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig04_awgn_vs_rajadas.png")
    plt.close(fig)


# ------------------------------------------------------------------ fig 5: recuperação da mensagem
def fig_message_recovery(agg_ok):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), sharey=True)
    for ax, ch, title in zip(axes, ("awgn", "burst"), ("AWGN", "AWGN + rajadas")):
        for m in MODULATIONS:
            col, mk = MOD_STYLE[m]
            a = sel(agg_ok, line_code=REF_LC, modulation=m, channel=ch)
            ax.errorbar(a["snr_db"], a["mean"], yerr=a["ci95"], color=col, marker=mk, ms=4.5, capsize=2.5,
                        lw=1.3, label=MOD_LABEL[m])
        ax.set_xlabel("SNR de fundo Es/N0 (dB)")
        ax.set_title(title, fontsize=10)
        ax.set_ylim(-0.03, 1.05)
        ax.legend(loc="lower right")
    axes[0].set_ylabel(f"fração recuperada sem erro (de {P['msg_trials']} envios)")
    fig.suptitle(f"Recuperação da mensagem ASCII (118 caracteres, {LC_LABEL[REF_LC]}) — média ± IC95% em {REPS} repetições",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig05_recuperacao_mensagem.png")
    plt.close(fig)


# ------------------------------------------------------------------ fig 6: constelações
def fig_constellations(snr_db=14.0, n_bits_demo=24_000):
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.4))
    for j, m in enumerate(MODULATIONS):
        mod = get_modulation(m)
        info = random_bits(n_bits_demo, np.random.default_rng(11))
        pts, _ = mod.constellation()
        for i, ch in enumerate(("awgn", "burst")):
            r = simulate_link(info, LinkConfig("nrz", m, ch, snr_db), np.random.default_rng(100 + j))
            ax = axes[i, j]
            rx = r.rx_symbols
            if r.burst_mask is None:
                ax.scatter(rx.real, rx.imag, s=2, alpha=0.35, color="#1f77b4", label="recebido")
            else:
                ax.scatter(rx.real[~r.burst_mask], rx.imag[~r.burst_mask], s=2, alpha=0.35, color="#1f77b4",
                           label="recebido (fora da rajada)")
                ax.scatter(rx.real[r.burst_mask], rx.imag[r.burst_mask], s=4, alpha=0.7, color="#d62728",
                           label="recebido (na rajada)")
            ax.scatter(pts.real, pts.imag, s=40, color="k", marker="+", linewidths=1.6, label="transmitido", zorder=5)
            lim = 1.9 if m == "16qam" else 1.7
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_aspect("equal")
            ax.set_xlabel("I")
            ax.set_ylabel("Q")
            ax.set_title(f"{MOD_LABEL[m]} — {'AWGN' if ch == 'awgn' else 'rajadas'} (BER {r.ber_raw:.1e})", fontsize=10)
            if j == 0:
                ax.legend(loc="upper left", fontsize=7, markerscale=3)
    fig.suptitle(f"Constelações antes (+) e depois do canal — Es/N0 de fundo = {snr_db:g} dB", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig06_constelacoes.png")
    plt.close(fig)


# ------------------------------------------------------------------ fig 7: posição dos erros
def fig_error_timeline(snr_db=14.0, n_bits_demo=100_000):
    fig, axes = plt.subplots(2, 3, figsize=(13, 4.6), sharex=True)
    for j, m in enumerate(MODULATIONS):
        info = random_bits(n_bits_demo, np.random.default_rng(5))
        for i, ch in enumerate(("awgn", "burst")):
            r = simulate_link(info, LinkConfig("nrz", m, ch, snr_db), np.random.default_rng(200 + j))
            pos = np.flatnonzero(r.stream != r.rx_stream)
            from commdigital.metrics import error_clustering
            ax = axes[i, j]
            ax.eventplot(pos, colors="#d62728" if ch == "burst" else "#1f77b4", linelengths=0.9, linewidths=0.6)
            ax.set_yticks([])
            ax.set_xlim(0, n_bits_demo)
            ax.set_title(f"{MOD_LABEL[m]} — {'AWGN' if ch == 'awgn' else 'rajadas'}: {pos.size} erros, "
                         f"agrupados {100 * error_clustering(pos):.0f}%", fontsize=9)
            if i == 1:
                ax.set_xlabel("índice do bit transmitido")
    fig.suptitle(f"Onde ocorrem os erros? (Es/N0 de fundo = {snr_db:g} dB; 'agrupados' = erros com outro erro a ≤ 8 bits)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "fig07_erros_no_tempo.png")
    plt.close(fig)


# ------------------------------------------------------------------ cruzamento de BER alvo
def crossing(x: np.ndarray, y: np.ndarray, target: float, floor: float) -> float:
    y = np.maximum(y, floor)
    for i in range(len(x) - 1):
        if y[i] > target >= y[i + 1]:
            f = (np.log10(y[i]) - np.log10(target)) / (np.log10(y[i]) - np.log10(y[i + 1]))
            return float(x[i] + f * (x[i + 1] - x[i]))
    return float("nan")


# ------------------------------------------------------------------ tabela de compromisso + fig 8
def tradeoff(agg_raw):
    floor = floor_for(P["n_bits"] * REPS * 2) / 10
    rows = []
    for m in MODULATIONS:
        bps = MODULATIONS[m].bits_per_symbol
        a1 = sel(agg_raw, line_code=REF_LC, modulation=m, channel="awgn")
        a2 = sel(agg_raw, line_code=REF_LC, modulation=m, channel="burst")
        sim_awgn = crossing(a1.snr_db.to_numpy(), a1["mean"].to_numpy(), TARGET_BER, floor)
        sim_burst = crossing(a2.snr_db.to_numpy(), a2["mean"].to_numpy(), TARGET_BER, floor)
        th_awgn = theory.required_esn0_db(m, TARGET_BER)
        th_burst = theory.required_esn0_db(m, TARGET_BER, DUTY, EXTRA)
        eta = bps
        rows.append(dict(mod=m, bps=bps, eta=eta, eta_net=eta * LINE_CODES[REF_LC].rate,
                         th_awgn=th_awgn, sim_awgn=sim_awgn, th_burst=th_burst, sim_burst=sim_burst,
                         eb_th=th_awgn - 10 * np.log10(bps), eb_sim=sim_awgn - 10 * np.log10(bps),
                         eb_burst_th=th_burst - 10 * np.log10(bps), eb_burst_sim=sim_burst - 10 * np.log10(bps)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "compromisso_ber_eficiencia.csv", index=False)

    def f(x):
        return "n/a (> %g dB)" % SNRS.max() if np.isnan(x) else f"{x:.1f}"

    lines = [f"# Compromisso BER × eficiência espectral (alvo: BER do canal = {TARGET_BER:g})", "",
             f"Cadeia de referência: {LC_LABEL[REF_LC]}. SNR = Es/N0. `η` = eficiência espectral nominal "
             f"(bits/s/Hz, pulso de Nyquist ideal, B = Rs); `η líquida` = η × taxa do código de linha "
             f"({LINE_CODES[REF_LC].rate:g}). Valores 'sim.' vêm de interpolação log-linear das médias simuladas "
             f"(passo de SNR = {P['snrs'][1] - P['snrs'][0]:g} dB, precisão ≈ ±0,3 dB).", "",
             "| Modulação | bits/símbolo | η nominal | η líquida | Es/N0 p/ BER 1e-3, AWGN (teoria / sim.) | "
             "Eb/N0 correspondente (teoria) | Es/N0 p/ BER 1e-3, rajadas (teoria / sim.) | Penalidade das rajadas (sim., dB) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        pen = r["sim_burst"] - r["sim_awgn"]
        lines.append(f"| {MOD_LABEL[r['mod']]} | {r['bps']} | {r['eta']:.1f} | {r['eta_net']:.1f} | "
                     f"{r['th_awgn']:.1f} / {f(r['sim_awgn'])} | {r['eb_th']:.1f} dB | "
                     f"{r['th_burst']:.1f} / {f(r['sim_burst'])} | {'—' if np.isnan(pen) else f'{pen:.1f}'} |")
    (OUT / "tabela_compromisso.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- figura 8
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    e = np.linspace(0.5, 4.6, 200)
    ax.plot(e, theory.shannon_ebn0_db(e), "k-", lw=1.2, label="limite de Shannon (AWGN)")
    for r in rows:
        col, mk = MOD_STYLE[r["mod"]]
        ax.scatter(r["eta"], r["eb_th"], marker=mk, s=70, facecolor="none", edgecolor=col, lw=1.6, zorder=4)
        ax.scatter(r["eta"], r["eb_sim"], marker="x", s=55, color=col, zorder=5)
        if not np.isnan(r["eb_burst_sim"]):
            ax.scatter(r["eta"], r["eb_burst_sim"], marker=mk, s=70, color=col, alpha=0.5, zorder=4)
        ax.annotate(MOD_LABEL[r["mod"]], (r["eta"], r["eb_th"]), textcoords="offset points", xytext=(6, -14), fontsize=9)
    ax.scatter([], [], marker="o", s=70, facecolor="none", edgecolor="gray", label="AWGN (teoria)")
    ax.scatter([], [], marker="x", s=55, color="gray", label="AWGN (simulado)")
    ax.scatter([], [], marker="o", s=70, color="gray", alpha=0.5, label="rajadas (simulado)")
    ax.set_xlabel("eficiência espectral nominal η (bits/s/Hz)")
    ax.set_ylabel(f"Eb/N0 necessário para BER = {TARGET_BER:g} (dB)")
    ax.set_title("Compromisso: mais bits/s/Hz exige mais energia por bit", fontsize=10)
    ax.legend(loc="center", bbox_to_anchor=(0.62, 0.72), fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig08_compromisso.png")
    plt.close(fig)
    return lines


def ber_table(agg_raw, agg_msg_ok):
    """BER média ± IC95% em SNRs selecionados + taxa de recuperação."""
    pick = [s for s in (4, 8, 12, 16, 20, 24, 30) if s in SNRS]
    nb = f"{P['n_bits']:,}".replace(",", ".")
    lines = [f"# BER por SNR (média ± IC95% em {REPS} repetições; {nb} bits de mensagem por ensaio)", "",
             f"BER do canal (fluxo transmitido) com {LC_LABEL[REF_LC]}. `rec.` = fração de mensagens ASCII recuperadas sem erro.", "",
             "| Es/N0 (dB) | Modulação | BER AWGN | rec. AWGN | BER rajadas | rec. rajadas |", "|---|---|---|---|---|---|"]
    for s in pick:
        for m in MODULATIONS:
            cells = []
            for ch in ("awgn", "burst"):
                a = sel(agg_raw, line_code=REF_LC, modulation=m, channel=ch)
                a = a[a.snr_db == s].iloc[0]
                k = sel(agg_msg_ok, line_code=REF_LC, modulation=m, channel=ch)
                k = k[k.snr_db == s].iloc[0]
                ber_txt = "0 (< %.0e)" % (1 / (P["n_bits"] * REPS * 2)) if a["mean"] == 0 else f"{a['mean']:.2e} ± {a['ci95']:.1e}"
                cells += [ber_txt, f"{100 * k['mean']:.0f}%"]
            lines.append(f"| {s:g} | {MOD_LABEL[m]} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    (OUT / "tabela_ber_por_snr.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    agg_raw = aggregate(ber_df, "ber_raw", ["line_code", "modulation", "channel", "snr_db"])
    agg_msg = aggregate(ber_df, "ber_msg", ["line_code", "modulation", "channel", "snr_db"])
    agg_ok = aggregate(msg_df, "exact_rate", ["line_code", "modulation", "channel", "snr_db"])
    agg_cl = aggregate(ber_df, "err_cluster_frac", ["line_code", "modulation", "channel", "snr_db"])
    # tabelas agregadas (úteis para conferir os gráficos)
    agg_raw.assign(metric="ber_raw").to_csv(OUT / "agregado_ber_raw.csv", index=False)
    agg_msg.assign(metric="ber_msg").to_csv(OUT / "agregado_ber_msg.csv", index=False)
    agg_ok.assign(metric="exact_rate").to_csv(OUT / "agregado_recuperacao_mensagem.csv", index=False)

    fig_waveforms()
    fig_ber_awgn(agg_raw)
    fig_line_codes(agg_msg)
    fig_awgn_vs_burst(agg_raw)
    fig_message_recovery(agg_ok)
    fig_constellations()
    fig_error_timeline()
    tradeoff(agg_raw)
    ber_table(agg_raw, agg_ok)
    print("Figuras e tabelas geradas em", FIG, "e", OUT)


if __name__ == "__main__":
    main()
