#!/usr/bin/env bash

# DatenJäger · Reproduccion de la validacion
#
#
# Uso:
#   ./scripts/validacion/validar.sh
#   ./scripts/validacion/validar.sh --sin-cobertura
#   ./scripts/validacion/validar.sh --sin-arranque
#   ./scripts/validacion/validar.sh --con-build
#   ./scripts/validacion/validar.sh --instalar-coverage
#   ./scripts/validacion/validar.sh --ayuda
#
# evidencias en:
#   scripts/validacion/resultados/AAAA-MM-DD_HHMMSS/


set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ" || { echo "No se pudo entrar en $RAIZ"; exit 1; }


# Valores del PDF (columna "Esperado")
ESPERADO_PY=264
ESPERADO_NODE=8
ESPERADO_UNITARIAS=82
ESPERADO_INTEGRACION=182
ESPERADO_COV_NUCLEO=82
ESPERADO_COV_GLOBAL=88
ESPERADO_PESO="258M"
ESPERADO_PESO_MB=258
ESPERADO_ARCHIVOS=444
PDF_ARRANQUE_TXT="≈1.0–1.5 s"
PDF_INTERPRETE_TXT="≈0.9 s"

# Márgenes del modo normal. 0 = exacto.
# Los conteos se dejan exactos a propósito: un test menos es una regresión.
MARGEN_PY=0
MARGEN_NODE=0
MARGEN_DIST=0
MARGEN_COV_NUCLEO=2
MARGEN_COV_GLOBAL=2
MARGEN_ARRANQUE_MIN=0.3
MARGEN_ARRANQUE_MAX=2.0
MARGEN_INTERPRETE_MIN=0.5
MARGEN_INTERPRETE_MAX=1.5
MARGEN_PESO_PCT=5
MARGEN_ARCHIVOS_PCT=5

INCLUDE_COBERTURA='*/backend/*,*/database.py,*/encryption.py,*/reporter.py,*/chatbot.py,*/config.py'


# Opciones

CON_COBERTURA=1
CON_ARRANQUE=1
CON_BUILD=0
INSTALAR_COBERTURA=0
ESTRICTO=0
PERMISIVO=0
SIN_COLOR=0
SIN_ANIMACION=0
COMPACTO=0
SALIDA=""

uso() {
  cat <<'AYUDA'
DatenJäger · validación reproducible

Uso:
  ./scripts/validacion/validar.sh [opciones]

Opciones:
  --sin-cobertura       No repite la suite bajo coverage (ahorra ~2 min).
  --sin-arranque        No mide arranque en frío ni peso del backend.
  --con-build           Añade "npm run build" al final (build del frontend).
  --instalar-coverage   Instala coverage==7.16.2 en el venv si falta.
  --salida DIR          Guarda las evidencias en DIR (por defecto, resultados/<fecha>).
  --margenes            Usa los márgenes del PDF (modo por defecto).
  --estricto            Exige los valores exactos del PDF, sin márgenes.
  --permisivo           No devuelve código 1 por métricas REVISAR.
  --compacto            Tabla compacta para terminales estrechas.
  --sin-color           Desactiva los colores.
  --sin-animacion       Desactiva spinner y barras animadas.
  -h, --ayuda           Muestra esta ayuda.

Ejemplos:
  ./scripts/validacion/validar.sh
  ./scripts/validacion/validar.sh --sin-cobertura
  ./scripts/validacion/validar.sh --con-build --estricto

Salida:
  scripts/validacion/resultados/AAAA-MM-DD_HHMMSS/
    entorno.txt              Versiones, commit y git status
    py-suite.txt             Salida completa de unittest
    node-suite.txt           Salida completa de node --test
    distribucion.txt         Casos por archivo (grep -c "def test_")
    cobertura-run.txt        Corrida de la suite bajo coverage
    cobertura-nucleo.txt     Reporte filtrado (el del 82 %)
    cobertura-global.txt     Reporte global (el del 88 %)
    arranque.txt             Tiempos y peso del backend
    build.txt                Build del frontend (solo con --con-build)
    resumen.txt              Tabla final esperado / obtenido / estado
AYUDA
}

while [ $# -gt 0 ]; do
  case "$1" in
    --sin-cobertura)     CON_COBERTURA=0 ;;
    --sin-arranque)      CON_ARRANQUE=0 ;;
    --con-build)         CON_BUILD=1 ;;
    --instalar-coverage) INSTALAR_COBERTURA=1 ;;
    --margenes)          ESTRICTO=0 ;;
    --estricto)          ESTRICTO=1 ;;
    --permisivo)         PERMISIVO=1 ;;
    --compacto)          COMPACTO=1 ;;
    --sin-color)         SIN_COLOR=1 ;;
    --sin-animacion)     SIN_ANIMACION=1 ;;
    --salida)
      if [ $# -lt 2 ]; then
        echo "ERROR: --salida necesita un directorio." >&2
        exit 2
      fi
      SALIDA="$2"
      shift
      ;;
    -h|--ayuda) uso; exit 0 ;;
    *)
      echo "ERROR: opción desconocida: $1" >&2
      echo "Prueba: ./scripts/validacion/validar.sh --ayuda" >&2
      exit 2
      ;;
  esac
  shift
done


# Presentacion

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "$SIN_COLOR" = "0" ]; then
  C_TITULO=$'\033[1;36m'
  C_OK=$'\033[1;32m'
  C_AVISO=$'\033[1;33m'
  C_ERROR=$'\033[1;31m'
  C_FIN=$'\033[0m'
else
  C_TITULO=""
  C_OK=""
  C_AVISO=""
  C_ERROR=""
  C_FIN=""
fi

paso()  { printf '\n%s==> %s%s\n' "$C_TITULO" "$*" "$C_FIN"; }
info()  { printf '    %s\n' "$*"; }
aviso() { printf '%s[aviso]%s %s\n' "$C_AVISO" "$C_FIN" "$*"; }
error() { printf '%s[error]%s %s\n' "$C_ERROR" "$C_FIN" "$*"; }


# Barra de progreso (solo si stdout es una terminal)

TTY=0
if [ -t 1 ] && [ "${TERM:-dumb}" != "dumb" ] && [ "$SIN_ANIMACION" = "0" ]; then
  TTY=1
fi

if locale charmap 2>/dev/null | grep -qi 'utf-8'; then
  BARRA_LLENO="█"
  BARRA_VACIO="░"
  BARRA_PARCIAL=(▏ ▎ ▍ ▌ ▋ ▊ ▉)
  CORTE="…"
  SPINNER=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
else
  BARRA_LLENO="#"
  BARRA_VACIO="-"
  BARRA_PARCIAL=()
  CORTE="~"
  SPINNER=('|' '/' '-' '\\')
fi

COLUMNAS="$(tput cols 2>/dev/null || echo 120)"
case "$COLUMNAS" in ''|*[!0-9]*) COLUMNAS=120 ;; esac
[ "$COLUMNAS" -lt 60 ] && COLUMNAS=60

if [ "$COMPACTO" = "1" ] || [ "$COLUMNAS" -lt 128 ]; then
  MODO_COMPACTO=1
else
  MODO_COMPACTO=0
fi

if [ "$COLUMNAS" -ge 90 ]; then
  MODO_GLOBAL=1
else
  MODO_GLOBAL=0
fi

if [ "$COLUMNAS" -ge 120 ]; then
  BARRA_ANCHO=24
elif [ "$COLUMNAS" -ge 90 ]; then
  BARRA_ANCHO=20
else
  BARRA_ANCHO=16
