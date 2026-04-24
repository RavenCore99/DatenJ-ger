# icons.py - Cargador centralizado de iconos
# Usa CTkImage para renderizado cross-platform consistente

import os
from PIL import Image
import customtkinter as ctk

ICONS_DIR = os.path.join(os.path.dirname(__file__), "assets", "icons")
_cache = {}


def get_icon(name: str, size: int = 18) -> ctk.CTkImage:
    """Carga un icono PNG y lo cachea.

    Args:
        name: Nombre del icono sin extensión (ej: 'folder-open', 'lock')
        size: Tamaño en píxeles (cuadrado). Default: 18

    Returns:
        CTkImage listo para usar en image= de cualquier widget CTk
    """
    key = (name, size)
    if key not in _cache:
        path = os.path.join(ICONS_DIR, f"{name}.png")
        if not os.path.exists(path):
            # Fallback: retorna un placeholder transparente | evita crashear
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            _cache[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            return _cache[key]
        img = Image.open(path).convert("RGBA")
        # version light (invertir a oscuro para fondos claros)
        img_dark = img.copy()  # blanco sobre fondo oscuro
        img_light = _invert_white_to_dark(img.copy())
        _cache[key] = ctk.CTkImage(
            light_image=img_light,
            dark_image=img_dark,
            size=(size, size)
        )
    return _cache[key]


def _invert_white_to_dark(img: Image.Image) -> Image.Image:
    """Invierte los píxeles blancos a un tono oscuro (#1a237e) para modo claro."""
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a > 0:
                # Invertir: blanco → azul oscuro (#1a237e)
                brightness = (r + g + b) / (3 * 255)
                nr = int(26 * brightness)
                ng = int(35 * brightness)
                nb = int(126 * brightness)
                pixels[x, y] = (nr, ng, nb, a)
    return img


# Mapeo  → nombre de icono para referencia rapida
EMOJI_MAP = {
    "📂": "folder-open",
    "📄": "file-text",
    "📋": "clipboard",
    "📝": "file-pen",
    "✏️": "edit",
    "🗑️": "trash-2",
    "⬇️": "download",
    "💾": "save",
    "🔲": "grid",
    "📅": "calendar",
    "👤": "user",
    "🏢": "building",
    "🪪": "id-card",
    "🔒": "lock",
    "🔐": "key-round",
    "🔑": "key",
    "🛡️": "shield",
    "🔓": "unlock",
    "🆔": "hash",
    "📊": "bar-chart",
    "📑": "file-stack",
    "📜": "scroll-text",
    "🔍": "search",
    "🔄": "refresh-cw",
    "📁": "folder",
    "👁": "eye",
    "🌍": "globe",
    "🌙": "moon",
    "🚀": "rocket",
    "🚪": "door-open",
    "👋": "hand",
    "👥": "users",
    "⏳": "hourglass",
    "⬅️": "arrow-left",
    "✅": "check-circle",
    "❌": "x-circle",
    "⚠️": "alert-triangle",
    "ℹ️": "info",
    "✨": "sparkles",
    "⚙️": "settings",
    "☀️": "sun",
    "✍️": "pen-line",
    "➕": "plus",
}
