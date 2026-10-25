# Validación reproducible · DatenJäger

Script para repetir en tu máquina (CachyOS / Arch Linux) las mediciones de la
sección 5 del *Plan de validación, evaluación de calidad y mejora continua* y del
*Reporte de ejecución de pruebas*:

| Métrica | Referencia del PDF |
|---|---|
| Pruebas Python | 264/264 OK |
| Pruebas Node | 8/8 OK |
| Unitarias / integración | 82 / 182 |
| Cobertura del núcleo (rama) | 82 % (3.086 sentencias) |
| Cobertura global | 88 % (5.303 sentencias) |
| Arranque congelado | ≈1,0–1,5 s (3 corridas) |
| Arranque con intérprete | ≈0,9 s |
| Peso del backend congelado | 258 MB · 444 archivos |

No modifica código de la aplicación. Solo ejecuta las suites y guarda las
evidencias en un directorio de resultados aislado.

## Requisitos

- Python del proyecto en `venv/` o `.venv/` con las dependencias instaladas.
- Node.js en `PATH`.
- `coverage` en el venv (ya está instalado en este equipo):

```bash
./venv/bin/python -m coverage --version
```

Si falta:

```bash
./venv/bin/python -m pip install coverage==7.16.2
# o
./scripts/validacion/validar.sh --instalar-coverage
```

En Arch/CachyOS no hace falta instalar nada del sistema: `bash`, `awk`, `sed`,
`grep`, `find`, `du` y `timeout` vienen en `coreutils`/`base`.

## Uso rápido

Desde la raíz del repositorio:

```bash
cd /home/raven/Documentos/DatenJäger/DatenJ-ger

# Reproducción completa (~4 min: suite Python + coverage + arranque)
./scripts/validacion/validar.sh

# Sin cobertura (mucho más rápido, ~2 min)
./scripts/validacion/validar.sh --sin-cobertura

# Sin arranque ni peso
./scripts/validacion/validar.sh --sin-arranque

# Añadir el build del frontend
./scripts/validacion/validar.sh --con-build

# Usar los márgenes del PDF (modo por defecto, recomendado para la demo)
./scripts/validacion/validar.sh --margenes

# Exigir los valores exactos del PDF, sin márgenes
./scripts/validacion/validar.sh --estricto

# No devolver código 1 por métricas REVISAR (sigue mostrando REVISAR)
./scripts/validacion/validar.sh --permisivo

# Terminal estrecho, sin colores o sin animación
./scripts/validacion/validar.sh --compacto --sin-color --sin-animacion
```

También puedes ejecutarlo desde cualquier directorio usando la ruta absoluta;
el script se posiciona solo en la raíz del proyecto.

```bash
/home/raven/Documentos/DatenJäger/DatenJ-ger/scripts/validacion/validar.sh
```

## Progreso visual

En una terminal se muestran dos líneas: la barra global de ejecuciones y la
barra de la suite que está corriendo. La segunda incluye el test actual, los
aprobados, los fallos, los omitidos y la ETA:

```text
Global  [██████████░░░░░░░░░░░░░░] 124/536  23%  ·  tests.test_servidor.TestServidor.test_acceso_por_http
        [████████████░░░░░░░░░░░░] 124/264  47% ⠹ Suite Python  52s · ETA 58s · ✔124 ✖0 ⏭0
```

Al terminar se imprime un panel con las barras completas:

```text
  Progreso real por suite
    Global      [████████████████████████] 536/536 100%  ejecuciones de test solicitadas
    Python      [████████████████████████] 264/264 100%  ✔264 · ✖0 · ⏭0 · 105.7s
    Node        [████████████████████████] 8/8 100%      8/8 · ✖0 · ⏭0
    Cobertura   [████████████████████████] 264/264 100%  núcleo 82 % · global 88 %
```