fi
PASO_ACTUAL=0
TOTAL_PASOS=4
[ "$CON_COBERTURA" = "1" ] && TOTAL_PASOS=$((TOTAL_PASOS + 1))
[ "$CON_ARRANQUE" = "1" ]  && TOTAL_PASOS=$((TOTAL_PASOS + 1))
[ "$CON_BUILD" = "1" ]     && TOTAL_PASOS=$((TOTAL_PASOS + 1))
TOTAL_PASOS=$((TOTAL_PASOS + 1))   # resumen final

barra_n() {
  local hechos="$1" total="$2"
  local pct=0 llenos=0 vacios="$BARRA_ANCHO"
  local parcial="" extra=0 relleno huecos

  if [ "$total" -gt 0 ]; then
    [ "$hechos" -gt "$total" ] && hechos="$total"
    pct=$(( hechos * 100 / total ))
    local escalones=$(( hechos * BARRA_ANCHO * 8 / total ))
    llenos=$(( escalones / 8 ))
    local resto=$(( escalones % 8 ))
    if [ "$resto" -gt 0 ]; then
      if [ "${#BARRA_PARCIAL[@]}" -gt 0 ]; then
        parcial="${BARRA_PARCIAL[$((resto - 1))]}"
        extra=1
      elif [ "$resto" -ge 4 ]; then
        llenos=$(( llenos + 1 ))
      fi
    fi
    vacios=$(( BARRA_ANCHO - llenos - extra ))
    [ "$vacios" -lt 0 ] && vacios=0
  else
    hechos=0
  fi

  printf -v relleno '%*s' "$llenos" ''
  printf -v huecos '%*s' "$vacios" ''
  relleno=${relleno// /$BARRA_LLENO}
  huecos=${huecos// /$BARRA_VACIO}

  printf '[%s%s%s] %d/%d %3d%%' \
    "$relleno" "$parcial" "$huecos" "$hechos" "$total" "$pct"
}

barra_estatica() {
  barra_n "$PASO_ACTUAL" "$TOTAL_PASOS"
}

formatear_segundos() {
  local s="$1"
  if [ "$s" -ge 60 ]; then
    printf '%dm %02ds' "$((s / 60))" "$((s % 60))"
  else
    printf '%ss' "$s"
  fi
}

_animar_paso() {
  local etiqueta="$1" inicio="$2" sentinela="$3" pid="$4"
  local progreso="${5:-}" esperado="${6:-}" base_global="${7:-0}" total_global="${8:-0}" frame=0

  if [ "$TTY" != "1" ]; then
    return 0
  fi

  local nframes=${#SPINNER[@]}
  local barra="" actual="" ok="" fallos="" omitidos="" cuenta="" total="" hechos=0
  if [ -n "$progreso" ]; then
    barra="$(barra_n 0 "${esperado:-0}")"
  elif [ -n "$esperado" ] && [ "$esperado" -gt 0 ]; then
    barra="$(barra_n 0 "$esperado")"
  fi
  local global_hechos="$base_global"
  local global_barra
  global_barra="$(barra_n "$global_hechos" "$total_global")"
  local global_linea=""

  if [ "$MODO_GLOBAL" = "1" ] && [ "$total_global" -gt 0 ]; then
    global_linea="Global  ${global_barra}  ·  preparando…"
    printf '%s\n' "$global_linea"
  fi

  while [ ! -f "$sentinela" ] && kill -0 "$pid" 2>/dev/null; do
    if [ -n "$progreso" ] && [ -f "$progreso" ]; then
      local contenido linea
      contenido="$(<"$progreso")"
      linea="${contenido%%$'\n'*}"
      IFS=$'\t' read -r cuenta ok fallos omitidos actual <<< "$linea"
      if [[ "$cuenta" =~ ^([0-9]+)/([0-9]+)$ ]]; then
        hechos="${BASH_REMATCH[1]}"
        total="${BASH_REMATCH[2]}"
        barra="$(barra_n "$hechos" "$total")"
        global_hechos=$((base_global + hechos))
        ok="${ok:-0}"
        fallos="${fallos:-0}"
        omitidos="${omitidos:-0}"
      fi
    fi
    [ -z "$barra" ] && barra="$(barra_estatica)"
    global_barra="$(barra_n "$global_hechos" "$total_global")"

    local transcurrido=$(( $(date +%s) - inicio ))
    local eta_txt=""
    if [ "$COLUMNAS" -ge 110 ] && [ "$hechos" -ge 5 ] && [ -n "$total" ] \
       && [ "$total" -gt "$hechos" ] && [ "$transcurrido" -gt 0 ]; then
      local eta=$(( (total - hechos) * transcurrido / hechos ))
      eta_txt=" · ETA $(formatear_segundos "$eta")"
    fi
    local stats=""
    if [ -n "$progreso" ]; then
      stats=" · ✔${ok:-?} ✖${fallos:-?} ⏭${omitidos:-?}"
    fi

    if [ "$MODO_GLOBAL" = "1" ] && [ "$total_global" -gt 0 ]; then
      local ancho_actual=$((COLUMNAS - 45))
      [ "$ancho_actual" -lt 20 ] && ancho_actual=20
      local actual_txt="${actual:0:ancho_actual}"
      global_linea="Global  ${global_barra}  ·  ${actual_txt:-ejecutando…}"
      printf '\033[1A\r\033[K%s\n\r\033[K  %s %s %-18s %4ss%s%s' \
        "$global_linea" "$barra" "${SPINNER[$((frame % nframes))]}" \
        "$etiqueta" "$transcurrido" "$eta_txt" "$stats"
    else
      printf '\r\033[K  %s %s %-18s %4ss%s%s' \
        "$barra" "${SPINNER[$((frame % nframes))]}" "$etiqueta" \
        "$transcurrido" "$eta_txt" "$stats"
    fi
    frame=$((frame + 1))
    sleep 0.2
  done

  if [ "$MODO_GLOBAL" = "1" ] && [ "$total_global" -gt 0 ]; then
    printf '\033[1A\r\033[K\n\r\033[K'
  else
    printf '\r\033[K'
  fi
}

progreso_completar_con_barra() {
  local etiqueta="$1" mensaje="$2" estado="${3:-0}" barra="$4"
  local icono color

  if [ "$estado" = "0" ]; then
    icono="✔"
    color="$C_OK"
  elif [ "$estado" = "skip" ]; then
    icono="–"
    color="$C_AVISO"
  else
    icono="✖"
    color="$C_ERROR"
  fi

  printf '  %s  %s%s%s %s · %s\n' \
    "$barra" "$color" "$icono" "$C_FIN" "$etiqueta" "$mensaje"
}

progreso_completar() {
  progreso_completar_con_barra "$1" "$2" "${3:-0}" "$(barra_estatica)"
}

progreso_instantaneo() {
  local etiqueta="$1" mensaje="$2" estado="${3:-0}"
  PASO_ACTUAL=$((PASO_ACTUAL + 1))
  progreso_completar "$etiqueta" "$mensaje" "$estado"
}

# Ejecuta un comando en segundo plano, anima la barra y devuelve su codigo.
_ejecutar_paso_base() {
  local etiqueta="$1" log="$2" progreso="$3" esperado="${4:-}"
  local base_global="${5:-0}" total_global="${6:-0}"
  shift 6

  PASO_ACTUAL=$((PASO_ACTUAL + 1))
  local inicio
  inicio="$(date +%s)"
  rm -f "$log.rc"

  ( "$@" > "$log" 2>&1; echo $? > "$log.rc" ) &
  local pid=$!

  _animar_paso "$etiqueta" "$inicio" "$log.rc" "$pid" \
    "$progreso" "$esperado" "$base_global" "$total_global"
  wait "$pid" 2>/dev/null || true

  local rc
  rc="$(cat "$log.rc" 2>/dev/null || echo 1)"
  rm -f "$log.rc"
  return "$rc"
}

ejecutar_paso() {
  local etiqueta="$1" log="$2"
  shift 2
  _ejecutar_paso_base "$etiqueta" "$log" "" "" "$GLOBAL_HECHOS" "$GLOBAL_TOTAL" "$@"
}

ejecutar_paso_esperado() {
  local etiqueta="$1" log="$2" esperado="$3"
  shift 3
  _ejecutar_paso_base "$etiqueta" "$log" "" "$esperado" "$GLOBAL_HECHOS" "$GLOBAL_TOTAL" "$@"
}

ejecutar_paso_con_progreso() {
  local etiqueta="$1" log="$2" progreso="$3" esperado="${4:-0}"
  local base_global="${5:-0}" total_global="${6:-0}"
  shift 6
  _ejecutar_paso_base "$etiqueta" "$log" "$progreso" "$esperado" \
    "$base_global" "$total_global" "$@"
}


# Entorno - Python, Node y directorio de evidencias

PY=""
for candidato in "$RAIZ/venv/bin/python" "$RAIZ/.venv/bin/python"; do
  if [ -x "$candidato" ]; then
    PY="$candidato"
    break
  fi
done

if [ -z "$PY" ]; then
  PY="$(command -v python3 || true)"
  if [ -n "$PY" ]; then
    aviso "No se encontró venv/ ni .venv/; se usará $PY. Las dependencias pueden faltar."
  fi
fi

if [ -z "$PY" ]; then
  error "No hay un intérprete de Python disponible."
  exit 2
fi

NODE_BIN="$(command -v node || true)"
NPM_BIN="$(command -v npm || true)"

if [ -z "$NODE_BIN" ]; then
  aviso "Node.js no está instalado o no está en PATH: se omitirá la suite Node."
fi

shopt -s nullglob
NODE_ARCHIVOS=(tests/*.test.cjs)
shopt -u nullglob

PY_TOTAL_ESTIMADO="$(grep -c "def test_" tests/*.py 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')"

GLOBAL_HECHOS=0
GLOBAL_TOTAL="$PY_TOTAL_ESTIMADO"
if [ -n "$NODE_BIN" ] && [ "${#NODE_ARCHIVOS[@]}" -gt 0 ]; then
  GLOBAL_TOTAL=$((GLOBAL_TOTAL + ESPERADO_NODE))
fi
if [ "$CON_COBERTURA" = "1" ]; then
  GLOBAL_TOTAL=$((GLOBAL_TOTAL + PY_TOTAL_ESTIMADO))
fi

if [ -z "$SALIDA" ]; then
  SALIDA="$RAIZ/scripts/validacion/resultados/$(date +%Y-%m-%d_%H%M%S)"
else
  case "$SALIDA" in
    /*) ;;
    *) SALIDA="$RAIZ/$SALIDA" ;;
  esac
fi
mkdir -p "$SALIDA"

RESUMEN="$SALIDA/resumen.txt"
INICIO_GLOBAL="$(date +%s)"


# Versiones y punto de partida

paso "Entorno de ejecución"
if [ "$TTY" = "1" ]; then
  printf '  %s  Iniciando validación...\n' "$(barra_estatica)"
fi

PY_VERSION="$("$PY" -V 2>&1)"
if [ -n "$NODE_BIN" ]; then
  NODE_VERSION="$("$NODE_BIN" -v 2>&1)"
else
  NODE_VERSION="no instalado"
fi
COV_VERSION="$("$PY" -m coverage --version 2>&1 | head -1 || true)"
GIT_COMMIT="$(git log -1 --oneline 2>/dev/null || true)"
GIT_RAMA="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
GIT_STATUS="$(git status --short 2>/dev/null || true)"
# Los scripts de validación y .claudeignore no son código de la aplicación.
GIT_STATUS_CODIGO="$(printf '%s\n' "$GIT_STATUS" | sed '/^$/d' \
  | grep -vE '^.. (\.claudeignore|scripts/validacion/)$' || true)"
GIT_CAMBIOS="$(printf '%s\n' "$GIT_STATUS" | sed '/^$/d' | wc -l | tr -d ' ')"
GIT_CAMBIOS_CODIGO="$(printf '%s\n' "$GIT_STATUS_CODIGO" | sed '/^$/d' | wc -l | tr -d ' ')"

{
  echo "DatenJäger · evidencias de validación"
  echo "Fecha: $(date -Is)"
  echo "Directorio: $RAIZ"
  echo "Rama: ${GIT_RAMA:-no disponible}"
  echo "Commit: ${GIT_COMMIT:-no disponible}"
  echo "Sistema: $(uname -srm)"
  echo "Python: $PY_VERSION ($PY)"
  echo "Node: $NODE_VERSION"
  echo "Coverage: ${COV_VERSION:-no disponible}"
  echo
  echo "git status --short:"
  if [ -n "$GIT_STATUS" ]; then
    printf '%s\n' "$GIT_STATUS"
  else
    echo "(árbol limpio)"
  fi
  echo
  echo "Opciones: cobertura=$CON_COBERTURA arranque=$CON_ARRANQUE build=$CON_BUILD"
} | tee "$SALIDA/entorno.txt" | sed 's/^/    /'

progreso_instantaneo "Entorno" "$PY_VERSION · Node $NODE_VERSION" 0


#  Suite Python

paso "Suite Python (unittest)"
PY_EXIT=1
PY_RAN=""
PY_TIEMPO=""
PY_FALLOS=""
PY_OMITIDAS=""
PY_ESTADO_TEXTO=""

PY_PROGRESO="$SALIDA/py-progreso.txt"
rm -f "$PY_PROGRESO"
ejecutar_paso_con_progreso "Suite Python" "$SALIDA/py-suite.txt" "$PY_PROGRESO" "$PY_TOTAL_ESTIMADO" \
  0 "$GLOBAL_TOTAL" \
  env DATENJAGER_PROGRESO="$PY_PROGRESO" "$PY" scripts/validacion/runner_progreso.py
PY_EXIT=$?

PY_RAN="$(sed -nE 's/^Ran ([0-9]+) tests? in .*/\1/p' "$SALIDA/py-suite.txt" | tail -1)"
PY_TIEMPO="$(sed -nE 's/^Ran [0-9]+ tests? in (.*)/\1/p' "$SALIDA/py-suite.txt" | tail -1)"
PY_FALLOS="$(grep -cE '^(FAIL|ERROR):' "$SALIDA/py-suite.txt" 2>/dev/null || true)"
PY_FALLOS="${PY_FALLOS:-0}"
PY_OMITIDAS="$(grep -oE 'skipped=[0-9]+' "$SALIDA/py-suite.txt" 2>/dev/null | tail -1 | cut -d= -f2)"
PY_OMITIDAS="${PY_OMITIDAS:-0}"
PY_APROBADAS=$(( ${PY_RAN:-0} - PY_FALLOS - PY_OMITIDAS ))
[ "$PY_APROBADAS" -lt 0 ] && PY_APROBADAS=0
GLOBAL_HECHOS="${PY_RAN:-0}"

if grep -qE '^OK( \(|$)' "$SALIDA/py-suite.txt"; then
  if [ "$PY_OMITIDAS" -gt 0 ]; then
    PY_ESTADO_TEXTO="OK (${PY_OMITIDAS} omitidas)"
  else
    PY_ESTADO_TEXTO="OK"
  fi
else
  PY_ESTADO_TEXTO="FALLÓ"
fi

progreso_completar_con_barra "Suite Python" \
  "${PY_RAN:-?} casos · ✔${PY_APROBADAS} · ✖${PY_FALLOS} · ⏭${PY_OMITIDAS} · ${PY_TIEMPO:-?}" "$PY_EXIT" \
  "$(barra_n "${PY_RAN:-0}" "${PY_RAN:-0}")"
info "Evidencia: scripts/validacion/resultados/$(basename "$SALIDA")/py-suite.txt"

if [ "$PY_EXIT" -ne 0 ]; then
  error "La suite Python no terminó en verde. Últimas líneas:"
  tail -n 20 "$SALIDA/py-suite.txt" | sed 's/^/      /'
fi


#  Suite Node

paso "Suite Node (node --test)"
NODE_EXIT=""
NODE_TOTAL=""
NODE_APROBADAS=""
NODE_FALLOS=""
NODE_OMITIDAS=""
NODE_DURACION=""

if [ -z "$NODE_BIN" ]; then
  progreso_instantaneo "Suite Node" "omitida (Node no disponible)" "skip"
  aviso "Se omite: Node.js no está disponible."
elif [ "${#NODE_ARCHIVOS[@]}" -eq 0 ]; then
  progreso_instantaneo "Suite Node" "omitida (sin archivos .test.cjs)" "skip"
  aviso "Se omite: no hay archivos tests/*.test.cjs."
else
  ejecutar_paso_esperado "Suite Node" "$SALIDA/node-suite.txt" "$ESPERADO_NODE" \
    "$NODE_BIN" --test "${NODE_ARCHIVOS[@]}"
  NODE_EXIT=$?

  node_campo() {
    local clave="$1"
    awk -v k="$clave" '($1=="ℹ" || $1=="#") && $2==k {print $3; exit}' "$SALIDA/node-suite.txt"
  }

  NODE_TOTAL="$(node_campo tests)"
  NODE_APROBADAS="$(node_campo pass)"
  NODE_FALLOS="$(node_campo fail)"
  NODE_OMITIDAS="$(node_campo skipped)"
  NODE_DURACION="$(node_campo duration_ms)"
  NODE_FALLOS="${NODE_FALLOS:-0}"
  NODE_OMITIDAS="${NODE_OMITIDAS:-0}"
  GLOBAL_HECHOS=$(( ${PY_RAN:-0} + ${NODE_TOTAL:-0} ))

  progreso_completar_con_barra "Suite Node" \
    "${NODE_APROBADAS:-?}/${NODE_TOTAL:-?} · ✖${NODE_FALLOS} · ⏭${NODE_OMITIDAS} · ${NODE_DURACION:-?} ms" \
    "$NODE_EXIT" "$(barra_n "${NODE_TOTAL:-0}" "${NODE_TOTAL:-0}")"
  info "Evidencia: scripts/validacion/resultados/$(basename "$SALIDA")/node-suite.txt"

  if [ "$NODE_EXIT" -ne 0 ]; then
    error "La suite Node no terminó en verde. Últimas líneas:"
    tail -n 20 "$SALIDA/node-suite.txt" | sed 's/^/      /'
  fi
fi


# Distribucion estatica de casos

paso "Distribución de casos por archivo"
ejecutar_paso "Distribución" "$SALIDA/distribucion.txt" \
  bash -c 'grep -c "def test_" tests/*.py 2>/dev/null | sort -t: -k2 -nr || true'
DIST_EXIT=$?

DIST_TOTAL="$(awk -F: '{s+=$2} END {print s+0}' "$SALIDA/distribucion.txt")"
DIST_UNITARIAS="$(awk -F: '/test_(semantica|tokens|reportes|personas|empresas|auditoria|commands)\.py/ {s+=$2} END {print s+0}' "$SALIDA/distribucion.txt")"
DIST_INTEGRACION="$(awk -F: '/test_(documentos|autenticacion|registro|cuenta|modelos|asistente|servidor|backend_sin_tkinter)\.py/ {s+=$2} END {print s+0}' "$SALIDA/distribucion.txt")"
DIST_OTROS=$(( DIST_TOTAL - DIST_UNITARIAS - DIST_INTEGRACION ))

progreso_completar "Distribución" \
  "$DIST_UNITARIAS unitarias · $DIST_INTEGRACION integración · $DIST_TOTAL total" "$DIST_EXIT"
sed 's/^/    /' "$SALIDA/distribucion.txt"
info "Otros: $DIST_OTROS"


# Cobertura de rama

COV_DISPONIBLE=0
if "$PY" -m coverage --version >/dev/null 2>&1; then
  COV_DISPONIBLE=1
fi

if [ "$INSTALAR_COBERTURA" = "1" ] && [ "$COV_DISPONIBLE" = "0" ]; then
  paso "Instalando coverage==7.16.2"
  if "$PY" -m pip install "coverage==7.16.2"; then
    COV_DISPONIBLE=1
    COV_VERSION="$("$PY" -m coverage --version 2>&1 | head -1 || true)"
  else
    error "No se pudo instalar coverage. Revisa la conexión o el venv."
  fi
fi

COV_EXIT=""
COV_RAN=""
COV_REL_PCT=""
COV_REL_STMTS=""
COV_REL_MISS=""
COV_GLOBAL_PCT=""
COV_GLOBAL_STMTS=""
COV_GLOBAL_MISS=""

if [ "$CON_COBERTURA" = "1" ]; then
  if [ "$COV_DISPONIBLE" = "0" ]; then
    progreso_instantaneo "Cobertura" "omitida (coverage no instalado)" "skip"
    aviso "coverage no está instalado en $PY."
    aviso "Instálalo con: $PY -m pip install coverage==7.16.2"
    aviso "O ejecuta: ./scripts/validacion/validar.sh --instalar-coverage"
    aviso "Se omite la cobertura."
  else
    paso "Cobertura de rama (repite la suite Python)"
    COV_FILE="$SALIDA/.coverage"

    COV_PROGRESO="$SALIDA/cobertura-progreso.txt"
    rm -f "$COV_PROGRESO"
    ejecutar_paso_con_progreso "Cobertura (suite)" "$SALIDA/cobertura-run.txt" "$COV_PROGRESO" "$PY_TOTAL_ESTIMADO" \
      "$GLOBAL_HECHOS" "$GLOBAL_TOTAL" \
      env COVERAGE_FILE="$COV_FILE" DATENJAGER_PROGRESO="$COV_PROGRESO" \
      "$PY" -m coverage run --branch --omit='scripts/validacion/*' \
      scripts/validacion/runner_progreso.py
    COV_EXIT=$?

    COV_RAN="$(sed -nE 's/^Ran ([0-9]+) tests? in .*/\1/p' "$SALIDA/cobertura-run.txt" | tail -1)"
    GLOBAL_HECHOS=$(( ${PY_RAN:-0} + ${NODE_TOTAL:-0} + ${COV_RAN:-0} ))

    COVERAGE_FILE="$COV_FILE" "$PY" -m coverage report --sort=cover \
      --include="$INCLUDE_COBERTURA" > "$SALIDA/cobertura-nucleo.txt" 2>&1
    COV_REL_EXIT=$?

    COVERAGE_FILE="$COV_FILE" "$PY" -m coverage report --sort=cover \
      > "$SALIDA/cobertura-global.txt" 2>&1
    COV_GLOBAL_EXIT=$?

    leer_total() {
      awk '$1=="TOTAL" { gsub(/%/,"",$6); print $2" "$3" "$6; exit }' "$1"
    }

    read -r COV_REL_STMTS COV_REL_MISS COV_REL_PCT <<< "$(leer_total "$SALIDA/cobertura-nucleo.txt")"
    read -r COV_GLOBAL_STMTS COV_GLOBAL_MISS COV_GLOBAL_PCT <<< "$(leer_total "$SALIDA/cobertura-global.txt")"

    if [ "$COV_EXIT" -ne 0 ]; then
      error "La corrida de coverage no terminó en verde (salida $COV_EXIT)."
    fi
    if [ "$COV_REL_EXIT" -ne 0 ] || [ "$COV_GLOBAL_EXIT" -ne 0 ]; then
      error "No se pudo generar alguno de los reportes de cobertura."
    fi

    progreso_completar_con_barra "Cobertura" \
      "núcleo ${COV_REL_PCT:-?} % · global ${COV_GLOBAL_PCT:-?} %" "$COV_EXIT" \
      "$(barra_n "${COV_RAN:-0}" "${COV_RAN:-0}")"
    info "Núcleo:  ${COV_REL_PCT:-?}% (${COV_REL_STMTS:-?} sentencias, ${COV_REL_MISS:-?} sin cubrir)"
    info "Global:  ${COV_GLOBAL_PCT:-?}% (${COV_GLOBAL_STMTS:-?} sentencias, ${COV_GLOBAL_MISS:-?} sin cubrir)"
    info "Evidencias: cobertura-run.txt, cobertura-nucleo.txt, cobertura-global.txt"

    # El archivo .coverage queda aislado en el directorio de resultados y se elimina.
    rm -f "$COV_FILE" "$COV_FILE".*
  fi
fi


# Arranque en frío y peso

CONGELADOS=()
CONGELADO_MIN=""
CONGELADO_MAX=""
CONGELADO_TXT="sin datos"
INTERPRETE=""
PESO=""
PESO_MB=""
ARCHIVOS=""
ARR_EXIT=""

if [ "$CON_ARRANQUE" = "1" ]; then
  paso "Arranque en frío y peso del backend"

  if [ ! -x "$RAIZ/empaquetado/servidor/datenjager-servidor/datenjager-servidor" ]; then
    aviso "No existe el backend congelado en empaquetado/servidor/datenjager-servidor/."
    aviso "Solo se medirá el intérprete. Para generarlo: npm run backend:congelar"
  fi

  ejecutar_paso "Arranque y peso" "$SALIDA/arranque.txt" \
    timeout 300 bash scripts/medir_arranque.sh
  ARR_EXIT=$?

  mapfile -t CONGELADOS < <(sed -nE 's/^congelado.*[[:space:]]([0-9]+\.[0-9]+) s.*/\1/p' "$SALIDA/arranque.txt")
  INTERPRETE="$(sed -nE 's/^intérprete.*[[:space:]]([0-9]+\.[0-9]+) s.*/\1/p' "$SALIDA/arranque.txt" | tail -1)"

  if [ "${#CONGELADOS[@]}" -gt 0 ]; then
    CONGELADO_MIN="$(printf '%s\n' "${CONGELADOS[@]}" | sort -n | head -1)"
    CONGELADO_MAX="$(printf '%s\n' "${CONGELADOS[@]}" | sort -n | tail -1)"
    CONGELADO_TXT="${CONGELADO_MIN}–${CONGELADO_MAX} s"
  fi

  PESO="$(du -sh "$RAIZ/empaquetado/servidor/datenjager-servidor" 2>/dev/null | cut -f1)"
  PESO_MB="$(du -sm "$RAIZ/empaquetado/servidor/datenjager-servidor" 2>/dev/null | cut -f1)"
  ARCHIVOS="$(find "$RAIZ/empaquetado/servidor/datenjager-servidor" -type f 2>/dev/null | wc -l | tr -d ' ')"

  progreso_completar "Arranque y peso" \
    "${CONGELADO_TXT} · ${PESO:-?} / ${ARCHIVOS:-?} archivos" "$ARR_EXIT"
  sed 's/^/    /' "$SALIDA/arranque.txt"
  info "Congelado: ${CONGELADO_TXT} · intérprete: ${INTERPRETE:-sin datos} s"
  info "Peso: ${PESO:-sin datos} · archivos: ${ARCHIVOS:-sin datos}"

  if [ "$ARR_EXIT" -ne 0 ]; then
    aviso "medir_arranque.sh terminó con código $ARR_EXIT (puede ser un puerto ocupado)."
  fi
fi


# Build opcional del frontend

BUILD_EXIT=""
if [ "$CON_BUILD" = "1" ]; then
  paso "Build del frontend (npm run build)"
  if [ -z "$NPM_BIN" ]; then
    progreso_instantaneo "Build frontend" "omitido (npm no disponible)" "skip"
    aviso "Se omite: npm no está disponible."
  else
    ejecutar_paso "Build frontend" "$SALIDA/build.txt" "$NPM_BIN" run build
    BUILD_EXIT=$?
    progreso_completar "Build frontend" \
      "$([ "$BUILD_EXIT" -eq 0 ] && echo 'sin errores' || echo "salida $BUILD_EXIT")" \
      "$BUILD_EXIT"
    if [ "$BUILD_EXIT" -eq 0 ]; then
      info "Build OK. Evidencia: build.txt"
    else
      error "El build falló (salida $BUILD_EXIT). Últimas líneas:"
      tail -n 20 "$SALIDA/build.txt" | sed 's/^/      /'
    fi
  fi
fi


# Resumen esperado / obtenido

FIN_GLOBAL="$(date +%s)"
DURACION_GLOBAL=$(( FIN_GLOBAL - INICIO_GLOBAL ))

# Modo y rangos aceptados

if [ "$ESTRICTO" = "1" ]; then
  MODO_TEXTO="valores exactos del PDF"
  RANGO_PY_MIN=$ESPERADO_PY;       RANGO_PY_MAX=$ESPERADO_PY
  RANGO_NODE_MIN=$ESPERADO_NODE;   RANGO_NODE_MAX=$ESPERADO_NODE
  DIST_UNITARIAS_MIN=$ESPERADO_UNITARIAS; DIST_UNITARIAS_MAX=$ESPERADO_UNITARIAS
  DIST_INTEGRACION_MIN=$ESPERADO_INTEGRACION; DIST_INTEGRACION_MAX=$ESPERADO_INTEGRACION
  DIST_TOTAL_MIN=$ESPERADO_PY;     DIST_TOTAL_MAX=$ESPERADO_PY
  COV_NUCLEO_MIN=$ESPERADO_COV_NUCLEO; COV_NUCLEO_MAX=$ESPERADO_COV_NUCLEO
  COV_GLOBAL_MIN=$ESPERADO_COV_GLOBAL; COV_GLOBAL_MAX=$ESPERADO_COV_GLOBAL
  ARRANQUE_MIN=1.0;                ARRANQUE_MAX=1.5
  INTERPRETE_MIN=0.7;              INTERPRETE_MAX=1.1
  PESO_MB_MIN=$ESPERADO_PESO_MB;   PESO_MB_MAX=$ESPERADO_PESO_MB
  ARCHIVOS_MIN=$ESPERADO_ARCHIVOS; ARCHIVOS_MAX=$ESPERADO_ARCHIVOS
else
  MODO_TEXTO="márgenes del PDF"
  RANGO_PY_MIN=$((ESPERADO_PY - MARGEN_PY));       RANGO_PY_MAX=$((ESPERADO_PY + MARGEN_PY))
  RANGO_NODE_MIN=$((ESPERADO_NODE - MARGEN_NODE)); RANGO_NODE_MAX=$((ESPERADO_NODE + MARGEN_NODE))
  DIST_UNITARIAS_MIN=$((ESPERADO_UNITARIAS - MARGEN_DIST)); DIST_UNITARIAS_MAX=$((ESPERADO_UNITARIAS + MARGEN_DIST))
  DIST_INTEGRACION_MIN=$((ESPERADO_INTEGRACION - MARGEN_DIST)); DIST_INTEGRACION_MAX=$((ESPERADO_INTEGRACION + MARGEN_DIST))
  DIST_TOTAL_MIN=$((ESPERADO_PY - MARGEN_DIST));   DIST_TOTAL_MAX=$((ESPERADO_PY + MARGEN_DIST))
  COV_NUCLEO_MIN=$((ESPERADO_COV_NUCLEO - MARGEN_COV_NUCLEO)); COV_NUCLEO_MAX=$((ESPERADO_COV_NUCLEO + MARGEN_COV_NUCLEO))
  COV_GLOBAL_MIN=$((ESPERADO_COV_GLOBAL - MARGEN_COV_GLOBAL)); COV_GLOBAL_MAX=$((ESPERADO_COV_GLOBAL + MARGEN_COV_GLOBAL))
  ARRANQUE_MIN=$MARGEN_ARRANQUE_MIN; ARRANQUE_MAX=$MARGEN_ARRANQUE_MAX
  INTERPRETE_MIN=$MARGEN_INTERPRETE_MIN; INTERPRETE_MAX=$MARGEN_INTERPRETE_MAX
  PESO_MB_MIN=$((ESPERADO_PESO_MB * (100 - MARGEN_PESO_PCT) / 100)); PESO_MB_MAX=$(( (ESPERADO_PESO_MB * (100 + MARGEN_PESO_PCT) + 50) / 100 ))
  ARCHIVOS_MIN=$(( (ESPERADO_ARCHIVOS * (100 - MARGEN_ARCHIVOS_PCT) + 99) / 100 )); ARCHIVOS_MAX=$(( (ESPERADO_ARCHIVOS * (100 + MARGEN_ARCHIVOS_PCT) + 50) / 100 ))
fi

en_rango_entero() {
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
  [ "$1" -ge "$2" ] && [ "$1" -le "$3" ]
}

en_rango_float() {
  case "$1" in ''|*[!0-9.]*) return 1 ;; esac
  awk -v v="$1" -v min="$2" -v max="$3" 'BEGIN { exit !(v >= min && v <= max) }'
}

estado_py="REVISAR"
if [ "$PY_EXIT" -ne 0 ] || [ "${PY_FALLOS:-0}" -gt 0 ]; then
  estado_py="FALLÓ"
elif [ "$PY_EXIT" -eq 0 ] \
     && en_rango_entero "${PY_RAN:-}" "$RANGO_PY_MIN" "$RANGO_PY_MAX" \
     && [ "${PY_OMITIDAS:-0}" = "0" ]; then
  estado_py="OK"
fi

estado_node="OMITIDO"
if [ -n "$NODE_BIN" ] && [ "${#NODE_ARCHIVOS[@]}" -gt 0 ]; then
  estado_node="REVISAR"
  if [ "${NODE_EXIT:-1}" -ne 0 ] || [ "${NODE_FALLOS:-0}" -gt 0 ]; then
    estado_node="FALLÓ"
  elif en_rango_entero "${NODE_TOTAL:-}" "$RANGO_NODE_MIN" "$RANGO_NODE_MAX" \
       && [ "${NODE_APROBADAS:-0}" = "${NODE_TOTAL:-0}" ] \
       && [ "${NODE_OMITIDAS:-0}" = "0" ]; then
    estado_node="OK"
  fi
fi

estado_dist="REVISAR"
if en_rango_entero "$DIST_UNITARIAS" "$DIST_UNITARIAS_MIN" "$DIST_UNITARIAS_MAX" \
   && en_rango_entero "$DIST_INTEGRACION" "$DIST_INTEGRACION_MIN" "$DIST_INTEGRACION_MAX" \
   && en_rango_entero "$DIST_TOTAL" "$DIST_TOTAL_MIN" "$DIST_TOTAL_MAX" \
   && [ "$DIST_TOTAL" = "${PY_RAN:-}" ]; then
  estado_dist="OK"
fi

estado_cov="SIN DATOS"
if [ "$CON_COBERTURA" = "0" ]; then
  estado_cov="OMITIDO"
elif [ -z "${COV_REL_PCT:-}" ]; then
  estado_cov="SIN DATOS"
elif [ "${COV_EXIT:-1}" != "0" ] || [ "${COV_REL_EXIT:-1}" != "0" ] \
     || [ "${COV_RAN:-0}" != "$ESPERADO_PY" ]; then
  estado_cov="REVISAR"
elif en_rango_entero "$COV_REL_PCT" "$COV_NUCLEO_MIN" "$COV_NUCLEO_MAX"; then
  estado_cov="OK"
else
  estado_cov="REVISAR"
fi

estado_cov_global="SIN DATOS"
if [ "$CON_COBERTURA" = "0" ]; then
  estado_cov_global="OMITIDO"
elif [ -z "${COV_GLOBAL_PCT:-}" ]; then
  estado_cov_global="SIN DATOS"
elif [ "${COV_EXIT:-1}" != "0" ] || [ "${COV_GLOBAL_EXIT:-1}" != "0" ] \
     || [ "${COV_RAN:-0}" != "$ESPERADO_PY" ]; then
  estado_cov_global="REVISAR"
elif en_rango_entero "$COV_GLOBAL_PCT" "$COV_GLOBAL_MIN" "$COV_GLOBAL_MAX"; then
  estado_cov_global="OK"
else
  estado_cov_global="REVISAR"
fi

estado_arranque="SIN DATOS"
if [ "$CON_ARRANQUE" = "0" ]; then
  estado_arranque="OMITIDO"
elif [ "${#CONGELADOS[@]}" -ge 3 ] && [ -n "$CONGELADO_MIN" ] && [ -n "$CONGELADO_MAX" ]; then
  if [ "${ARR_EXIT:-1}" = "0" ] \
     && en_rango_float "$CONGELADO_MIN" "$ARRANQUE_MIN" "$ARRANQUE_MAX" \
     && en_rango_float "$CONGELADO_MAX" "$ARRANQUE_MIN" "$ARRANQUE_MAX"; then
    estado_arranque="OK"
  else
    estado_arranque="REVISAR"
  fi
fi

estado_interprete="SIN DATOS"
if [ "$CON_ARRANQUE" = "0" ]; then
  estado_interprete="OMITIDO"
elif [ "${ARR_EXIT:-1}" = "0" ] && en_rango_float "${INTERPRETE:-}" "$INTERPRETE_MIN" "$INTERPRETE_MAX"; then
  estado_interprete="OK"
else
  estado_interprete="REVISAR"
fi

estado_peso="SIN DATOS"
if [ "$CON_ARRANQUE" = "0" ]; then
  estado_peso="OMITIDO"
elif en_rango_entero "${PESO_MB:-}" "$PESO_MB_MIN" "$PESO_MB_MAX" \
     && en_rango_entero "${ARCHIVOS:-}" "$ARCHIVOS_MIN" "$ARCHIVOS_MAX"; then
  estado_peso="OK"
else
  estado_peso="REVISAR"
fi

estado_git="LIMPIO"
if [ "$GIT_CAMBIOS_CODIGO" -gt 0 ]; then
  estado_git="REVISAR"
elif [ "$GIT_CAMBIOS" -gt 0 ]; then
  estado_git="OK (config/val.)"
fi

estado_build="NO SOLICITADO"
if [ "$CON_BUILD" = "1" ]; then
  if [ -z "$NPM_BIN" ]; then
    estado_build="OMITIDO"
  elif [ "${BUILD_EXIT:-1}" = "0" ]; then
    estado_build="OK"
  else
    estado_build="FALLÓ"
  fi
fi

# Severidad: 0 verde, 1 parcial, 2 revisar, 3 fallos
SEVERIDAD=0
MOTIVOS=()
marcar() {
  local nivel="$1" motivo="$2"
  [ "$nivel" -gt "$SEVERIDAD" ] && SEVERIDAD="$nivel"
  MOTIVOS+=("$motivo")
}

case "$estado_py" in
  OK) ;;
  FALLÓ) marcar 3 "Python: ${PY_RAN:-?} casos, ${PY_FALLOS:-?} fallos" ;;
  *) marcar 2 "Python: ${PY_RAN:-?} casos (PDF ${ESPERADO_PY}), ${PY_OMITIDAS:-0} omitidas" ;;
