"""保留QtQml原生依赖；Widgets/WebEngine产品不收集QML界面扩展。"""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies
from pathlib import Path

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# 产品不启用QML调试；调试插件会额外牵入Quick3D工具库。
binaries = [(source, target) for source, target in binaries if Path(target).name != "qmltooling"]
