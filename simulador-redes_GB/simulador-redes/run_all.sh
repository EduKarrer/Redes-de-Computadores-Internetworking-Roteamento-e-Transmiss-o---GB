#!/usr/bin/env bash
# Reproduz TUDO: testes, consistência, ablação, experimentos (~1,5 min), figuras e tabelas.
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest -q
python scripts/teste_consistencia.py
python scripts/ablacao_scrambler.py > /dev/null
python scripts/executar_experimentos.py
python scripts/gerar_figuras.py
echo "Pronto: veja results/figures/ e results/*.md"
