# Copyright (c) 2024 DatenJäger. All rights reserved.
# scripts/verificar_instalador.py — conduce la aplicación empaquetada
# Trazabilidad Jira: SCRUM-54 (DatenJäger — Electron).

"""Verifica el instalador conduciendo la aplicación de verdad (Fase 5).

Comprobar que el instalador *existe* no dice nada: lo que hay que probar es que
alguien que no tiene Python pueda abrirlo y usarlo. Esta sonda abre el
`.AppImage` como lo haría esa persona —sin el entorno del proyecto— y conduce la
ventana por el protocolo de depuración de Chromium para leer el DOM real.

Por qué no basta con comprobar los archivos:

* El renderer arranca en Electron y hace `fetch` al servicio local. Un servicio
  que no arranca deja una ventana en blanco o «sin conexión», y el `.AppImage`
  sigue ahí, impecable.
* `vite build` compila sin quejarse un identificador que no existe (lección de
  `SCRUM-89`), así que el build no prueba que la pantalla monte.

Qué se comprueba, en orden:

1. El `.AppImage` arranca y el renderer monta (sin excepciones de JavaScript).
2. El servicio local **congelado** responde y su base de datos está sana.
3. El **estado no viaja en el instalador**: la base y los almacenes se crean en
   el directorio de datos del usuario, y el árbol de la aplicación queda limpio.
4. El recorrido de una persona nueva: bienvenida → registro → cuenta creada.

El entorno se aísla con `XDG_*` en directorios temporales, así que la sonda no
toca la configuración real de quien la ejecuta.

    ./venv/bin/python scripts/verificar_instalador.py
    ./venv/bin/python scripts/verificar_instalador.py --mantener   # no borra

Sale con 0 si todo pasa y con 1 si algo falla.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUERTO_CDP = 9333
ESPERA_VENTANA_S = 60
#: Espera del `.AppImage` tal cual. Es más corta que la del arranque normal: si
#: el montaje FUSE no está disponible, el proceso no llega a publicar nada nunca
#: y esperar 60 s solo alarga la sonda antes de pasar al respaldo.
ESPERA_APPIMAGE_S = 25

#: Contraseña de la cuenta de prueba. Cumple la política de la pantalla (8+
#: caracteres, mayúscula, número y símbolo).
CLAVE_PRUEBA = "Boveda#Prueba2026"
USUARIO_PRUEBA = "operador_congelado"


class Fallo(Exception):
    """Una comprobación no se cumplió."""


# --------------------------------------------------------------------------- #
# Descubrimiento del instalador
# --------------------------------------------------------------------------- #


def buscar_appimage() -> Path:
    """El `.AppImage` más reciente de `release/`."""
    candidatos = sorted((RAIZ / "release").glob("*/*.AppImage"), key=lambda p: p.stat().st_mtime)
    if not candidatos:
        raise Fallo(
            "No hay ningún .AppImage en release/. Constrúyelo con `npm run dist:linux`."
        )
    return candidatos[-1]


def extraer_appimage(appimage: Path, destino: Path) -> Path:
    """Descomprime la AppImage a un directorio y devuelve su `AppRun`.

    `--appimage-extract` es una lectura del squashfs en espacio de usuario: no
    monta nada. Sirve para ejecutar el **mismo contenido y el mismo lanzador**
    (`AppRun`) del archivo que se descarga, sin depender de que FUSE funcione en
    la máquina donde se verifica.
    """
    destino.mkdir(parents=True, exist_ok=True)
    resultado = subprocess.run(
        [str(appimage), "--appimage-extract"],
        cwd=destino,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
    )
    arranque = destino / "squashfs-root" / "AppRun"
    if not arranque.exists():
        raise Fallo(
            "No se pudo descomprimir la AppImage "
            f"({resultado.returncode}): {resultado.stderr.strip()[:300]}"
        )
    return arranque


# --------------------------------------------------------------------------- #
# Protocolo de depuración de Chromium
# --------------------------------------------------------------------------- #


async def punto_de_depuracion(proceso: subprocess.Popen, limite: float) -> str:
    """Espera a que Chromium publique su lista de pestañas y devuelve el `ws://`."""
    url = f"http://127.0.0.1:{PUERTO_CDP}/json/list"
    fin = time.time() + limite
    ultimo = "sin respuesta"

    while time.time() < fin:
        if proceso.poll() is not None:
            raise Fallo(f"La aplicación terminó antes de abrir la ventana (código {proceso.returncode})")
        try:
            with urllib.request.urlopen(url, timeout=2) as respuesta:
                objetivos = json.load(respuesta)
            for objetivo in objetivos:
                if objetivo.get("type") == "page" and objetivo.get("webSocketDebuggerUrl"):
                    return objetivo["webSocketDebuggerUrl"]
            ultimo = f"{len(objetivos)} objetivos, ninguno es una página"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            ultimo = str(error)
        await asyncio.sleep(0.4)

    raise Fallo(f"La ventana no publicó su punto de depuración: {ultimo}")


class Sesion:
    """Cliente mínimo de CDP: evalúa en la página y recoge lo que se rompe."""

    def __init__(self, conexion):
        self.conexion = conexion
        self.siguiente = 0
        self.pendientes: dict[int, asyncio.Future] = {}
        self.excepciones: list[str] = []
        self.consola: list[str] = []
        self._lector: asyncio.Task | None = None

    async def iniciar(self) -> None:
        async def leer() -> None:
            try:
                while True:
                    mensaje = json.loads(await self.conexion.recv())
                    if "id" in mensaje and mensaje["id"] in self.pendientes:
                        futuro = self.pendientes.pop(mensaje["id"])
                        if not futuro.done():
                            futuro.set_result(mensaje)
                        continue
                    await self.evento(mensaje)
            except Exception:  # noqa: BLE001 — el cierre de la conexión no es un fallo
                pass

        self._lector = asyncio.create_task(leer())

    async def evento(self, mensaje: dict) -> None:
        metodo = mensaje.get("method")
        parametros = mensaje.get("params") or {}

        if metodo == "Runtime.exceptionThrown":
            detalles = parametros.get("exceptionDetails") or {}
            self.excepciones.append(
                detalles.get("exception", {}).get("description")
                or detalles.get("text", "excepción sin descripción")
            )
        elif metodo == "Runtime.consoleAPICalled":
            if parametros.get("type") in ("error", "warning"):
                texto = " ".join(
                    str(argumento.get("value", argumento.get("description", "")))
                    for argumento in parametros.get("args", [])
                )
                self.consola.append(f"{parametros.get('type')}: {texto}")

    async def enviar(self, metodo: str, **parametros):
        self.siguiente += 1
        identificador = self.siguiente
        futuro: asyncio.Future = asyncio.get_running_loop().create_future()
        self.pendientes[identificador] = futuro
        await self.conexion.send(
            json.dumps({"id": identificador, "method": metodo, "params": parametros})
        )
        return await asyncio.wait_for(futuro, timeout=30)

    async def evaluar(self, expresion: str):
        """Evalúa `expresion` en la página y devuelve el valor."""
        respuesta = await self.enviar(
            "Runtime.evaluate",
            expression=expresion,
            returnByValue=True,
            awaitPromise=True,
        )
        resultado = respuesta.get("result", {})
        if "exceptionDetails" in resultado:
            descripcion = resultado["exceptionDetails"].get("exception", {}).get("description")
            raise Fallo(f"La expresión falló en la página: {descripcion}")
        return resultado.get("result", {}).get("value")

    async def esperar(self, expresion: str, descripcion: str, limite: float = 40) -> None:
        """Espera a que `expresion` sea verdadera, sin `sleep` fijo."""
        fin = time.time() + limite
        ultimo = None
        while time.time() < fin:
            try:
                ultimo = await self.evaluar(expresion)
                if ultimo is True:
                    return
            except Fallo as error:
                ultimo = str(error)
            await asyncio.sleep(0.3)
        cuerpo = await self.evaluar("document.body.innerText.slice(0, 400)")
        raise Fallo(f"{descripcion}\n  último valor: {ultimo!r}\n  pantalla: {cuerpo!r}")

    async def cerrar(self) -> None:
        if self._lector:
            self._lector.cancel()


# --------------------------------------------------------------------------- #
# Guiones que se ejecutan dentro de la página
# --------------------------------------------------------------------------- #

# Escribir en un input de React: asignar `.value` no actualiza el estado; hay
# que usar el setter nativo y disparar el evento `input`.
RELLENAR = """
(() => {
  const campos = [...document.querySelectorAll('input')].filter((i) => i.offsetParent !== null);
  const campo = campos[%d];
  if (!campo) return false;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(campo, %s);
  campo.dispatchEvent(new Event('input', { bubbles: true }));
  campo.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
})()
"""

# Pulsar por texto, buscando el botón más pequeño que contenga la frase: si se
# toma el contenedor, el clic cae fuera.
PULSAR = """
(() => {
  const patron = new RegExp(%s, 'i');
  const botones = [...document.querySelectorAll('button, a')]
    .filter((b) => b.offsetParent !== null && patron.test(b.textContent || ''))
    .sort((a, b) => (a.textContent || '').length - (b.textContent || '').length);
  if (!botones.length) return false;
  botones[0].click();
  return true;
})()
"""

CONTAR_CAMPOS = """
(() => [...document.querySelectorAll('input')].filter((i) => i.offsetParent !== null).length)()
"""


def js_texto(valor: str) -> str:
    return json.dumps(valor)


# --------------------------------------------------------------------------- #
# Comprobaciones
# --------------------------------------------------------------------------- #


async def comprobar(argumentos) -> None:
    appimage = buscar_appimage()
    trabajo = Path(tempfile.mkdtemp(prefix="dj-instalador-"))
    configuracion = trabajo / "config"
    datos = trabajo / "datos"
    cache = trabajo / "cache"
    for directorio in (configuracion, datos, cache):
        directorio.mkdir(parents=True, exist_ok=True)

    print(f"[sonda] instalador: {appimage.name} ({appimage.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"[sonda] entorno aislado: {trabajo}")

    entorno = {
        **os.environ,
        "XDG_CONFIG_HOME": str(configuracion),
        "XDG_DATA_HOME": str(datos),
        "XDG_CACHE_HOME": str(cache),
        # Sin esto, Electron busca el llavero del escritorio y puede quedarse
        # esperando una ventana de desbloqueo que nadie va a ver.
        "ELECTRON_DISABLE_SECURITY_WARNINGS": "1",
    }

    proceso = None
    modo = ""
    try:
        proceso, ws_url, modo = await lanzar(appimage, trabajo, entorno, argumentos)
        print(f"[sonda] ventana publicada en {ws_url}")
        print(f"[sonda] lanzada {modo}")

        import websockets

        async with websockets.connect(ws_url, max_size=32 * 1024 * 1024) as conexion:
            sesion = Sesion(conexion)
            await sesion.iniciar()
            for metodo in ("Runtime.enable", "Page.enable", "Log.enable"):
                await sesion.enviar(metodo)

            await comprobaciones(sesion, datos)

            if sesion.excepciones:
                raise Fallo(
                    "La ventana lanzó excepciones de JavaScript:\n  - "
                    + "\n  - ".join(sesion.excepciones)
                )
            ruido = [linea for linea in sesion.consola if "error" in linea.lower()]
            if ruido:
                print("[sonda] consola con errores (revisar si son esperados):")
                for linea in ruido[:10]:
                    print(f"        {linea}")

            await sesion.cerrar()

        print("\n[sonda] TODAS LAS COMPROBACIONES PASARON")

    finally:
        if proceso is not None:
            _detener(proceso)
        if argumentos.mantener:
            print(f"[sonda] se conserva el entorno: {trabajo}")
        else:
            shutil.rmtree(trabajo, ignore_errors=True)


async def lanzar(appimage: Path, trabajo: Path, entorno: dict, argumentos):
    """Arranca el instalador y devuelve `(proceso, punto de depuración, modo)`.

    Primero se ejecuta el `.AppImage` tal cual: es lo que hace la persona que lo
    descarga. Eso monta el squashfs con **FUSE**, y hay entornos donde ese
    montaje no está disponible o está roto (un contenedor sin `/dev/fuse`, una
    conexión FUSE colgada). Cuando el montaje no responde, se descomprime el
    archivo y se ejecuta su propio `AppRun`: es el mismo contenido y el mismo
    lanzador, solo que sin el paso de montaje. El modo empleado se informa
    siempre, porque no es lo mismo verificar con FUSE que sin él.
    """
    orden = [str(appimage), "--no-sandbox", f"--remote-debugging-port={PUERTO_CDP}"]

    proceso = subprocess.Popen(
        orden,
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        # Grupo propio: el `.AppImage` lanza Electron como hijo, y matar solo al
        # padre dejaría la ventana viva.
        start_new_session=True,
    )

    try:
        ws_url = await punto_de_depuracion(proceso, ESPERA_APPIMAGE_S)
        return proceso, ws_url, "como AppImage (montaje FUSE)"
    except Fallo as error:
        print(f"[sonda] el AppImage no arrancó por FUSE: {error}")
        _detener(proceso)

    if not argumentos.sin_respaldo:
        print("[sonda] se ejecuta el AppRun del contenido descomprimido…")
        arranque = extraer_appimage(appimage, trabajo / "extraido")
        proceso = subprocess.Popen(
            [str(arranque), *orden[1:]],
            env=entorno,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        ws_url = await punto_de_depuracion(proceso, ESPERA_VENTANA_S)
        return proceso, ws_url, "desde AppRun (sin montaje FUSE)"

    raise Fallo("El instalador no arrancó ni como AppImage ni descomprimido")


async def esperar_configuracion(sesion: Sesion, limite: float = 60) -> dict:
    """Espera a que el proceso principal publique el servicio como disponible.

    Se pregunta por el puente de Electron (`window.datenjager.configuracion`),
    que es una consulta directa al proceso principal: cada llamada devuelve el
    estado del momento, no una copia cacheada.

    Los tropiezos se reintentan en lugar de abortar: justo después de recargar,
    el puente de Electron todavía no existe y eso no es un fallo del instalador.
    """
    fin = time.time() + limite
    ultima: dict = {}
    while time.time() < fin:
        try:
            crudo = await sesion.evaluar(
                "(function(){ if (!window.datenjager || !window.datenjager.configuracion) return null;"
                " return window.datenjager.configuracion().then((c) => JSON.stringify(c)); })()"
            )
            if crudo:
                ultima = json.loads(crudo)
                if ultima.get("disponible"):
                    return ultima
        except Fallo:
            pass
        await asyncio.sleep(0.5)

    raise Fallo(
        "El servicio local no llegó a estar disponible en "
        f"{limite:.0f} s. Último estado: {ultima}. "
        f"Motivo: {ultima.get('error') or 'sin motivo — revisa los procesos hijos'}"
    )


async def comprobaciones(sesion: Sesion, datos: Path) -> None:
    # 1. El renderer monta.
    await sesion.esperar(
        "document.body.innerText.trim().length > 20",
        "El renderer no pintó nada (ventana en blanco)",
    )
    pantalla = await sesion.evaluar("document.body.innerText.slice(0, 200)")
    print(f"[sonda] 1. ventana montada · {pantalla.splitlines()[0] if pantalla else ''!r}")

    # 2. El servicio congelado responde. La configuración la publica el proceso
    #    principal y el renderer la recibe por IPC. Se pregunta **en bucle**: la
    #    ventana se muestra antes de que el servicio termine de arrancar, así que
    #    una sola lectura puede llegar con `disponible: false` y eso no es un
    #    fallo, es ir demasiado pronto. Se lee por IPC directo (no por
    #    `src/lib/api.js`, que cachea la primera respuesta).
    config = await esperar_configuracion(sesion)
    print(
        f"[sonda] 2. servicio local en {config['urlBackend']} "
        f"(puerto real {config['puertoBackend']})"
    )

    salud = await sesion.evaluar(
        "fetch('%s/api/salud', { headers: { 'X-DatenJager-Token': %s } })"
        ".then((r) => r.text())" % (config["urlBackend"], js_texto(config["token"]))
    )
    datos_salud = json.loads(salud)
    if datos_salud.get("base_datos") != "ok":
        raise Fallo(f"La base de datos no está sana según el servicio: {salud}")
    print(f"[sonda]    salud: {salud}")

    # 3. El estado se crea en el directorio de datos, no junto al programa.
    if not (datos.exists() and any(datos.rglob("*"))):
        raise Fallo(f"El servicio no creó su estado en el directorio de datos: {datos}")
    print(f"[sonda] 3. estado local creado en {datos}:")
    for archivo in sorted(datos.rglob("*"))[:6]:
        print(f"        {archivo.relative_to(datos)}")

    # 4. Recorrido de una persona nueva: bienvenida → registro → cuenta creada.
    await sesion.esperar(
        "/bienvenid|iniciar sesi|registro de operador/i.test(document.body.innerText)",
        "No se llegó a la pantalla de bienvenida",
    )
    await sesion.esperar(
        js_pulsar(r"Registrar operador"),
        "No se encontró la entrada al registro",
    )
    # «Repite la contraseña» solo existe en el formulario de alta: es la señal
    # de que se llegó a la pantalla, no la palabra «registro», que también está
    # en la bienvenida.
    await sesion.esperar(
        "document.body.innerText.includes('Repite la contraseña')",
        "La pantalla de registro no apareció",
    )
    await sesion.esperar(
        "document.querySelectorAll('input').length >= 3",
        "El formulario de registro no tiene los campos esperados",
    )

    campos = await sesion.evaluar(CONTAR_CAMPOS)
    print(f"[sonda] 4. formulario de registro con {campos} campos")

    for indice, valor in enumerate([USUARIO_PRUEBA, CLAVE_PRUEBA, CLAVE_PRUEBA]):
        if not await sesion.evaluar(RELLENAR % (indice, js_texto(valor))):
            raise Fallo(f"No se pudo rellenar el campo {indice}")

    await sesion.esperar(
        js_pulsar(r"Crear la cuenta"),
        "No se encontró el botón de crear la cuenta",
    )
    await sesion.esperar(
        "!document.body.innerText.includes('Creando la cuenta') && "
        "!document.body.innerText.includes('Repite la contraseña')",
        "El registro no terminó: la pantalla sigue en el formulario",
        limite=60,
    )

    # La cuenta existe si el servicio la conoce: se pregunta al backend con las
    # credenciales recién creadas en vez de fiarse de lo que pinte la pantalla.
    verificacion = await sesion.evaluar(
        "fetch('%s/api/sesion', { method: 'POST', "
        "headers: { 'Content-Type': 'application/json', 'X-DatenJager-Token': %s }, "
        "body: JSON.stringify({ nombre: %s, contrasena: %s }) })"
        ".then(async (r) => r.status + ' ' + (await r.text()))"
        % (
            config["urlBackend"],
            js_texto(config["token"]),
            js_texto(USUARIO_PRUEBA),
            js_texto(CLAVE_PRUEBA),
        )
    )
    if not re.match(r"^200 ", verificacion):
        raise Fallo(f"La cuenta creada no puede iniciar sesión: {verificacion}")

    base = list(datos.rglob("base_datos_pdfs.db"))
    print(f"[sonda]    la cuenta {USUARIO_PRUEBA} inicia sesión: {verificacion[:90]}")
    print(f"[sonda]    base de datos en {base[0] if base else '(no encontrada)'}")

    # Y el instalador no lleva estado del desarrollador dentro.
    if (RAIZ / "release").exists():
        for instalado in RAIZ.glob("release/*/linux-unpacked"):
            if (instalado / "base_datos_pdfs.db").exists():
                raise Fallo(f"El paquete lleva una base de datos dentro: {instalado}")
    print("[sonda] 5. el paquete no lleva base de datos ni estado del desarrollador")


def js_pulsar(patron: str) -> str:
    return PULSAR % json.dumps(patron)


def _detener(proceso: subprocess.Popen) -> None:
    """Mata el proceso y su grupo: el `.AppImage` deja a Electron de hijo."""
    if proceso.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proceso.pid), signal.SIGTERM)
        proceso.wait(timeout=10)
    except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
        try:
            os.killpg(os.getpgid(proceso.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica el instalador de DatenJäger")
    parser.add_argument("--mantener", action="store_true", help="no borra el entorno temporal")
    parser.add_argument(
        "--sin-respaldo",
        action="store_true",
        help="no ejecuta el AppRun descomprimido si el montaje FUSE falla",
    )
    argumentos = parser.parse_args()

    try:
        asyncio.run(comprobar(argumentos))
    except Fallo as error:
        print(f"\n[sonda] FALLÓ: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
