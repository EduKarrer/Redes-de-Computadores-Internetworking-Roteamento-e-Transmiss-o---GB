"""Simulador de transmissão digital — Redes de Computadores (UNISINOS), Trabalho II.

Cadeia completa:
    mensagem ASCII -> bits -> codificação de linha -> embaralhador -> modulação
    -> canal (AWGN / rajadas) -> demodulação -> desembaralhador -> decodificação
    de linha -> mensagem recuperada + métricas (BER, eficiência espectral).
"""
__version__ = "1.0.0"
