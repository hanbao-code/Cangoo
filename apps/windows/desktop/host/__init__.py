"""WebEngine 原生宿主；包初始化保持 Qt-free（不导入 Qt）。"""


def register_app_scheme() -> None:
    """仅在启动策略通过后按需导入 Qt WebEngine 并注册协议。"""

    from .web_profile import register_app_scheme as _register_app_scheme

    _register_app_scheme()


def __getattr__(name: str):
    """兼容既有资源导出，同时避免包初始化阶段加载 ``QtCore``。"""

    if name in {"APP_ORIGIN", "ENTRY_URL", "ResourceCatalog"}:
        from .resources import APP_ORIGIN, ENTRY_URL, ResourceCatalog

        return {
            "APP_ORIGIN": APP_ORIGIN,
            "ENTRY_URL": ENTRY_URL,
            "ResourceCatalog": ResourceCatalog,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "APP_ORIGIN",
    "ENTRY_URL",
    "ResourceCatalog",
    "register_app_scheme",
]