esac

case "$estado_node" in
  OK) ;;
  OMITIDO) marcar 1 "Node omitido" ;;
  FALLÓ) marcar 3 "Node: ${NODE_APROBADAS:-?}/${NODE_TOTAL:-?}, ${NODE_FALLOS:-?} fallos" ;;
  *) marcar 2 "Node: ${NODE_APROBADAS:-?}/${NODE_TOTAL:-?}, ${NODE_OMITIDAS:-0} omitidas" ;;
esac

case "$estado_dist" in
  OK) ;;
  *) marcar 2 "distribución ${DIST_UNITARIAS}/${DIST_INTEGRACION}/${DIST_TOTAL} (PDF ${ESPERADO_UNITARIAS}/${ESPERADO_INTEGRACION}/${ESPERADO_PY})" ;;
esac

case "$estado_cov" in
  OK) ;;
  OMITIDO) marcar 1 "cobertura omitida" ;;
  "SIN DATOS") marcar 2 "cobertura núcleo sin datos" ;;
  *) marcar 2 "cobertura núcleo ${COV_REL_PCT:-?} % (margen ${COV_NUCLEO_MIN}–${COV_NUCLEO_MAX})" ;;
esac

case "$estado_cov_global" in
  OK) ;;
  OMITIDO) marcar 1 "cobertura global omitida" ;;
  "SIN DATOS") marcar 2 "cobertura global sin datos" ;;
  *) marcar 2 "cobertura global ${COV_GLOBAL_PCT:-?} % (margen ${COV_GLOBAL_MIN}–${COV_GLOBAL_MAX})" ;;
