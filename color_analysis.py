"""
Análisis de uso de color por página para Copy-on.
Usa OpenCV + NumPy: saturación (HSV) y aproximación tipo CMYK (cyan, magenta, amarillo)
para estimar % de color por hoja y clasificar en rangos de precio.

Futuro: un modelo de deep learning puede reemplazar esta lógica por una
clasificación más fina (p. ej. poco color / medio / lleno) entrenada con
ejemplos reales de la fotocopiadora.
"""
from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Rangos por defecto para clasificar "poco color" (mínimo ~40 cént) vs "lleno" (S/ 1)
# Porcentaje de color en la hoja (0-100). Ajustables según experiencia real.
TIER_RANGES = {
    "bajo": (0.0, 15.0),   # poco color -> precio mínimo
    "medio": (15.0, 50.0),
    "alto": (50.0, 100.0), # lleno de color -> precio máximo
}


def _rgb_to_cmyk_approx(rgb: np.ndarray) -> np.ndarray:
    """
    Aproximación RGB -> uso de tinta tipo CMYK (cyan, magenta, amarillo).
    Las impresoras usan CMYK; desde RGB podemos aproximar:
    C ≈ 1 - R/255, M ≈ 1 - G/255, Y ≈ 1 - B/255 (normalizado 0-1).
    Devuelve array (H, W, 3) con valores en [0, 1].
    """
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    r, g, b = r.astype(np.float32) / 255.0, g.astype(np.float32) / 255.0, b.astype(np.float32) / 255.0
    c = 1.0 - r
    m = 1.0 - g
    y = 1.0 - b
    return np.stack([c, m, y], axis=-1)


def _colorfulness_from_hsv(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Saturación (HSV): indica qué tan "colorido" es cada píxel (0 = gris, alto = color).
    Devuelve (saturation 0-255, value 0-255) para uso posterior.
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]  # saturación
    v = hsv[:, :, 2]  # valor (brillo)
    return s, v


def analyze_image(
    image_input: bytes | str,
    tier_ranges: Optional[dict[str, tuple[float, float]]] = None,
    saturation_threshold: int = 25,
) -> dict:
    """
    Analiza una imagen (página escaneada o renderizada) y estima el uso de color.

    Métricas:
    - color_pct: porcentaje 0-100 de "color" en la hoja (basado en saturación y área no blanca).
    - tier: "bajo" | "medio" | "alto" según rangos configurables (mapeo a precio).
    - saturation_mean: saturación media (0-255), para auditoría.
    - cmyk_approx: uso relativo aproximado C, M, Y (0-1) promediado en la página.

    image_input: bytes de la imagen (PNG/JPEG) o ruta a archivo.
    tier_ranges: dict con keys "bajo", "medio", "alto" y valores (min, max) de color_pct.
    saturation_threshold: píxeles con saturación por debajo se consideran "sin color" (gris/blanco).
    """
    ranges = tier_ranges or TIER_RANGES

    if isinstance(image_input, str):
        img = cv2.imread(image_input)
    else:
        buf = np.frombuffer(image_input, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("No se pudo cargar la imagen (bytes o ruta inválidos)")

    # BGR -> RGB para reportes; OpenCV trabaja en BGR
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    total_pixels = h * w

    # 1) Saturación HSV: qué fracción del área tiene color "visible"
    s, v = _colorfulness_from_hsv(img)
    saturation_mean = float(np.mean(s))
    # Píxeles "con color": saturación por encima del umbral y no demasiado oscuros
    has_color = (s >= saturation_threshold) & (v >= 30)
    color_pixel_ratio = np.sum(has_color) / max(total_pixels, 1)
    # Peso por intensidad: no solo "hay color" sino cuánta saturación
    weighted_color = np.sum(s * has_color.astype(np.float32)) / max(np.sum(has_color), 1)
    # color_pct: combina área con color y cuánto color (0-100)
    color_pct = min(100.0, (color_pixel_ratio * 0.5 + (weighted_color / 255.0) * 0.5) * 100.0)

    # 2) Aproximación CMYK (cyan, magenta, amarillo) para reporte
    cmy = _rgb_to_cmyk_approx(rgb)
    c_mean = float(np.mean(cmy[..., 0]))
    m_mean = float(np.mean(cmy[..., 1]))
    y_mean = float(np.mean(cmy[..., 2]))

    # 3) Tier según rangos
    tier = "bajo"
    for t, (lo, hi) in ranges.items():
        if lo <= color_pct < hi:
            tier = t
            break
    if color_pct >= ranges.get("alto", (50, 100))[0]:
        tier = "alto"

    return {
        "color_pct": round(color_pct, 2),
        "tier": tier,
        "saturation_mean": round(saturation_mean, 2),
        "cmyk_approx": {
            "cyan": round(c_mean, 4),
            "magenta": round(m_mean, 4),
            "yellow": round(y_mean, 4),
        },
        "size_pixels": {"width": w, "height": h},
    }
