"""Testes automatizados do simulador. Execute:  python -m pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commdigital import theory  # noqa: E402
from commdigital.channel import awgn, burst_mask  # noqa: E402
from commdigital.line_coding import AMI, LINE_CODES, Manchester  # noqa: E402
from commdigital.metrics import char_errors, error_clustering, spectral_efficiency  # noqa: E402
from commdigital.modulation import MODULATIONS  # noqa: E402
from commdigital.pipeline import LinkConfig, simulate_link  # noqa: E402
from commdigital.scrambler import PRBS15_PERIOD, descramble, prbs15_period, scramble  # noqa: E402
from commdigital.source import DEFAULT_MESSAGE, bits_to_text, random_bits, text_to_bits  # noqa: E402

RNG = lambda s=0: np.random.default_rng(s)  # noqa: E731


# ---------------------------------------------------------------- fonte
def test_ascii_roundtrip():
    bits = text_to_bits(DEFAULT_MESSAGE)
    assert bits.size == 8 * len(DEFAULT_MESSAGE)
    assert bits_to_text(bits) == DEFAULT_MESSAGE


def test_ascii_known_bits():
    assert text_to_bits("A").tolist() == [0, 1, 0, 0, 0, 0, 0, 1]


def test_non_ascii_rejected():
    with pytest.raises(ValueError):
        text_to_bits("codificação")


# ---------------------------------------------------------------- codificação de linha
@pytest.mark.parametrize("name", list(LINE_CODES))
def test_line_code_roundtrip(name):
    lc = LINE_CODES[name]
    bits = random_bits(1001, RNG())
    dec, viol = lc.decode(lc.encode(bits))
    assert np.array_equal(dec, bits) and viol == 0
    assert lc.encode(bits).size == round(bits.size / lc.rate)


def test_manchester_known_pattern():
    # convenção adotada: 1 -> (0,1), 0 -> (1,0)
    assert Manchester().encode(np.array([1, 0, 1], dtype=np.uint8)).tolist() == [0, 1, 1, 0, 0, 1]


def test_manchester_always_has_midbit_transition():
    enc = Manchester().encode(random_bits(500, RNG()))
    assert np.all(enc[0::2] != enc[1::2])


def test_ami_alternating_polarity_and_no_dc():
    bits = np.array([1, 0, 1, 1, 0, 1, 0, 0, 1], dtype=np.uint8)
    lv = AMI.ternary(bits)
    assert lv.tolist() == [1, 0, -1, 1, 0, -1, 0, 0, 1]
    assert abs(int(lv.sum())) <= 1                      # sem componente DC acumulada


def test_ami_detects_bipolar_violation():
    ami = AMI()
    enc = ami.encode(np.array([1, 1], dtype=np.uint8)).copy()   # +1, -1  -> 01 10
    enc[2:4] = [0, 1]                                           # força +1, +1 (violação bipolar)
    _, viol = ami.decode(enc)
    assert viol == 1


def test_manchester_detects_violation():
    enc = Manchester().encode(np.array([1, 0, 1, 1], dtype=np.uint8)).copy()
    enc[1] ^= 1                                                 # chips iguais no 1º bit
    _, viol = Manchester().decode(enc)
    assert viol == 1


# ---------------------------------------------------------------- embaralhador
def test_prbs15_is_maximal_length():
    p = prbs15_period()
    assert p.size == PRBS15_PERIOD and int(p.sum()) == 2 ** 14   # 16384 uns em 32767


def test_scrambler_involution_and_no_error_propagation():
    bits = random_bits(5000, RNG(1))
    assert np.array_equal(descramble(scramble(bits)), bits)
    corrupted = scramble(bits).copy()
    corrupted[100] ^= 1
    assert np.count_nonzero(descramble(corrupted) != bits) == 1


# ---------------------------------------------------------------- modulação
@pytest.mark.parametrize("name", list(MODULATIONS))
def test_modulation_roundtrip_and_unit_energy(name):
    mod = MODULATIONS[name]
    bits = random_bits(mod.bits_per_symbol * 5000, RNG(2))
    sym = mod.modulate(bits)
    assert np.array_equal(mod.demodulate(sym), bits)
    pts, _ = mod.constellation()
    assert np.isclose(np.mean(np.abs(pts) ** 2), 1.0)            # Es = 1
    assert len(np.unique(np.round(pts, 9))) == mod.M


@pytest.mark.parametrize("name", list(MODULATIONS))
def test_gray_mapping_nearest_neighbours_differ_by_one_bit(name):
    mod = MODULATIONS[name]
    pts, labels = mod.constellation()
    d = np.abs(pts[:, None] - pts[None, :])
    np.fill_diagonal(d, np.inf)
    dmin = d.min()
    for i in range(mod.M):
        for j in np.flatnonzero(np.isclose(d[i], dmin)):
            assert np.count_nonzero(labels[i] != labels[j]) == 1


# ---------------------------------------------------------------- canal
def test_awgn_noise_power_matches_snr():
    sym = np.ones(400_000, dtype=complex)
    for snr_db in (0, 7, 13):
        n = awgn(sym, snr_db, RNG(3)) - sym
        assert np.mean(np.abs(n) ** 2) == pytest.approx(10 ** (-snr_db / 10), rel=0.02)


def test_burst_mask_duty_and_mean_length():
    m = burst_mask(2_000_000, duty=0.05, mean_len=50, rng=RNG(4))
    assert m.mean() == pytest.approx(0.05, rel=0.08)
    edges = np.flatnonzero(np.diff(m.astype(int)) == 1)
    ends = np.flatnonzero(np.diff(m.astype(int)) == -1)
    n = min(edges.size, ends.size)
    lengths = ends[:n] - edges[:n] if ends[0] > edges[0] else ends[1:n] - edges[:n - 1]
    assert lengths.mean() == pytest.approx(50, rel=0.1)


# ---------------------------------------------------------------- enlace ponta a ponta
@pytest.mark.parametrize("lc", list(LINE_CODES))
@pytest.mark.parametrize("mod", list(MODULATIONS))
def test_ideal_channel_recovers_message(lc, mod):
    bits = text_to_bits(DEFAULT_MESSAGE)
    r = simulate_link(bits, LinkConfig(lc, mod, "ideal"), RNG(5))
    assert bits_to_text(r.rx_info_bits) == DEFAULT_MESSAGE
    assert r.errors_raw == 0 and r.violations == 0


def test_padding_when_stream_not_multiple_of_bits_per_symbol():
    bits = random_bits(1001, RNG(6))                 # 1001 bits NRZ -> não múltiplo de 4
    r = simulate_link(bits, LinkConfig("nrz", "16qam", "ideal"), RNG(6))
    assert r.n_pad == 3 and np.array_equal(r.rx_info_bits, bits)


# ---------------------------------------------------------------- simulação x teoria
@pytest.mark.parametrize("mod,snr", [("bpsk", 4), ("qpsk", 7), ("16qam", 14)])
def test_simulated_ber_matches_theory_awgn(mod, snr):
    info = random_bits(600_000, RNG(7))
    r = simulate_link(info, LinkConfig("nrz", mod, "awgn", snr), RNG(8))
    assert r.ber_raw == pytest.approx(float(theory.ber_awgn(mod, snr)), rel=0.06)


@pytest.mark.parametrize("mod,snr", [("bpsk", 8), ("qpsk", 12), ("16qam", 20)])
def test_simulated_ber_matches_theory_burst(mod, snr):
    info = random_bits(1_000_000, RNG(9))
    r = simulate_link(info, LinkConfig("nrz", mod, "burst", snr), RNG(10))
    assert r.ber_raw == pytest.approx(float(theory.ber_burst(mod, snr, 0.05, 15.0)), rel=0.2)


@pytest.mark.parametrize("lc,mod,snr", [("manchester", "bpsk", 4), ("ami", "bpsk", 4), ("ami", "qpsk", 7),
                                        ("manchester", "16qam", 14)])
def test_message_ber_matches_line_code_theory(lc, mod, snr):
    info = random_bits(600_000, RNG(11))
    r = simulate_link(info, LinkConfig(lc, mod, "awgn", snr), RNG(12))
    assert r.ber_msg == pytest.approx(float(theory.ber_message(lc, mod, snr)), rel=0.07)


def test_same_seed_is_reproducible():
    info = random_bits(50_000, RNG(13))
    a = simulate_link(info, LinkConfig("ami", "qpsk", "burst", 12), RNG(14))
    b = simulate_link(info, LinkConfig("ami", "qpsk", "burst", 12), RNG(14))
    assert np.array_equal(a.rx_info_bits, b.rx_info_bits)


# ---------------------------------------------------------------- métricas
def test_spectral_efficiency():
    assert spectral_efficiency("16qam", "manchester") == {"nominal": 4.0, "liquida": 2.0}
    assert spectral_efficiency("bpsk", "nrz")["liquida"] == 1.0
    assert spectral_efficiency("qpsk", "nrz", rolloff=0.25)["nominal"] == pytest.approx(1.6)


def test_char_errors_and_clustering():
    tx = text_to_bits("abcd")
    rx = tx.copy()
    rx[9] ^= 1
    assert char_errors(tx, rx).tolist() == [False, True, False, False]
    assert error_clustering(np.array([10, 12, 500])) == pytest.approx(2 / 3)