esac

case "$estado_arranque" in
  OK) ;;
  OMITIDO) marcar 1 "arranque omitido" ;;
  "SIN DATOS") marcar 2 "arranque sin datos" ;;
  *) marcar 2 "arranque ${CONGELADO_TXT} (margen ${ARRANQUE_MIN}–${ARRANQUE_MAX} s)" ;;
esac

case "$estado_interprete" in
  OK) ;;
  OMITIDO) marcar 1 "arranque del intérprete omitido" ;;
  "SIN DATOS") marcar 2 "arranque del intérprete sin datos" ;;
  *) marcar 2 "intérprete ${INTERPRETE:-?} s (margen ${INTERPRETE_MIN}–${INTERPRETE_MAX} s)" ;;
esac

case "$estado_peso" in
  OK) ;;
  OMITIDO) marcar 1 "peso omitido" ;;
  "SIN DATOS") marcar 2 "peso sin datos" ;;
  *) marcar 2 "peso ${PESO:-?}/${ARCHIVOS:-?} (margen ${PESO_MB_MIN}–${PESO_MB_MAX}M / ${ARCHIVOS_MIN}–${ARCHIVOS_MAX})" ;;
esac

[ "$estado_git" = "REVISAR" ] && marcar 2 "árbol de trabajo con cambios de código"

