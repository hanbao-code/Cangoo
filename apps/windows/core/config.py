"""
core.config — 用户配置文件管理模块

从早期界面实现的配置读写逻辑中剥离而来，独立为不依赖 UI 框架的配置管理类。

配置文件采用 JSON 格式，默认位于 %APPDATA%/cangoo/settings.json
（Windows 标准做法，保证卸载/重装不丢配置、程序迁移不丢数据）；
非 Windows 平台回退到 ~/.cangoo/settings.json。
首次运行（文件不存在）时自动创建默认配置文件及所在目录。
所有 I/O 操作均使用 try/except 包裹，避免因文件异常导致程序崩溃。
"""

import os
import json
import copy


def _default_settings_file():
    """返回默认配置文件路径。

    Windows 上使用 %APPDATA%/cangoo/settings.json（Roaming 漫游配置），
    保证卸载/重装不丢配置、程序迁移不丢数据；
    非 Windows 平台回退到 ~/.cangoo/settings.json。
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "cangoo", "settings.json")
    return os.path.join(os.path.expanduser("~"), ".cangoo", "settings.json")


# 默认配置（对齐原型设置面板 6 分组，字段名以原型 INSPECTION_DATA desc 为准）
DEFAULT_SETTINGS = {
    # --- 通用分组 ---
    "close_to_tray": True,             # 关闭按钮行为：True 最小化到托盘，False 直接退出（setting-tray-close）
    "theme": "light",                  # 主题（light/dark/auto）（setting-theme）
    "language": "zh",                  # 界面语言（zh/en），决策 D2（setting-lang）
    "ui_font_scale": "100",           # UI 字号比例（90/100/110/125）

    # --- 视图分组 ---
    "view_mode": "list",               # 默认视图模式（list/split，原型已删 drawer）（setting-default-view）
    "sidebar_visible": True,           # 侧边栏是否可见
    "sidebar_text": True,              # 侧栏显示文字标签，False 时仅图标（setting-sidebar-text）
    "list_density": "comfortable",      # 列表密度（comfortable/compact）
    "sort_mode": "updated",             # 排序模式（updated/name/strength）

    # --- 剪贴板分组 ---
    "clipboard_clear_mode": "countdown",  # 清空模式（countdown/manual）（setting-clip-mode）
    "clipboard_clear_seconds": 30,        # 倒计时秒数（5-60）（setting-clip-duration）
    "quickbar_enabled": True,             # 是否启用 Quick Bar（setting-quickbar）
    "quickbar_autohide_sec": 30,          # QuickBar 自动隐藏秒数（10-600，默认 30s）

    # --- 安全分组 ---
    "stale_threshold_days": 180,         # 长期未更换阈值（天，30-365）（setting-stale）
    "auto_lock_enabled": True,           # 自动锁定开关（setting-autolock）
    "auto_lock_minutes": 5,              # 自动锁定时长（分钟，1-60）（setting-autolock-timeout）
    "quick_bar_hotkey": "Alt+P",         # Quick Bar 全局热键（默认 Alt+P）

    # --- 显示选项 ---
    "show_password_strength": True,     # 列表项显示密码强度条
    "show_totp_in_list": False,          # 列表项显示 TOTP 码

    # --- 密码生成器 ---
    "generator": {
        "length": 20,
        "useLower": True,
        "useUpper": True,
        "useDigits": True,
        "useSymbols": True,
        "avoidAmbiguous": False,
    },

    # --- 数据库 ---
    "recent_databases": [],             # 最近打开的数据库路径列表
    "max_recent": 5,                    # 最近记录最大数（默认 5）
    "startup_autofill": False,          # 启动时自动填充上次数据库路径（setting-autofill）
}


class ConfigManager:
    """
    用户配置文件管理类

    管理 settings.json 配置文件的读写，提供统一的 get/set 接口。
    所有 I/O 操作均使用 try/except 包裹，避免因文件异常导致程序崩溃。

    用法示例：
        cfg = ConfigManager("settings.json")
        cfg.load()
        if cfg.get("close_to_tray", True):
            ...
        cfg.set("theme", "light")
        cfg.save()
    """

    def __init__(self, settings_file: str = None):
        """
        初始化配置管理器

        :param settings_file: 配置文件路径，为 None 时使用
                              %APPDATA%/cangoo/settings.json
                              （非 Windows 回退到 ~/.cangoo/settings.json）
        """
        self.settings_file = settings_file if settings_file is not None else _default_settings_file()
        # 内存中的配置数据，初始化为默认配置的深拷贝
        # （DEFAULT_SETTINGS 含 list 类型字段 recent_databases，浅拷贝会导致多实例共享同一 list 对象）
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)

    def _ensure_dir(self):
        """确保配置文件所在目录存在（首次运行时自动创建）"""
        dir_path = os.path.dirname(self.settings_file)
        if dir_path:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception:
                pass

    def load(self, *, create_if_missing: bool = True):
        """
        读取 settings.json 配置文件

        - 文件不存在时，使用默认配置；默认自动创建文件（首次运行）
          只读启动探测可传 ``create_if_missing=False`` 延迟到严格写端口
        - 文件解析失败或格式错误时，回退到默认配置
        - 文件存在且格式正确时，将文件数据与默认配置合并
          （文件中已有的项覆盖默认项，文件中缺失的项使用默认值，
           兼容旧版本配置文件，自动补全新增的默认配置项）
        """
        try:
            self._ensure_dir()
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # 默认配置在前，文件配置在后，文件配置覆盖默认配置
                    # deepcopy 避免多实例共享 list/dict 默认值
                    self.settings = {**copy.deepcopy(DEFAULT_SETTINGS), **data}
                else:
                    # 顶层不是字典，回退到默认配置
                    self.settings = copy.deepcopy(DEFAULT_SETTINGS)
            else:
                # 首次运行使用默认配置；严格写端口可延迟创建。
                self.settings = copy.deepcopy(DEFAULT_SETTINGS)
                if create_if_missing:
                    self.save()
        except (json.JSONDecodeError, UnicodeError, IOError, OSError):
            # 任何 I/O 或解析异常均回退到默认配置
            self.settings = copy.deepcopy(DEFAULT_SETTINGS)

    def save(self):
        """写入 settings.json 配置文件"""
        try:
            self._ensure_dir()
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except (IOError, OSError) as e:
            print(f"Warning: 无法保存配置文件: {e}")

    def get(self, key: str, default=None):
        """
        读取指定配置项

        :param key: 配置键名
        :param default: 键不存在时的默认返回值
        :return: 配置值，不存在则返回 default
        """
        return self.settings.get(key, default)

    def set(self, key: str, value):
        """
        设置指定配置项（仅修改内存，需调用 save() 持久化）

        :param key: 配置键名
        :param value: 配置值
        """
        self.settings[key] = value
