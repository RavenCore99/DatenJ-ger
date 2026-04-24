# iconos del sistema
# carga y cachea los png para los widgets

import os
from PIL import Image
import customtkinter as ctk

ICONS_DIR = os.path.join(os.path.dirname(__file__), "assets", "icons")
_cache = {}


def get_icon(name: str, size: int = 18) -> ctk.CTkImage:
    # carga icono png y lo guarda en cache
    key = (name, size)
    if key not in _cache:
        path = os.path.join(ICONS_DIR, f"{name}.png")
        if not os.path.exists(path):
            # si no existe el icono, devuelve uno vacio
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            _cache[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            return _cache[key]
        img = Image.open(path).convert("RGBA")
        # para modo claro invertimos el color
        img_dark = img.copy()  # dark mode va tal cual
        img_light = _invert_white_to_dark(img.copy())
        _cache[key] = ctk.CTkImage(
            light_image=img_light,
            dark_image=img_dark,
            size=(size, size)
        )
    return _cache[key]


def _invert_white_to_dark(img: Image.Image) -> Image.Image:
    # invierte blanco a azul oscuro para fondos claros
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a > 0:
                # invertir color
                brightness = (r + g + b) / (3 * 255)
                nr = int(26 * brightness)
                ng = int(35 * brightness)
                nb = int(126 * brightness)
                pixels[x, y] = (nr, ng, nb, a)
    return img


# mapeo de referencia
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