- Durante Python y cobertura, el conteo sale de `runner_progreso.py`, que usa
  el mismo descubrimiento de `unittest` y escribe después de cada test:
  `hechos/total<TAB>ok<TAB>fallos<TAB>omitidos<TAB>test_actual`.
- La barra global suma Python + Node + cobertura (cuando corresponde). Si
  omites cobertura con `--sin-cobertura`, el total baja y la barra global sigue
  llegando al 100 % de lo solicitado.
- La barra por pasos se sigue usando para entorno, distribución, arranque y
  build. Node muestra `0/8` mientras corre y `8/8` al terminar.
- El test actual se ve en la línea global; si un test se cuelga, ahí queda el
  nombre del último test iniciado.
- Los pasos omitidos (por ejemplo, Node no instalado o `--sin-cobertura`) se
  marcan como `OMITIDO`; el resultado final será `PARCIAL`, no verde.
- Con `--con-build` se añade el paso **Build frontend** y su fila en la tabla;
  si el build falla, el script termina con código 1.
- Si rediriges la salida o no hay terminal, no se anima el spinner, pero las
  barras y el panel final se guardan igualmente en `resumen.txt`.
- El runner no modifica los tests ni el código de la aplicación.

## Qué hace exactamente

1. **Entorno**: `python -V`, `node -v`, versión de `coverage`, rama, commit y
   `git status --short`.
2. **Suite Python**: `python scripts/validacion/runner_progreso.py`, que usa
   `unittest.TestLoader().discover('tests', top_level_dir='.')` y ejecuta los
   mismos casos que `python -m unittest discover -s tests -t .`. El avance
   (incluido el test actual, aprobados, fallos y omitidos) se escribe en
   `py-progreso.txt`.
3. **Suite Node**:
   `node --test tests/*.test.cjs`
4. **Distribución de casos**:
   `grep -c "def test_" tests/*.py`
5. **Cobertura de rama**:
   ```bash
   coverage run --branch --omit='scripts/validacion/*' \
     scripts/validacion/runner_progreso.py
   coverage report --sort=cover \
     --include="*/backend/*,*/database.py,*/encryption.py,*/reporter.py,*/chatbot.py,*/config.py"
   coverage report --sort=cover
   ```
   El `--omit` excluye el runner auxiliar para que el total global siga siendo
   comparable con el PDF (5.303 sentencias / 88 %). El archivo `.coverage` se
   crea dentro del directorio de resultados y se elimina al terminar.
6. **Arranque y peso**:
   `bash scripts/medir_arranque.sh`, más `du -sh` y `find … | wc -l`.
7. **Resumen final** con columnas *Esperado (PDF) / Margen aceptado /
   Obtenido / Estado*, el panel de progreso real por suite y el resultado
   global (`SUITE EN VERDE`, `PARCIAL`, `REVISAR` o `FALLOS`).

## Resultados

Cada corrida crea:

```
scripts/validacion/resultados/AAAA-MM-DD_HHMMSS/
├── entorno.txt
├── py-suite.txt
├── py-progreso.txt
├── node-suite.txt
├── distribucion.txt
├── cobertura-run.txt
├── cobertura-progreso.txt
├── cobertura-nucleo.txt
├── cobertura-global.txt
├── arranque.txt
├── resumen.txt
└── build.txt            (solo con --con-build)
```

El contenido de `resultados/` está ignorado por Git (ver
`resultados/.gitignore`), así que puedes conservar todas las corridas que
quieras sin ensuciar el repositorio.

## Cómo leer el resumen

Cada fila muestra cuatro cosas: el valor del PDF, el margen aceptado, lo
obtenido en esta corrida y el estado.

- **OK**: la cifra está dentro del margen (o coincide exactamente, si el margen
  es 0).
- **REVISAR**: la suite pasó, pero la cifra quedó fuera del margen: cambió el
  número de tests, la cobertura, el arranque o el peso.
