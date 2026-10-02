# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/modelos.py - conexión de modelos de IA (SCRUM-64)

"""Configuración del proveedor de modelos que usa el asistente.

El panel de conexión del frontend necesita tres datos —proveedor, modelo y
punto de conexión— y, opcionalmente, una clave de API. Los tres primeros no
son secretos; la clave sí.

**Dónde vive la clave.** Nunca en el renderer y nunca en claro en disco: se
guarda cifrada con AES-256-GCM en `modelos/config.json`, dentro de un
directorio con permisos `0700`, y la clave del almacén vive en
`modelos/llave.bin` con permisos `0600` — el mismo patrón que ya usa
`backend/tokens.py` para los tokens de confianza. El servicio solo informa de
*si* hay clave configurada, jamás la devuelve.

**Alcance real de esta protección.** Cifrar en disco evita que la clave quede
en un respaldo, en el historial de git o al copiar el proyecto. No protege
frente a quien pueda leer todo el directorio personal del usuario: si puede
leer `llave.bin`, puede descifrar la clave. Para eso haría falta el llavero
del sistema operativo.

**Alcance funcional.** Esta pieza es la pantalla y su almacén; el proveedor
efectivo sigue siendo el que ya usaba el chatbot (Gemini por API), y el
modelo elegido se antepone a su lista de candidatos. Añadir proveedores
locales es la evaluación `SCRUM-37` a `SCRUM-39`, aparcada a propósito.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from backend.errors import DatosInvalidosError
from backend.services import proveedores
from encryption import EncryptionManager

#: Directorio del almacén y de su clave, con permisos restringidos.
NOMBRE_DIRECTORIO = "modelos"
NOMBRE_ARCHIVO = "config.json"
NOMBRE_CLAVE = "llave.bin"
LONGITUD_CLAVE = 32

#: Archivo de entorno del proyecto, que el panel mantiene al día.
NOMBRE_ENV = ".env"

#: Cabecera del `.env` cuando lo crea el panel. Se respeta la que ya exista.
CABECERA_ENV = (
    "# DatenJäger — Variables de entorno\n"
    "# NO subir este archivo a control de versiones\n"
    "# Lo mantiene el panel de conexión de modelos.\n"
)

#: Campos que no son secretos y se guardan en claro en el almacén.
CAMPOS_PUBLICOS = ("proveedor", "modelo", "endpoint")

#: Salud de la conexión, para la franja de telemetría. No es un adorno: cada
#: valor tiene detrás un hecho comprobado, no una suposición.
SALUD_SIN_CONFIGURAR = "sin_configurar"  #: no hay credencial
SALUD_SIN_VERIFICAR = "sin_verificar"    #: hay credencial, pero no se ha probado
SALUD_OK = "ok"                          #: la última prueba real pasó
SALUD_ERROR = "error"                    #: la última prueba real falló

#: Tipos de prueba que se registran.
PRUEBA_CONEXION = "conexion"   #: la credencial sirve (listado de modelos)
PRUEBA_RESPUESTA = "respuesta" #: el modelo genera texto

#: El catálogo lo manda `backend/services/proveedores.py`. Estos nombres se
#: conservan porque el resto del sistema ya los importaba de aquí.
PROVEEDOR_POR_DEFECTO = proveedores.PROVEEDOR_POR_DEFECTO
VARIABLE_ENTORNO = proveedores.variable_de(PROVEEDOR_POR_DEFECTO)


def modelo_por_defecto(proveedor: str) -> str:
    """Primer modelo sugerido del proveedor, o cadena vacía si no tiene."""
    ficha = proveedores.descrito(proveedor)
    modelos = ficha["modelos"] if ficha else ()
    return modelos[0] if modelos else ""


# --------------------------------------------------------------------------- #
# Archivo de entorno
# --------------------------------------------------------------------------- #


def _ruta_env(raiz: str | os.PathLike) -> Path:
    return Path(raiz) / NOMBRE_ENV


def _asegurar_permisos_env(raiz: str | os.PathLike) -> bool:
    """Deja el `.env` en `0600` si estaba legible por otros. Devuelve si lo cambió.

    El `.env` lleva la credencial **en claro** —es de donde la lee el asistente—
    así que sus permisos son parte de la protección, no un detalle. Escribirlo ya
    fuerza `0600`, pero un `.env` que existía de antes conserva los suyos: el
    caso real es un archivo creado a mano con `0644`, legible por cualquier
    usuario del equipo. Se corrige al consultarlo, que es cuando el panel lo
    mira, y es idempotente.
    """
    ruta = _ruta_env(raiz)
    if not ruta.exists():
        return False
    try:
        actuales = ruta.stat().st_mode & 0o777
        if actuales & 0o077:
            os.chmod(ruta, 0o600)
            return True
    except OSError:
        return False
    return False


def _leer_env(raiz: str | os.PathLike, variable: str) -> Optional[str]:
    """Valor de ``variable`` en el `.env`.

    Distingue tres casos, y la diferencia importa:

    * el archivo **no existe** → `None`, y se consulta el entorno del proceso;
    * el archivo existe y **define** la variable → su valor;
    * el archivo existe y **no la define** → `""`, que significa «no hay clave».
      No se cae al entorno del proceso a propósito: tras «Quitar la
      credencial», un proceso que cargó la clave al arrancar la seguiría viendo
      en `os.environ`, y quitar no quitaría nada hasta reiniciar.
    """
    ruta = _ruta_env(raiz)
    if not ruta.exists():
        return None

    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for linea in lineas:
        desnuda = linea.strip()
        if desnuda.startswith(f"{variable}="):
            return desnuda.split("=", 1)[1].strip()
    return ""


def _clave_del_entorno(raiz: str | os.PathLike, variable: str) -> str:
    """Credencial vigente para esa variable, con el `.env` por delante.

    `os.getenv` devuelve lo que el proceso cargó **al arrancar** —`config.py`
    lee el `.env` una sola vez—, así que una clave escrita desde el panel no
    surtiría efecto hasta reiniciar. Para que la activación sin reinicio sea
    real, manda el archivo; el entorno del proceso solo se consulta cuando el
    proyecto no tiene `.env` (pruebas, o una variable exportada a mano).
    """
    del_archivo = _leer_env(raiz, variable)
    if del_archivo is not None:
        return del_archivo
    return os.getenv(variable, "").strip()


def _actualizar_env(raiz: str | os.PathLike, proveedor: str, valor: Optional[str]) -> None:
    """Deja en el `.env` **solo** la credencial del proveedor indicado.

    El asistente resuelve la credencial desde el entorno, así que guardarla solo
    en el almacén cifrado no bastaría: hay que dejarla también aquí, que es de
    donde la lee. Se conserva el resto del archivo (comentarios y otras
    variables) y se escribe con permisos `0600`, porque es un secreto en claro.

    Se retiran las credenciales de los **demás** proveedores a propósito: al
    cambiar de proveedor, dejar la clave anterior en el entorno haría que el
    panel dijera que hay credencial cuando la activa ya es otra.

    `valor=None` deja el `.env` sin ninguna credencial: es lo que hace «Quitar
    la credencial». Si no se retirara, el entorno seguiría teniendo la clave
    anterior y el panel diría que hay credencial después de haberla quitado.
    """
    ruta = _ruta_env(raiz)
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
    except OSError:
        lineas = []

    if not lineas:
        lineas = CABECERA_ENV.rstrip("\n").splitlines()

    variables = proveedores.variables_de_credenciales()
    variable = proveedores.variable_de(proveedor) or proveedores.variable_de(PROVEEDOR_POR_DEFECTO)
    nueva = f"{variable}={valor}" if valor else None

    salida: list[str] = []
    puesto = False

    for linea in lineas:
        desnuda = linea.strip()
        if any(desnuda.startswith(f"{candidata}=") for candidata in variables):
            if nueva and desnuda.startswith(f"{variable}=") and not puesto:
                salida.append(nueva)
                puesto = True
            # Con `nueva=None`, o si es la credencial de otro proveedor, la
            # línea simplemente se descarta.
            continue
        salida.append(linea)

    if nueva and not puesto:
        salida.append(nueva)

    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    # `O_CREAT` solo aplica el modo cuando **crea** el archivo: si ya existía
    # (el `.env` del proyecto suele existir), conservaría sus permisos y la
    # clave quedaría legible por otros usuarios. Se fuerzan aquí.
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(salida).rstrip("\n") + "\n")


# --------------------------------------------------------------------------- #
# Almacén
# --------------------------------------------------------------------------- #


def _directorio(raiz: str | os.PathLike) -> Path:
    """Directorio del almacén, creado con permisos restringidos si falta."""
    directorio = Path(raiz) / NOMBRE_DIRECTORIO
    directorio.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directorio


def _ruta_config(raiz: str | os.PathLike) -> Path:
    return _directorio(raiz) / NOMBRE_ARCHIVO


def _clave_del_almacen(raiz: str | os.PathLike) -> bytes:
    """Clave local del almacén: se crea la primera vez con permisos 0600."""
    ruta = _directorio(raiz) / NOMBRE_CLAVE
    if ruta.exists():
        return ruta.read_bytes()

    import secrets

    clave = secrets.token_bytes(LONGITUD_CLAVE)
    # `os.open` con O_EXCL evita la carrera de dos procesos creando la clave.
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as archivo:
        archivo.write(clave)
    return clave


def _leer(raiz: str | os.PathLike) -> dict[str, Any]:
    """Contenido del almacén, o un dict vacío si todavía no existe."""
    ruta = _ruta_config(raiz)
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _escribir(raiz: str | os.PathLike, datos: dict[str, Any]) -> None:
    """Guarda el almacén con permisos 0600."""
    ruta = _ruta_config(raiz)
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    # Igual que en el `.env`: si el archivo ya existía con permisos más amplios,
    # `O_CREAT` no los corrige.
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Lectura
# --------------------------------------------------------------------------- #


def _proveedor_por_entorno(raiz: str | os.PathLike) -> Optional[str]:
    """Proveedor deducido de la credencial que ya esté en el `.env`.

    Cubre el caso de una clave puesta a mano en el `.env`, o heredada de una
    versión anterior: la aplicación la reconoce en vez de decir que no hay nada
    configurado.
    """
    for ficha in proveedores.catalogo():
        if _clave_del_entorno(raiz, ficha["variable_entorno"]):
            return ficha["clave"]
    return None


def _proveedor_guardado(raiz: str | os.PathLike) -> str:
    """Proveedor vigente: lo guardado, lo que se deduzca del `.env`, o el de reserva."""
    datos = _leer(raiz)
    return (
        datos.get("proveedor")
        or _proveedor_por_entorno(raiz)
        or proveedores.PROVEEDOR_POR_DEFECTO
    )


def clave(raiz: str | os.PathLike) -> Optional[str]:
    """Credencial vigente del proveedor configurado.

    Manda el `.env` —es lo que permite activar sin reiniciar—; si no la define,
    se usa la del almacén cifrado.
    """
    proveedor = _proveedor_guardado(raiz)
    variable = proveedores.variable_de(proveedor)

    del_entorno = _clave_del_entorno(raiz, variable)
    if del_entorno:
        return del_entorno

    datos = _leer(raiz)
    cifrada = datos.get("api_key")
    if not cifrada:
        return None

    try:
        return EncryptionManager.decrypt_str_with_key(cifrada, _clave_del_almacen(raiz))
    except Exception:
        # Una clave del almacén cambiada o un archivo corrupto no deben tumbar
        # el asistente: se comporta como si no hubiera credencial.
        return None


def modelos_conocidos(raiz: str | os.PathLike) -> list[str]:
    """Modelos que la cuenta tiene de verdad, según la última prueba de conexión.

    Es la lista real que devolvió el proveedor. Sirve para dos cosas: ofrecerlos
    en el panel —en vez de solo los del catálogo— y usarlos como respaldo cuando
    el modelo elegido falla.
    """
    crudos = _leer(raiz).get("modelos_conocidos")
    return [str(modelo) for modelo in crudos] if isinstance(crudos, list) else []


def modelos_candidatos(raiz: str | os.PathLike) -> list[str]:
    """Modelos a probar, en orden: el elegido, los de la cuenta y los del catálogo.

    El orden importa: primero lo que el usuario eligió, después lo que su cuenta
    tiene comprobado y, al final, los alias estables del catálogo. Así, si el
    modelo elegido se retiró —que es exactamente lo que pasó con
    `gemini-2.0-flash`— el asistente cae en uno que sí existe en vez de
    devolver un 503.
    """
    elegido = estado(raiz)["modelo"]
    orden: list[str] = []
    # El orden importa. Primero lo elegido; después los **alias del catálogo**,
    # que están curados y no caducan; y al final la lista cruda de la cuenta.
    # La cuenta trae de todo y sin curar: fue caer en un `gemma` de ahí lo que
    # puso a la vista su razonamiento, porque los gemma escriben su
    # planificación como texto en vez de devolverla marcada como pensamiento.
    for nombre in [
        elegido,
        *proveedores.modelos_de(_proveedor_guardado(raiz)),
        *[modelo for modelo in modelos_conocidos(raiz) if _conversa(modelo)],
    ]:
        limpio = (nombre or "").strip()
        if limpio and limpio not in orden:
            orden.append(limpio)
    return orden


def ultima_prueba(raiz: str | os.PathLike) -> Optional[dict[str, Any]]:
    """Resultado de la última prueba real, o `None` si nunca se probó."""
    datos = _leer(raiz).get("ultima_prueba")
    return datos if isinstance(datos, dict) and "ok" in datos else None


def _hay_credencial(raiz: str | os.PathLike) -> bool:
    """Si hay credencial, del `.env` o del almacén.

    Se calcula aparte porque ``salud`` y ``estado`` lo necesitan y no pueden
    llamarse entre sí: ``estado`` incluye la salud, así que la salud no puede
    pedir el estado entero —sería una recursión infinita—.
    """
    variable = proveedores.variable_de(_proveedor_guardado(raiz))
    return bool(_clave_del_entorno(raiz, variable)) or bool(_leer(raiz).get("api_key"))


def salud(raiz: str | os.PathLike) -> str:
    """Estado de la conexión, para la franja de telemetría.

    **No se pone verde por tener una credencial.** Una clave puede estar
    guardada, ser del proveedor equivocado y no servir para nada; pintar verde
    ahí es mentir. Verde solo significa «la última prueba real pasó»:

    * sin credencial → ``sin_configurar``;
    * con credencial pero sin probar → ``sin_verificar``;
    * última prueba correcta → ``ok``;
    * última prueba fallida → ``error``.
    """
    if not _hay_credencial(raiz):
        return SALUD_SIN_CONFIGURAR
    prueba = ultima_prueba(raiz)
    if not prueba:
        return SALUD_SIN_VERIFICAR
    return SALUD_OK if prueba.get("ok") else SALUD_ERROR


def registrar_prueba(raiz: str | os.PathLike, resultado: dict[str, Any],
                     tipo: str) -> dict[str, Any]:
    """Anota el resultado de una prueba real y lo deja en el almacén.

    Se guarda el desenlace, no solo el mensaje: es lo que permite que la franja
    de telemetría diga la verdad en la sesión siguiente. Si la prueba fue la de
    conexión y salió bien, se guarda además la lista de modelos que la cuenta
    tiene de verdad.

    Returns:
        El resultado, tal cual llegó, para que el llamante lo devuelva.
    """
    datos = _leer(raiz)
    datos["ultima_prueba"] = {
        "tipo": tipo,
        "ok": bool(resultado.get("ok")),
        "mensaje": str(resultado.get("mensaje") or "")[:300],
        "momento": _ahora(),
    }
    if tipo == PRUEBA_CONEXION and resultado.get("ok"):
        disponibles = [
            str(modelo) for modelo in (resultado.get("modelos_disponibles") or [])
        ][:40]
        if disponibles:
            datos["modelos_conocidos"] = disponibles
            # Si el modelo guardado ya no existe en la cuenta, se cambia por uno
            # que sí. Es lo que convierte «Probar conexión» en algo que arregla el
            # problema y no solo en algo que lo informa: el caso real fue un
            # `gemini-2.0-flash` retirado devolviendo 503 en cada respuesta.
            if datos.get("modelo") not in disponibles:
                datos["modelo"] = _mejor_modelo(disponibles)
    _escribir(raiz, datos)
    return resultado


#: Marcas de modelos que no sirven para conversar. La lista de una cuenta trae
#: de todo —voz, imagen, embeddings, robótica—, y elegir el primero a ciegas
#: puede acabar en uno que no genera texto.
_MARCAS_NO_CONVERSACION = (
    "tts", "image", "imagen", "embedding", "embed", "audio", "transcribe",
    "lyria", "robotics", "computer-use", "antigravity", "veo", "aqa",
)


def _conversa(nombre: str) -> bool:
    """Si el nombre del modelo parece de conversación y no de voz o imagen."""
    return not any(marca in nombre.lower() for marca in _MARCAS_NO_CONVERSACION)


def _mejor_modelo(disponibles: list[str]) -> str:
    """El modelo más razonable de una lista para conversar.

    Prefiere un alias estable —los que no caducan— y descarta lo que no genera
    texto. Si todo parece de otro tipo, devuelve el primero: es mejor intentarlo
    que dejar la conexión sin modelo.
    """
    conversables = [nombre for nombre in disponibles if _conversa(nombre)]
    if not conversables:
        return disponibles[0]

    estables = [nombre for nombre in conversables if nombre.endswith("-latest")]
    preferidos = [nombre for nombre in (estables or conversables) if "flash" in nombre.lower()]
    return (preferidos or estables or conversables)[0]


def _ahora() -> str:
    """Marca de tiempo en ISO-8601, en hora local."""
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


def identificar(clave: str) -> dict[str, Any]:
    """Reconoce el proveedor de una clave **sin llamar a nadie**.

    Es lo que permite que el panel muestre «detectado: Google Gemini ·
    https://…» mientras el usuario escribe, antes de guardar nada. No es
    adivinar: aplica las mismas reglas del catálogo y, si ninguna reconoce la
    clave, lo dice en vez de inventarse un proveedor.
    """
    return proveedores.resolver(clave)


def estado(raiz: str | os.PathLike) -> dict[str, Any]:
    """Resumen de la conexión de modelos para el panel.

    Nunca devuelve la clave: solo si está configurada, de dónde sale y con qué
    proveedor. Incluye el catálogo, para que el panel ofrezca las opciones y
    diga qué forma tiene la clave de cada una, y la **salud real** de la
    conexión (ver ``salud``).
    """
    datos = _leer(raiz)
    proveedor = _proveedor_guardado(raiz)
    variable = proveedores.variable_de(proveedor)

    del_entorno = bool(_clave_del_entorno(raiz, variable))
    if del_entorno:
        origen = "entorno"
    elif datos.get("api_key"):
        origen = "almacen"
    else:
        origen = None

    ficha = proveedores.descrito(proveedor) or {}
    permisos_corregidos = _asegurar_permisos_env(raiz)
    salud_actual = salud(raiz)

    return {
        "proveedor": proveedor,
        "proveedor_nombre": ficha.get("nombre", proveedor),
        "estilo": proveedores.estilo_de(proveedor),
        "modelo": datos.get("modelo") or modelo_por_defecto(proveedor),
        "endpoint": datos.get("endpoint") or proveedores.endpoint_de(proveedor),
        "clave_configurada": bool(origen),
        "origen_clave": origen,
        "proveedores": proveedores.catalogo(),
        # Salud real y su evidencia, para que la franja no suponga nada.
        "salud": salud_actual,
        "ultima_prueba": ultima_prueba(raiz),
        "modelos_conocidos": modelos_conocidos(raiz),
        "identificador": proveedores.identificador_de(proveedor),
        "endpoint_editable": proveedores.endpoint_editable(proveedor),
        "permisos_env_corregidos": permisos_corregidos,
    }


# --------------------------------------------------------------------------- #
# Escritura
# --------------------------------------------------------------------------- #


def guardar(
    raiz: str | os.PathLike,
    *,
    proveedor: Optional[str] = None,
    modelo: Optional[str] = None,
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    quitar_clave: bool = False,
) -> dict[str, Any]:
    """Guarda la conexión elegida y devuelve el estado resultante.

    **Si llega una credencial, ella manda.** De su forma se deduce el proveedor
    y, con él, la URL base y la variable del `.env`; el panel no tiene que
    acertar con nada más. Un ``proveedor`` explícito solo decide cuando la
    detección no reconoce la clave.

    Una ``endpoint`` escrita manda siempre, con clave o sin ella: es la única
    forma de configurar un endpoint propio, que por definición no está en el
    catálogo. El panel no la envía cuando el proveedor la tiene fijada, así que
    en la práctica el usuario no llega a verla.

    Args:
        api_key: si llega con valor, se escribe en el `.env` del proveedor
            detectado, se cifra en el almacén y **se retiran** las credenciales
            de los demás proveedores.
        quitar_clave: deja el `.env` sin ninguna credencial y descarta la del
            almacén.

    Raises:
        DatosInvalidosError: el proveedor no está en el catálogo.
    """
    antes = _leer(raiz)
    datos = _leer(raiz)
    clave_pegada = (api_key or "").strip()

    if clave_pegada:
        resuelto = proveedores.resolver(clave_pegada, proveedor)
        elegido = resuelto["proveedor"]
        datos["proveedor"] = elegido
        if resuelto["detectado"] and resuelto["endpoint"]:
            # La clave se reconoció: su proveedor manda y la URL base la fija el
            # catálogo. Es lo que evita que el usuario tenga que saber dónde vive
            # NVIDIA. Si la clave no se reconoce —o es un endpoint propio, que por
            # definición no tiene URL conocida— la decide el llamante.
            datos["endpoint"] = resuelto["endpoint"]
        if not datos.get("modelo") or modelo:
            datos["modelo"] = (modelo or "").strip() or modelo_por_defecto(elegido)
        datos["api_key"] = EncryptionManager.encrypt_str_with_key(
            clave_pegada, _clave_del_almacen(raiz))
        # El asistente lee la credencial del entorno, así que se deja también en
        # el `.env`: guardarla solo en el almacén no la activaría.
        _actualizar_env(raiz, elegido, clave_pegada)

    else:
        if proveedor:
            proveedor = proveedor.strip()
            if not proveedores.descrito(proveedor):
                raise DatosInvalidosError(f"Proveedor desconocido: {proveedor}")
            datos["proveedor"] = proveedor
            datos["endpoint"] = proveedores.endpoint_de(proveedor)

        if modelo is not None:
            datos["modelo"] = modelo.strip()

        if quitar_clave:
            datos.pop("api_key", None)
            # Se retira del `.env` también; si no, el entorno seguiría sirviendo
            # la clave anterior y «quitar» no quitaría nada.
            _actualizar_env(
                raiz, datos.get("proveedor") or PROVEEDOR_POR_DEFECTO, None)

    # Una URL escrita manda sobre lo deducido, en las dos ramas: si no, no habría
    # forma de apuntar a un endpoint propio.
    if endpoint is not None and endpoint.strip():
        datos["endpoint"] = endpoint.strip()

    # Un cambio en la conexión invalida la prueba anterior. Si se guarda otra
    # clave, se cambia de modelo o de endpoint, el «verde» de ayer ya no
    # describe lo de hoy: la franja debe volver a «sin verificar» hasta que se
    # pruebe de nuevo, en vez de quedarse en verde por inercia.
    if _cambio_la_conexion(antes, datos):
        datos.pop("ultima_prueba", None)
        if antes.get("proveedor") != datos.get("proveedor"):
            # Los modelos de la cuenta anterior no dicen nada de la nueva.
            datos.pop("modelos_conocidos", None)

    _escribir(raiz, datos)
    return estado(raiz)


def _cambio_la_conexion(antes: dict[str, Any], despues: dict[str, Any]) -> bool:
    """Si algo que afecta a la conexión cambió entre dos lecturas del almacén."""
    for campo in (*CAMPOS_PUBLICOS, "api_key"):
        if antes.get(campo) != despues.get(campo):
            return True
    return False


# --------------------------------------------------------------------------- #
# Prueba real de la credencial
# --------------------------------------------------------------------------- #


def _listar_modelos(proveedor: str, endpoint: str, clave_actual: str,
                    tiempo_limite: float) -> dict[str, Any]:
    """Pide al proveedor su lista de modelos, en el dialecto que hable.

    Gemini usa la cabecera ``x-goog-api-key`` y devuelve ``{"models": [...]}``;
    el estilo de OpenAI —NVIDIA, OpenAI, OpenRouter— usa ``Authorization:
    Bearer`` y devuelve ``{"data": [...]}``.
    """
    base = (endpoint or proveedores.endpoint_de(proveedor)).rstrip("/")

    if proveedores.estilo_de(proveedor) == proveedores.ESTILO_GEMINI:
        peticion = urllib.request.Request(
            f"{base}/models", headers={"x-goog-api-key": clave_actual})
    else:
        peticion = urllib.request.Request(
            f"{base}/models", headers={"Authorization": f"Bearer {clave_actual}"})

    with urllib.request.urlopen(peticion, timeout=tiempo_limite) as respuesta:
        cuerpo = json.loads(respuesta.read() or b"{}")

    crudos = cuerpo.get("models") or cuerpo.get("data") or []
    return {
        "modelos": [
            str(modelo.get("name") or modelo.get("id") or "").split("/")[-1]
            for modelo in crudos
            if modelo.get("name") or modelo.get("id")
        ]
    }


def probar(raiz: str | os.PathLike, *, tiempo_limite: float = 15.0) -> dict[str, Any]:
    """Prueba la credencial y **deja anotado** el resultado.

    La anotación es lo que hace que la franja de telemetría diga la verdad: sin
    ella, «Probar conexión» solo informaría a quien lo pulsó, y el estado del
    sistema seguiría siendo una suposición. Si la prueba sale bien, además se
    guarda la lista real de modelos de la cuenta.
    """
    return registrar_prueba(
        raiz, _probar(raiz, tiempo_limite=tiempo_limite), PRUEBA_CONEXION)


def _probar(raiz: str | os.PathLike, *, tiempo_limite: float = 15.0) -> dict[str, Any]:
    """Comprueba contra el proveedor que la credencial guardada sirve.

    No adivina ni simula: hace una petición real al endpoint del proveedor y
    devuelve lo que responda. Es lo que el panel ofrece antes de ponerse a usar
    el modelo, para no descubrir una clave inválida a mitad de una conversación.

    **El mensaje distingue lo que falló.** Una credencial rechazada (401/403),
    un proveedor caído (5xx) y un problema de red no son lo mismo; decir
    «rechazó la credencial» ante un 503 lleva a buscar el problema donde no
    está. Solo el 401/403 habla de la credencial; el 5xx dice que el proveedor
    no está disponible y que la clave no se ha rechazado.

    Returns:
        Dict con ``ok``, ``mensaje`` y, cuando hay error, ``detalle`` y
        ``reintentable``.
    """
    actual = estado(raiz)
    clave_actual = clave(raiz)
    proveedor = actual["proveedor"]

    if not clave_actual:
        return {
            "ok": False,
            "mensaje": "No hay credencial configurada que probar.",
            "reintentable": False,
        }

    if not (actual["endpoint"] or proveedores.endpoint_de(proveedor)):
        # Sin URL base no hay nada que probar. Decirlo es más útil que dejar que
        # falle una petición a una dirección vacía.
        return {
            "ok": False,
            "mensaje": (
                f"{actual['proveedor_nombre']} no tiene punto de conexión configurado: "
                "indícalo en el panel para poder probarlo."
            ),
            "reintentable": False,
        }

    try:
        datos = _listar_modelos(proveedor, actual["endpoint"], clave_actual, tiempo_limite)
    except urllib.error.HTTPError as error:
        detalle = ""
        try:
            detalle = json.loads(error.read() or b"{}").get("error", {}).get("message", "")
        except Exception:
            detalle = ""

        if error.code in (401, 403):
            return {
                "ok": False,
                "mensaje": (
                    f"El proveedor rechazó la credencial ({error.code}). Revisa que la clave "
                    f"pertenezca a {actual['proveedor_nombre']} y esté activa."
                ),
                "detalle": detalle or str(error),
                "reintentable": False,
            }
        if error.code == 404:
            return {
                "ok": False,
                "mensaje": (
                    f"El proveedor no reconoce la ruta de modelos (404) en "
                    f"{actual['endpoint']}. Revisa la URL base."
                ),
                "detalle": detalle or str(error),
                "reintentable": False,
            }
        if error.code == 429:
            return {
                "ok": False,
                "mensaje": "El proveedor está limitando las peticiones (429). Espera y reintenta.",
                "detalle": detalle or str(error),
                "reintentable": True,
            }
        return {
            "ok": False,
            "mensaje": (
                f"El proveedor no está disponible ahora mismo ({error.code}). "
                "La credencial no se ha rechazado: vuelve a probar en un momento."
            ),
            "detalle": detalle or str(error),
            "reintentable": error.code >= 500,
        }
    except Exception as error:
        return {
            "ok": False,
            "mensaje": f"No se pudo contactar {actual['proveedor_nombre']}.",
            "detalle": str(error),
            "reintentable": True,
        }

    disponibles = datos["modelos"]

    # Un listado de modelos no siempre demuestra que la credencial valga: el de
    # NVIDIA es público y responde 200 con cualquier clave. Para los proveedores
    # de estilo OpenAI se comprueba además con un turno mínimo, que sí exige
    # autenticación de verdad. Gemini no lo necesita: su listado ya rechaza una
    # clave mala, y se comprobó con una clave inválida.
    if proveedores.estilo_de(proveedor) == proveedores.ESTILO_COMPATIBLE:
        comprobacion = _comprobar_turno_minimo(
            proveedor, actual["endpoint"], clave_actual, tiempo_limite, disponibles)
        if not comprobacion["ok"]:
            return comprobacion

    return {
        "ok": True,
        "mensaje": f"La credencial responde y {actual['proveedor_nombre']} la acepta.",
        "modelos_disponibles": disponibles[:40],
        "reintentable": False,
    }


def _detalle_de(error: urllib.error.HTTPError) -> str:
    """Mensaje del proveedor, si lo trae; si no, el error tal cual."""
    try:
        return json.loads(error.read() or b"{}").get("error", {}).get("message", "") or str(error)
    except Exception:
        return str(error)


def _comprobar_turno_minimo(proveedor: str, endpoint: str, clave: str,
                            tiempo_limite: float, disponibles: list[str]) -> dict[str, Any]:
    """Pide una respuesta de un token: es lo que demuestra que la clave vale.

    Listar modelos es barato pero no concluyente en todos los proveedores. Un
    turno real, en cambio, no lo contesta nadie sin una credencial válida.

    Returns:
        ``{"ok": True}`` si el proveedor contestó, o el fallo ya explicado.
    """
    ficha = proveedores.descrito(proveedor) or {}
    nombre = ficha.get("nombre", proveedor)
    base = (endpoint or proveedores.endpoint_de(proveedor)).rstrip("/")
    modelo = next((candidato for candidato in disponibles if _conversa(candidato)), "")
    if not modelo:
        # Sin un modelo de conversación no se puede comprobar: se dice, en vez de
        # dar por buena la credencial con el listado.
        return {
            "ok": False,
            "mensaje": (
                f"{nombre} no ofrece ningún modelo de conversación que usar para "
                "comprobar la credencial."
            ),
            "reintentable": False,
        }

    peticion = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps({
            "model": modelo,
            "messages": [{"role": "user", "content": "ok"}],
            "max_tokens": 1,
        }).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {clave}"},
    )

    try:
        with urllib.request.urlopen(peticion, timeout=tiempo_limite) as respuesta:
            respuesta.read()
    except urllib.error.HTTPError as error:
        detalle = _detalle_de(error)
        if error.code in (401, 403):
            return {
                "ok": False,
                "mensaje": (
                    f"El proveedor rechazó la credencial ({error.code}). El listado de "
                    f"modelos no bastaba: {nombre} lo sirve sin autenticar. Revisa que la "
                    "clave sea de este proveedor y esté activa."
                ),
                "detalle": detalle,
                "reintentable": False,
            }
        return {
            "ok": False,
            "mensaje": f"{nombre} no aceptó la comprobación ({error.code}).",
            "detalle": detalle,
            "reintentable": error.code >= 500,
        }
    except Exception as error:
        return {
            "ok": False,
            "mensaje": f"No se pudo contactar {nombre} para comprobar la credencial.",
            "detalle": str(error),
            "reintentable": True,
        }

    return {"ok": True}