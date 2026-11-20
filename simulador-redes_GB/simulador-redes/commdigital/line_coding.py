"""Codificação de linha.

Todos os codificadores recebem bits de mensagem e devolvem um *fluxo binário*
que é entregue ao modulador digital:

* NRZ-L (linha de base, sem redundância);
* Manchester (bifase; convenção G. E. Thomas / Stallings: bit 1 = transição
  baixo->alto = chips (0,1); bit 0 = alto->baixo = chips (1,0));
* AMI (pseudoternário: 0 -> nível 0; 1 -> pulsos alternados +1/-1). Como o
  modulador é binário, cada símbolo ternário vira uma palavra de 2 bits:
  0 -> 00, +1 -> 01, -1 -> 10 (a palavra 11 é inválida).

Cada decodificador devolve (bits, violações). As violações são erros
*detectáveis* pelo próprio código (Manchester: chips iguais; AMI: palavra 11 ou
dois pulsos consecutivos de mesma polaridade).

ATENÇÃO: codificação de linha NÃO é codificação de correção de erros. Ela molda
o espectro/sincronismo/componente DC; só detecta alguns erros e não os corrige.
"""
from __future__ import annotations

import numpy as np


class LineCode:
    name = ""
    label = ""
    rate = 1.0           # bits de mensagem por bit enviado ao modulador
    slots_per_bit = 1    # intervalos de sinalização por bit de mensagem

    def encode(self, bits: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def decode(self, stream: np.ndarray) -> tuple[np.ndarray, int]:
        raise NotImplementedError

    def levels(self, bits: np.ndarray) -> np.ndarray:
        """Níveis de amplitude (-1, 0, +1) por intervalo — usado só para desenhar ondas."""
        raise NotImplementedError


class NRZL(LineCode):
    name = "nrz"
    label = "NRZ-L"
    rate = 1.0
    slots_per_bit = 1

    def encode(self, bits):
        return np.asarray(bits, dtype=np.uint8).copy()

    def decode(self, stream):
        return np.asarray(stream, dtype=np.uint8).copy(), 0

    def levels(self, bits):
        return 2.0 * np.asarray(bits, dtype=float) - 1.0


class Manchester(LineCode):
    name = "manchester"
    label = "Manchester"
    rate = 0.5
    slots_per_bit = 2

    def encode(self, bits):
        b = np.asarray(bits, dtype=np.uint8)
        out = np.empty(2 * b.size, dtype=np.uint8)
        out[0::2] = 1 - b      # 1º chip
        out[1::2] = b          # 2º chip
        return out

    def decode(self, stream):
        s = np.asarray(stream, dtype=np.uint8)
        s = s[: (s.size // 2) * 2]
        c1, c2 = s[0::2], s[1::2]
        violations = int(np.count_nonzero(c1 == c2))   # sem transição no meio do bit
        return c2.copy(), violations                   # decisão pela 2ª metade do bit

    def levels(self, bits):
        return 2.0 * self.encode(bits).astype(float) - 1.0


class AMI(LineCode):
    name = "ami"
    label = "AMI"
    rate = 0.5
    slots_per_bit = 1

    @staticmethod
    def ternary(bits) -> np.ndarray:
        ones = np.asarray(bits, dtype=np.int64)
        polarity = np.where(np.cumsum(ones) % 2 == 1, 1, -1)
        return (ones * polarity).astype(np.int8)

    def encode(self, bits):
        lv = self.ternary(bits)
        out = np.empty(2 * lv.size, dtype=np.uint8)
        out[0::2] = lv == -1
        out[1::2] = lv == 1
        return out

    def decode(self, stream):
        s = np.asarray(stream, dtype=np.uint8)
        s = s[: (s.size // 2) * 2]
        w1, w2 = s[0::2], s[1::2]
        bits = (w1 | w2).astype(np.uint8)              # qualquer pulso => bit 1
        invalid = int(np.count_nonzero(w1 & w2))       # palavra 11
        lv = w2.astype(np.int8) - w1.astype(np.int8)   # +1, -1 ou 0
        pulses = lv[lv != 0]
        bipolar = int(np.count_nonzero(pulses[1:] == pulses[:-1])) if pulses.size > 1 else 0
        return bits, invalid + bipolar

    def levels(self, bits):
        return self.ternary(bits).astype(float)


LINE_CODES = {c.name: c for c in (NRZL(), Manchester(), AMI())}


def get_line_code(name: str) -> LineCode:
    try:
        return LINE_CODES[name.lower()]
    except KeyError as exc:
        raise ValueError(f"Código de linha desconhecido: {name!r}. Opções: {list(LINE_CODES)}") from exc
