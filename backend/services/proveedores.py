# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/services/proveedores.py - catálogo y detección de proveedores de IA
# Trazabilidad Jira: SCRUM-62 (DatenJäger — API / Servicios).

"""Catálogo de proveedores de modelos y detección por la forma de la clave.

La idea es que el usuario **solo pegue su credencial**: de su forma se deduce el
proveedor, y del proveedor, la URL base y la variable de entorno donde se
guarda. Nadie tiene que saber que NVIDIA vive en `integrate.api.nvidia.com/v1` ni
que Gemini usa `generativelanguage.googleapis.com`.

**Sobre la detección.** No es adivinación: cada proveedor publica sus claves con
un prefijo o sufijo reconocible, y aquí se declara cuál. Si una clave no encaja
con ninguno, se dice tal cual y se pide elegir el proveedor a mano; no se prueba
a ciegas contra varias APIs.

**Dos estilos de API.** Gemini habla su propio dialecto (`generateContent`,
cabecera `X-goog-api-key`). NVIDIA, OpenAI y OpenRouter comparten el estilo de
OpenAI (`chat/completions`, `Authorization: Bearer`), que aquí se llama
`compatible`. El servicio del asistente sabe hablar los dos.
"""

from __future__ import annotations

from typing import Any, Optional

#: Estilo de API. Decide cómo se construye la petición y cómo se lee el flujo.
ESTILO_GEMINI = "gemini"
ESTILO_COMPATIBLE = "compatible"

#: URL base de NVIDIA, que no es configurable: es su endpoint público.
ENDPOINT_NVIDIA = "https://integrate.api.nvidia.com/v1"


def _normalizar(clave: str) -> str:
    return (clave or "").strip()


def _es_gemini(clave: str) -> bool:
    """Claves de Google AI Studio / Gemini.

    Empiezan por ``AIza`` (el formato histórico) o por ``AQ`` (el que emite
    ahora AI Studio para claves de proyecto).
    """
    return clave.startswith("AIza") or clave.startswith("AQ.") or clave.startswith("AQ")


def _es_nvidia(clave: str) -> bool:
    """Claves de NVIDIA: llevan el sufijo ``nvapi`` delante."""
    return clave.startswith("nvapi-") or "nvapi" in clave[:12].lower()


def _es_openrouter(clave: str) -> bool:
    return clave.startswith("sk-or-")


def _es_anthropic(clave: str) -> bool:
    return clave.startswith("sk-ant-")


def _es_openai(clave: str) -> bool:
    return clave.startswith("sk-") and not _es_openrouter(clave) and not _es_anthropic(clave)


#: Catálogo de proveedores. El orden importa para la detección: se comprueba de
#: arriba abajo y el primero que reconozca la clave manda. Por eso los prefijos
#: más específicos (`sk-or-`, `sk-ant-`) van antes que el genérico `sk-`.
#:
#: ``identificador`` es la regla en lenguaje llano que el panel muestra junto al
#: campo de la clave, para que el usuario sepa de antemano qué forma tiene la
#: suya. ``endpoint_editable`` es falso en todos los proveedores conocidos: su
#: URL base la fija este catálogo y el usuario no debería tocarla. Solo el
#: proveedor genérico la necesita, porque su endpoint es, por definición, el que
#: no conocemos.
#:
#: **Los modelos del catálogo son alias, no versiones fijas.** `gemini-2.0-flash`
#: dejó de existir y el asistente respondía 503 «high demand» al pedírselo: una
#: versión fija se retira y deja de funcionar sin que nadie toque nada. Los alias
#: (`-latest`) apuntan siempre a la versión vigente de esa familia, así que no
#: caducan. Las versiones concretas que la cuenta tenga se ofrecen aparte, con la
#: lista real que devuelve la prueba de conexión.
PROVEEDORES: tuple[dict[str, Any], ...] = (
    {
        "clave": "gemini",
        "nombre": "Google Gemini",
        "estilo": ESTILO_GEMINI,
        "endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "variable_entorno": "GEMINI_API_KEY",
        "formato_clave": "Empieza por AIza o AQ",
        "identificador": "Empieza por «AIza» o por «AQ»",
        "endpoint_editable": False,
        "detectar": _es_gemini,
        "modelos": ("gemini-flash-latest", "gemini-pro-latest"),
        "implementado": True,
    },
    {
        "clave": "nvidia",
        "nombre": "NVIDIA NIM",
        "estilo": ESTILO_COMPATIBLE,
        "endpoint": ENDPOINT_NVIDIA,
        "variable_entorno": "NVIDIA_API_KEY",
        "formato_clave": "Contiene nvapi-",
        "identificador": "Contiene «nvapi-»",
        "endpoint_editable": False,
        "detectar": _es_nvidia,
        "modelos": (
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "nvidia/llama-3.1-nemotron-70b-instruct",
        ),
        "implementado": True,
    },
    {
        "clave": "openrouter",
        "nombre": "OpenRouter",
        "estilo": ESTILO_COMPATIBLE,
        "endpoint": "https://openrouter.ai/api/v1",
        "variable_entorno": "OPENROUTER_API_KEY",
        "formato_clave": "Empieza por sk-or-",
        "identificador": "Empieza por «sk-or-»",
        "endpoint_editable": False,
        "detectar": _es_openrouter,
        "modelos": ("openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet"),
        "implementado": True,
    },
    {
        "clave": "openai",
        "nombre": "OpenAI",
        "estilo": ESTILO_COMPATIBLE,
        "endpoint": "https://api.openai.com/v1",
        "variable_entorno": "OPENAI_API_KEY",
        "formato_clave": "Empieza por sk-",
        "identificador": "Empieza por «sk-»",
        "endpoint_editable": False,
        "detectar": _es_openai,
        "modelos": ("gpt-4o-mini", "gpt-4o"),
        "implementado": True,
    },
    {
        "clave": "compatible",
        "nombre": "Otro endpoint compatible con OpenAI",
        "estilo": ESTILO_COMPATIBLE,
        "endpoint": "",
        "variable_entorno": "COMPATIBLE_API_KEY",
        "formato_clave": "Cualquiera; hay que indicar la URL base",
        "identificador": "Ninguna reconocible: es la opción para un endpoint propio",
        "endpoint_editable": True,
        "detectar": lambda _clave: False,
        "modelos": (),
        "implementado": True,
    },
)