if [ "$CON_BUILD" = "1" ]; then
  case "$estado_build" in
    OK) ;;
    FALLÓ) marcar 3 "build falló" ;;
    OMITIDO) marcar 2 "build sin npm" ;;
    *) marcar 2 "build: ${BUILD_EXIT:-?}" ;;
  esac
fi

case "$SEVERIDAD" in
  0) RESULTADO="SUITE EN VERDE" ;;
  1) RESULTADO="PARCIAL" ;;
  2) RESULTADO="REVISAR" ;;
  *) RESULTADO="FALLOS" ;;
esac

RC=0
[ "$SEVERIDAD" -ge 2 ] && RC=1
[ "$ESTRICTO" = "1" ] && [ "$SEVERIDAD" -ge 1 ] && RC=1
[ "$PERMISIVO" = "1" ] && [ "$SEVERIDAD" -lt 3 ] && RC=0

MOTIVO_TXT=""
for motivo in "${MOTIVOS[@]}"; do
  [ -n "$MOTIVO_TXT" ] && MOTIVO_TXT+=" · "
  MOTIVO_TXT+="$motivo"
done

# Relleno por caracteres (no por bytes) para que los acentos no desalineen
pad() {
  local texto="$1" ancho="$2" n
  n=${#texto}
  if [ "$n" -gt "$ancho" ]; then
    printf '%s%s' "${texto:0:$((ancho - 1))}" "$CORTE"
    return
  fi
  printf '%s' "$texto"
  while [ "$n" -lt "$ancho" ]; do
    printf ' '
    n=$((n + 1))
  done
}

guiones() {
  local n="$1" s
  printf -v s '%*s' "$n" ''
  printf '%s' "${s// /-}"
}

rango_etiquetado() {
  local min="$1" max="$2" sufijo="${3:-}"
  if [ "$min" = "$max" ]; then
    printf '%s%s (exacto)' "$min" "$sufijo"
  else
    printf '%s–%s%s' "$min" "$max" "$sufijo"
  fi
}

margen_dist_txt() {
  if [ "$DIST_UNITARIAS_MIN" = "$DIST_UNITARIAS_MAX" ] \
     && [ "$DIST_INTEGRACION_MIN" = "$DIST_INTEGRACION_MAX" ] \
     && [ "$DIST_TOTAL_MIN" = "$DIST_TOTAL_MAX" ]; then
    printf '%s/%s/%s (exacto)' "$ESPERADO_UNITARIAS" "$ESPERADO_INTEGRACION" "$ESPERADO_PY"
  else
    printf '%s–%s/%s–%s/%s–%s' \
      "$DIST_UNITARIAS_MIN" "$DIST_UNITARIAS_MAX" \
      "$DIST_INTEGRACION_MIN" "$DIST_INTEGRACION_MAX" \
      "$DIST_TOTAL_MIN" "$DIST_TOTAL_MAX"
  fi
}

margen_peso_txt() {
  if [ "$PESO_MB_MIN" = "$PESO_MB_MAX" ] && [ "$ARCHIVOS_MIN" = "$ARCHIVOS_MAX" ]; then
    printf '%sM / %s (exacto)' "$PESO_MB_MIN" "$ARCHIVOS_MIN"
  else
    printf '%s–%sM / %s–%s' "$PESO_MB_MIN" "$PESO_MB_MAX" "$ARCHIVOS_MIN" "$ARCHIVOS_MAX"
  fi
}

linea_resumen() {
  local metrica="$1" pdf="$2" margen="$3" obtenido="$4" estado="$5"
  if [ "$MODO_COMPACTO" = "1" ] && [ "$metrica" = "Distribución (u/i/total)" ]; then
    metrica="Distribución (u/i/t)"
  fi
  {
    printf '  '
    if [ "$MODO_COMPACTO" = "1" ]; then
      pad "$metrica" 22; printf ' '
      pad "$pdf · $margen" 32; printf ' '
      pad "$obtenido" 32; printf ' '
      case "$estado" in
        "OK (config/val.)") printf '%s\n' "OK (config)" ;;
        *) printf '%s\n' "$estado" ;;
      esac
    else
      pad "$metrica" 26; printf ' '
      pad "$pdf" 22; printf ' '
      pad "$margen" 22; printf ' '
      pad "$obtenido" 36; printf ' '
      printf '%s\n' "$estado"
    fi
  } | tee -a "$RESUMEN"
}

