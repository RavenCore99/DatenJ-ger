#!/usr/bin/env bash
# scripts/medir_arranque.sh — arranque en frío del backend congelado (Fase 5).
#
# Mide lo que pide la prueba de viabilidad de `planning.md`: cuánto tarda el
# servicio en anunciarse, comparado con lanzarlo con el intérprete normal.
set -u

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$RAIZ/empaquetado/servidor/datenjager-servidor/datenjager-servidor"
PUERTO=8897

esperar_anuncio() {
  local log="$1" pid="$2" inicio="$3" intentos=0
  while [ "$intentos" -lt 600 ]; do
    if grep -q DATENJAGER_LISTO "$log" 2>/dev/null; then break; fi
    sleep 0.05
    intentos=$((intentos + 1))
  done
  awk -v a="$inicio" -v b="$(date +%s.%N)" 'BEGIN { printf "%.2f", b - a }'
}

medir() {
  local etiqueta="$1" puerto="$2"; shift 2
  rm -rf /tmp/dj-medida && mkdir -p /tmp/dj-medida
  rm -f /tmp/dj-medida.log
  local inicio; inicio="$(date +%s.%N)"
  DATENJAGER_DATOS=/tmp/dj-medida "$@" --puerto "$puerto" --token t > /tmp/dj-medida.log 2>&1 &
  local pid=$!
  local segundos; segundos="$(esperar_anuncio /tmp/dj-medida.log "$pid" "$inicio")"
  printf '%-34s %6s s   %s\n' "$etiqueta" "$segundos" "$(head -1 /tmp/dj-medida.log)"
  kill "$pid" 2>/dev/null
  wait "$pid" 2>/dev/null
  sleep 1
}

echo "--- Arranque en frío del servicio local ---"
for corrida in 1 2 3; do
  medir "congelado (corrida $corrida)" 8897 "$BIN"
done
medir "intérprete del proyecto (venv)" 8896 "$RAIZ/venv/bin/python" "$RAIZ/scripts/servidor_entry.py"

echo
echo "--- Peso en disco ---"
du -sh "$RAIZ/empaquetado/servidor/datenjager-servidor" 2>/dev/null | cut -f1
find "$RAIZ/empaquetado/servidor/datenjager-servidor" -type f 2>/dev/null | wc -l