PROVEEDOR_POR_DEFECTO = "gemini"

#: Ficha de reserva, para que resolver() siempre devuelva algo completo.
_FICHA_POR_DEFECTO = PROVEEDORES[0]

#: Estilos que el asistente sabe hablar.
ESTILOS_IMPLEMENTADOS = (ESTILO_GEMINI, ESTILO_COMPATIBLE)


def _sin_funcion(descrito: dict[str, Any]) -> dict[str, Any]:
    """Copia del proveedor sin la función de detección (no es serializable)."""
    return {clave: valor for clave, valor in descrito.items() if clave != "detectar"}


def catalogo() -> list[dict[str, Any]]:
    """Catálogo público, para el panel. Sin funciones, solo datos."""
    return [_sin_funcion(descrito) for descrito in PROVEEDORES]


def descrito(proveedor: str) -> Optional[dict[str, Any]]:
    """Ficha del proveedor, o ``None`` si no está en el catálogo."""
    for candidato in PROVEEDORES:
        if candidato["clave"] == proveedor:
            return candidato
    return None


def endpoint_de(proveedor: str) -> str:
    """URL base del proveedor; cadena vacía si no la tiene fijada."""
    ficha = descrito(proveedor)
    return ficha["endpoint"] if ficha else ""


def variable_de(proveedor: str) -> str:
    """Variable del `.env` donde se guarda la credencial de ese proveedor."""
    ficha = descrito(proveedor)
    return ficha["variable_entorno"] if ficha else ""


def estilo_de(proveedor: str) -> str:
    """Estilo de API del proveedor (``gemini`` o ``compatible``)."""
    ficha = descrito(proveedor)
    return ficha["estilo"] if ficha else ESTILO_GEMINI


def identificador_de(proveedor: str) -> str:
    """Regla en lenguaje llano para reconocer la clave de ese proveedor."""
    ficha = descrito(proveedor)
    return ficha["identificador"] if ficha else ""


def endpoint_editable(proveedor: str) -> bool:
    """Si el usuario puede escribir la URL base, o la fija el catálogo.

    Solo el proveedor genérico la necesita. En el resto, pedírsela al usuario es
    pedirle un dato que ya sabemos y que puede equivocar.
    """
    ficha = descrito(proveedor)
    return bool(ficha["endpoint_editable"]) if ficha else False


def modelos_de(proveedor: str) -> tuple[str, ...]:
    """Modelos sugeridos del proveedor (alias estables, no versiones fijas)."""
    ficha = descrito(proveedor)
    return tuple(ficha["modelos"]) if ficha else ()


def variables_de_credenciales() -> tuple[str, ...]:
    """Todas las variables del `.env` que pueden llevar una credencial.

    Se usan para no dejar credenciales viejas de otros proveedores: al guardar
    una clave se retiran las demás, o el `.env` acumularía claves de proveedores
    que ya no se usan.
    """
    return tuple(descrito_["variable_entorno"] for descrito_ in PROVEEDORES)


def detectar(clave: str) -> Optional[str]:
    """Proveedor al que pertenece una clave, según su forma.

    Returns:
        La clave del proveedor, o ``None`` si ninguna forma la reconoce.
    """
    valor = _normalizar(clave)
    if not valor:
        return None

    for candidato in PROVEEDORES:
        try:
            if candidato["detectar"](valor):
                return candidato["clave"]
        except Exception:
            # Una detección que falla no debe tumbar el panel: se sigue probando.
            continue
    return None


def resolver(clave: str, proveedor: Optional[str] = None) -> dict[str, Any]:
    """Resuelve proveedor, URL base y variable de entorno a partir de la clave.

    Es la pieza que permite que el usuario pegue **solo** la credencial: de ella
    salen el proveedor, su endpoint y dónde se guarda.

    Args:
        clave: credencial tal cual la pegó el usuario.
        proveedor: proveedor forzado a mano, si la detección no basta.

    Returns:
        Dict con ``detectado`` (bool), ``proveedor``, ``nombre``, ``endpoint``,
        ``variable_entorno`` y ``estilo``.
    """
    valor = _normalizar(clave)
    detectado = detectar(valor) if valor else None
    elegido = detectado or proveedor or PROVEEDOR_POR_DEFECTO

    ficha = descrito(elegido) or _FICHA_POR_DEFECTO
    return {
        "detectado": bool(detectado),
        "proveedor": ficha["clave"],
        "nombre": ficha["nombre"],
        "endpoint": ficha["endpoint"],
        "variable_entorno": ficha["variable_entorno"],
        "estilo": ficha["estilo"],
    }