{
  echo "DatenJäger · resumen de validación"
  echo "Fecha: $(date -Is)"
  echo "Commit: ${GIT_COMMIT:-no disponible}"
  echo "Entorno: $PY_VERSION · Node $NODE_VERSION"
  echo "Modo: $MODO_TEXTO"
  echo "Duración total: ${DURACION_GLOBAL}s"
  echo
} > "$RESUMEN"

paso "Resumen de la corrida"
PASO_ACTUAL=$TOTAL_PASOS
progreso_completar "Resumen" "todas las mediciones completadas" 0
head -n 9 "$RESUMEN" | sed 's/^/  /'

{
  printf '  '
  if [ "$MODO_COMPACTO" = "1" ]; then
    pad "Métrica" 22; printf ' '
    pad "PDF · margen" 32; printf ' '
    pad "Obtenido" 32; printf ' '
    printf '%s\n' "Estado"
    printf '  '
    guiones 22; printf ' '
    guiones 32; printf ' '
    guiones 32; printf ' '
    guiones 10; printf '\n'
  else
    pad "Métrica" 26; printf ' '
    pad "Esperado (PDF)" 22; printf ' '
    pad "Margen aceptado" 22; printf ' '
    pad "Obtenido" 36; printf ' '
    printf '%s\n' "Estado"
    printf '  '
    guiones 26; printf ' '
    guiones 22; printf ' '
    guiones 22; printf ' '
    guiones 36; printf ' '
    guiones 16; printf '\n'
  fi
} | tee -a "$RESUMEN"

