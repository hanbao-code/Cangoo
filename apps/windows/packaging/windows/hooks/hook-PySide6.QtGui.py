"""复用Qt原生收集，排除产品未使用的Qt虚拟键盘插件。"""

from pathlib import Path
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# Windows输入法仍由qwindows平台插件提供，不使用QML虚拟键盘。
binaries = [(source, target) for source, target in binaries
            if Path(source).name.lower() != "qtvirtualkeyboardplugin.dll"]