- **FALLÓ**: la suite o el build no terminaron correctamente.
- **OMITIDO**: la medición se saltó a propósito (`--sin-cobertura`,
  `--sin-arranque`) o falta una herramienta.
- **SIN DATOS**: la medición se solicitó pero no produjo datos.

El resultado global es:

- **SUITE EN VERDE**: todo lo solicitado está OK.
- **PARCIAL**: no hay fallos ni cifras fuera de margen, pero se omitió alguna
  medición (por ejemplo, cobertura o arranque). Devuelve código 0.
- **REVISAR**: alguna métrica solicitada está fuera de margen o sin datos.
  Devuelve código 1.
- **FALLOS**: falló Python, Node o el build. Devuelve código 1.

### Márgenes

Para la presentación se usan márgenes alrededor de los valores del PDF, porque
el arranque y el peso varían entre máquinas:

| Métrica | Margen normal |
|---|---|
| Pruebas Python / Node | exacto (264 / 8) |
| Distribución | exacta (82 / 182 / 264) |
| Cobertura núcleo / global | ±2 pp (80–84 % / 86–90 %) |
| Arranque congelado | 0,3–2,0 s (el PDF dice ≈1,0–1,5 s; más rápido también vale) |
| Arranque con intérprete | 0,5–1,5 s |
| Peso / archivos | ±5 % (245–271 MB / 422–466 archivos) |

Los conteos de tests se dejan exactos a propósito: un test menos es una
regresión, no una variación de máquina. Si quieres ampliarlos, cambia
`MARGEN_PY`, `MARGEN_NODE` o `MARGEN_DIST` al inicio del script.

Con `--estricto` se exigen los valores exactos del PDF: cobertura 82/88 %,
arranque 1,0–1,5 s y peso 258M/444. Con `--permisivo` el código de salida es 0
aunque haya métricas `REVISAR`, pero el banner sigue mostrando `REVISAR`.

Los tiempos de arranque y la duración de las suites **no son fijos**: dependen
de la caché del sistema y de la carga de la máquina. El PDF ya reporta
horquillas (1,04–1,54 s congelado, 0,92 s con intérprete). Por eso se miden tres
corridas y se muestra el rango.

El **82 %** solo se reproduce con el filtro exacto de cobertura del núcleo. Si
se omite `config.py` o `chatbot.py`, el total sube a 83 % sobre 2.806
sentencias, tal como advierte el reporte.

La cobertura global del **88 %** se mantiene porque `coverage run` usa
`--omit='scripts/validacion/*'`: el runner de progreso y los scripts auxiliares
no cuentan como código de la aplicación.

## Solución de problemas

- **`coverage no está instalado`**: ejecuta
  `./venv/bin/python -m pip install coverage==7.16.2` o añade
  `--instalar-coverage`.
- **La suite Python falla**: revisa `py-suite.txt`; el script muestra las
  últimas 20 líneas. No se debe a los `ResourceWarning` de pruebas que simulan
  respuestas 401/403/429.
- **El arranque falla**: comprueba que los puertos `8897` y `8896` estén libres.
  `medir_arranque.sh` reintenta y reporta el error en `arranque.txt`.
- **No existe el backend congelado**: genera uno con
  `npm run backend:congelar`; mientras tanto solo se mide el intérprete.
- **`PESO / archivos` en REVISAR**: `du` puede variar algunos MB según el
  sistema de archivos. El modo normal acepta ±5 %; compara también con
  `du -sm` y `find … | wc -l` manualmente.
- **`--estricto` marca REVISAR con arranque de 0,9 s**: es correcto; el PDF
  exige 1,0–1,5 s y esa corrida fue más rápida. Para la demo usa el modo normal
  (`--margenes`), que acepta 0,3–2,0 s.
- **Resultado PARCIAL**: revisa el motivo; normalmente es
  `--sin-cobertura`, `--sin-arranque` o Node no disponible. No es un fallo,
  pero tampoco es verde.