linea_resumen "Pruebas Python" \
  "${ESPERADO_PY}/${ESPERADO_PY} OK" \
  "$(rango_etiquetado "$RANGO_PY_MIN" "$RANGO_PY_MAX")" \
  "${PY_RAN:-?} casos · ✔${PY_APROBADAS:-?} · ✖${PY_FALLOS:-?} · ⏭${PY_OMITIDAS:-0}" \
  "$estado_py"

linea_resumen "Pruebas Node" \
  "${ESPERADO_NODE}/${ESPERADO_NODE} OK" \
  "$(rango_etiquetado "$RANGO_NODE_MIN" "$RANGO_NODE_MAX")" \
  "${NODE_APROBADAS:-?}/${NODE_TOTAL:-?} · ✖${NODE_FALLOS:-?} · ⏭${NODE_OMITIDAS:-0}" \
  "$estado_node"

linea_resumen "Distribución (u/i/total)" \
  "${ESPERADO_UNITARIAS}/${ESPERADO_INTEGRACION}/${ESPERADO_PY}" \
  "$(margen_dist_txt)" \
  "${DIST_UNITARIAS}/${DIST_INTEGRACION}/${DIST_TOTAL}" \
  "$estado_dist"

linea_resumen "Cobertura núcleo" \
  "${ESPERADO_COV_NUCLEO} %" \
  "$(rango_etiquetado "$COV_NUCLEO_MIN" "$COV_NUCLEO_MAX" " %")" \
  "${COV_REL_PCT:-?} % (${COV_REL_STMTS:-?} sent.)" \
  "$estado_cov"

