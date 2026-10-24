"""统一 UI 字号档位与稳定基准像素换算。"""

UI_FONT_SCALES = frozenset({"90", "100", "110", "125"})
DEFAULT_UI_FONT_SCALE = "100"


def normalize_ui_font_scale(value: object) -> str:
    return (
        value
        if isinstance(value, str) and value in UI_FONT_SCALES
        else DEFAULT_UI_FONT_SCALE
    )


def scaled_font_pixel_size(base: int, scale: str) -> int:
    if type(base) is not int or base <= 0:
        raise ValueError("font base must be a positive integer")
    if scale not in UI_FONT_SCALES:
        raise ValueError("invalid UI font scale")
    return max(1, (base * int(scale) + 50) // 100)


__all__ = [
    "DEFAULT_UI_FONT_SCALE",
    "UI_FONT_SCALES",
    "normalize_ui_font_scale",
    "scaled_font_pixel_size",
]