linea_resumen "Cobertura global" \
  "${ESPERADO_COV_GLOBAL} %" \
  "$(rango_etiquetado "$COV_GLOBAL_MIN" "$COV_GLOBAL_MAX" " %")" \
  "${COV_GLOBAL_PCT:-?} % (${COV_GLOBAL_STMTS:-?} sent.)" \
  "$estado_cov_global"

linea_resumen "Arranque congelado (3)" \
  "$PDF_ARRANQUE_TXT" \
  "$(rango_etiquetado "$ARRANQUE_MIN" "$ARRANQUE_MAX" " s")" \
  "$CONGELADO_TXT" \
  "$estado_arranque"

linea_resumen "Arranque intérprete" \
  "$PDF_INTERPRETE_TXT" \
  "$(rango_etiquetado "$INTERPRETE_MIN" "$INTERPRETE_MAX" " s")" \
  "${INTERPRETE:-?} s" \
  "$estado_interprete"

linea_resumen "Peso / archivos" \
  "${ESPERADO_PESO} / ${ESPERADO_ARCHIVOS}" \
  "$(margen_peso_txt)" \
  "${PESO:-?} / ${ARCHIVOS:-?}" \
  "$estado_peso"

linea_resumen "Árbol de trabajo" \
  "sin cambios" \
  "código limpio" \
  "${GIT_CAMBIOS_CODIGO} de código (${GIT_CAMBIOS} total)" \
  "$estado_git"

if [ "$CON_BUILD" = "1" ]; then
  linea_resumen "Build frontend" \
    "sin errores" \
    "exit 0" \
    "$([ "${BUILD_EXIT:-1}" = "0" ] && echo 'OK' || echo "salida ${BUILD_EXIT:-?}")" \
    "$estado_build"
fi

{
  echo
  echo "  Progreso real por suite"
  printf '    %-11s %s  %s\n' "Global" \
    "$(barra_n "${GLOBAL_HECHOS:-0}" "${GLOBAL_TOTAL:-0}")" \
    "ejecuciones de test solicitadas"
  printf '    %-11s %s  %s\n' "Python" \
    "$(barra_n "${PY_RAN:-0}" "${PY_TOTAL_ESTIMADO:-0}")" \
    "✔${PY_APROBADAS:-?} · ✖${PY_FALLOS:-?} · ⏭${PY_OMITIDAS:-0} · ${PY_TIEMPO:-?}"
  printf '    %-11s %s  %s\n' "Node" \
    "$(barra_n "${NODE_TOTAL:-0}" "${NODE_TOTAL:-0}")" \
    "${NODE_APROBADAS:-?}/${NODE_TOTAL:-?} · ✖${NODE_FALLOS:-?} · ⏭${NODE_OMITIDAS:-0}"
  if [ "$CON_COBERTURA" = "1" ] && [ -n "${COV_RAN:-}" ]; then
    printf '    %-11s %s  %s\n' "Cobertura" \
      "$(barra_n "$COV_RAN" "$COV_RAN")" \
      "núcleo ${COV_REL_PCT:-?} % · global ${COV_GLOBAL_PCT:-?} %"
  fi
} | tee -a "$RESUMEN"

{
  echo
  echo "Resultado: $RESULTADO"
  [ -n "$MOTIVO_TXT" ] && echo "Motivo: $MOTIVO_TXT"
  echo "Evidencias: $SALIDA"
  echo
  echo "Notas:"
  echo "- Los tiempos varían entre corridas por caché del sistema y carga de la máquina."
  echo "- Márgenes: cobertura ±2 pp; arranque 0.3–2.0 s; peso ±5 %. Los conteos son exactos."
  echo "- Usa --estricto para exigir los valores exactos del PDF."
  echo "- El 82 % exige el filtro de cobertura del núcleo; sin config.py/chatbot.py sube a 83 %."
  echo "- La suite Python tarda ~2 min y coverage la repite; Node tarda < 1 s."
  echo "- No se modifica código de la aplicación; .coverage se elimina al terminar."
} | tee -a "$RESUMEN"

case "$RESULTADO" in
  "SUITE EN VERDE") COLOR_FINAL="$C_OK" ;;
  "FALLOS") COLOR_FINAL="$C_ERROR" ;;
  *) COLOR_FINAL="$C_AVISO" ;;
esac

printf '\n%s%s%s\n' "$COLOR_FINAL" "$RESULTADO" "$C_FIN"
printf 'Evidencias guardadas en: %s\n\n' "$SALIDA"

exit "$RC"
