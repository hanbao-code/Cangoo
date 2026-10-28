# 第三方来源与库替换 / Third-party sources and library replacement

[安卓第三方来源与许可](../third_party/android/README.md) · [电脑版许可原文](../third_party/notices.txt) · [源码构建](building.md)

软件内“帮助 → 关于 → 第三方许可”提供随附版权及许可原文；相同文本也保存在
`apps/windows/desktop/frontend/assets/help/content.json`。本页供需要取得源码、构建或替换库的开发者使用。

## Qt / PySide6 / Shiboken 6.9.3

使用PySide6官方Windows轮子及其中的Qt运行库，库文件保留独立动态链接形式。
Qt自身许可、Chromium/WebEngine/PDF归属、实际保留原生模块和图像格式插件的上游许可均在软件中提供。
QtBluetooth 使用本项目写等待补丁；其余 Qt 库及 PySide/Shiboken 保持上游版本。
对应源码归档、补丁、摘要及重建说明随程序保存在 `_internal/third_party/qt_bluetooth/`，
源码树中的说明见 `apps/windows/packaging/windows/qt_bluetooth_build.md`。

以下是对应版本的官方源码归档，SHA-256取自Qt官方文件详情页。Qt WebEngine归档包含其Chromium来源；
PySide/Shiboken来源为pyside-setup。构建第三方库时遵循源码内的许可和官方对应版本构建说明。

| 源码 | SHA-256 |
|---|---|
| [qtbase](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtbase-everywhere-src-6.9.3.tar.xz) | `c5a1a2f660356ec081febfa782998ae5ddbc5925117e64f50e4be9cd45b8dc6e` |
| [qtconnectivity（Qt Bluetooth）](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtconnectivity-everywhere-src-6.9.3.tar.xz) | `e21bba5efb174c4456c5e5a7b4d52bba1ee62dfb4509bcff73fdfad9cb1dd7f5` |
| [qtdeclarative](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtdeclarative-everywhere-src-6.9.3.tar.xz) | `5a071b227229afbf5c976b7b59a0d850818d06ae861fcdf6d690351ca3f8a260` |
| [qtpositioning](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtpositioning-everywhere-src-6.9.3.tar.xz) | `0c87c980f704c17aadaf0bf8a03845dd0a60cc0313be24bd7b5b90685d5835b4` |
| [qtserialport](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtserialport-everywhere-src-6.9.3.tar.xz) | `4b18ec030ff2644698c3f5c776894d8ffe5d3174c964d9bd8668429c943e8298` |
| [qtsvg](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtsvg-everywhere-src-6.9.3.tar.xz) | `db76aa3358cbbe6fce7da576ff4669cb9801920188c750d3b12783bbe97026e2` |
| [qtwebchannel](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtwebchannel-everywhere-src-6.9.3.tar.xz) | `9457bbc1e5a13d9cf277c1fc121cdeb0a21546abf7fba091779b7ce9806fa305` |
| [qtwebengine](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtwebengine-everywhere-src-6.9.3.tar.xz) | `d50b3b11d51dd876418cc36b4d6c96b4721e0aab773a3dd6beda606d46da8966` |
| [qtimageformats](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qtimageformats-everywhere-src-6.9.3.tar.xz) | `4fb26bdbfbd4b8e480087896514e11c33aba7b6b39246547355ea340c4572ffe` |
| [qttranslations](https://download.qt.io/archive/qt/6.9/6.9.3/submodules/qttranslations-everywhere-src-6.9.3.tar.xz) | `f36d545e6681b146fd79b3ebb74ef275e88694cf81eae8323327cae3bfc490a1` |
| [pyside-setup (PySide6 / Shiboken)](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.9.3-src/pyside-setup-everywhere-src-6.9.3.zip) | `bd6cea8ced15db163de66b38c34a949bd2a749711890e9aeb2fee30941436114` |

## 数据库驱动与其他组件

pysqleet31.1.3的原始源码：[官方源码包](https://files.pythonhosted.org/packages/c8/e4/b2271580532bb88e2c42d9f2b386f43e29675fc93269009c26240ebff9dc/pysqleet-31.1.3.tar.gz)，
SHA-256为 `941e14b7533eeffcfee666c12e8ecf6e4b72317daafe3d0e788dc8540c8a277a`。
本项目改动完整保存在 `apps/windows/packaging/windows/pysqleet_31_1_3.patch`，构建命令见根目录README。
补丁包含Python3.10/MSVC构建适配与SQLite资源限制接口。包装层保留pysqlite各作者的来源许可；sqleet加密及SQLite引擎实现保持原样。

Python3.10.11来源：[Python官方版本页](https://www.python.org/downloads/release/python-31011/)。
Python自身及其OpenSSL等随附许可在软件中保留；此Windows运行时随附OpenSSL1.1.1t，
对应[OpenSSL1.1.1t源码](https://github.com/openssl/openssl/tree/OpenSSL_1_1_1t)及其OpenSSL/SSLeay原始许可随来源保留。其他Python依赖的确切版本见 `apps/windows/packaging/windows/requirements.txt`，
原始源码可从各版本的PyPI发布页取得；CFFI内含libffi、Argon2绑定内含Argon2/Blake2的独立许可也已补充。
网页侧的pinyin-pro、zxcvbn、Phosphor Icons、Manrope和JetBrains Mono保留随附原文及来源链接。

Windows局域网授权使用[comtypes 1.4.17](https://pypi.org/project/comtypes/1.4.17/)调用系统COM接口，未修改上游库。采用MIT许可，原文保留在软件第三方许可中；不增加必选的传递依赖。官方轮子`comtypes-1.4.17-py3-none-any.whl`的SHA-256为`4e0a221dde2c589b82977bed802efd71cd5eb67a380347b732e02735e597f586`；源码包SHA-256为`3d9c1e92ad8daf7600d371e76ee16161a627a5fb70c3144f6e52e78af6034363`。

设备配对使用[srp 1.0.22](https://pypi.org/project/srp/1.0.22/)与其依赖[six 1.17.0](https://pypi.org/project/six/1.17.0/)，两者MIT许可原文随帮助资产提供。运行固定srp的Python后端，打包排除旧OpenSSL动态后端；上游源码未修改。安卓继续使用其既有Bouncy Castle，未引入Python配对运行时。

## 替换第三方库

1. 正常退出小仓，另行备份程序目录和用户数据。
2. 使用相同Windows x64架构、Python ABI及兼容接口构建相应第三方库；相关上游构建说明见
   [Qt6.9构建](https://doc.qt.io/qt-6.9/build-sources.html)和
   [Qt for Python构建](https://doc.qt.io/qtforpython-6.9/building_from_source/index.html)。
3. 安装版和解压后的便携版均以程序旁 `_internal` 保存运行库。Qt及其插件位于
   `_internal/PySide6/`；PySide绑定和Shiboken扩展须与对应Qt接口兼容，成套更换相关文件。
   WebEngine还需要匹配的 `QtWebEngineProcess.exe`、资源包和翻译资源，不能只任意替换单个DLL。
4. Python原生扩展位于 `_internal` 中的相应模块位置。数据库驱动为
   `_internal/_sqleet.cp310-win_amd64.pyd`；从源码运行时位于项目虚拟环境的site-packages。
5. 用独立测试数据库验证替换结果；若接口不兼容，应恢复备份的程序文件。本软件不对这些第三方库
   执行固定字节摘要锁定；前端静态资源的完整性校验仍属于另一条边界。

软件自有许可不限制第三方许可授予的修改、替换、重新链接和为调试这些修改所需的相应权利。

## English

The app includes copyright notices and license texts under Help → About → Third-party licenses.
The same texts and their sources are present in `apps/windows/desktop/frontend/assets/help/content.json`.
The table links the official, versioned Qt and PySide/Shiboken source archives and their published SHA-256 hashes.
Qt WebEngine includes Chromium sources. QtBluetooth includes the project write-wait patch dated 2026-10-27;
other Qt libraries and PySide/Shiboken are unchanged. The matching source archive, patch, hashes and build
instructions are bundled under `_internal/third_party/qt_bluetooth/`.

The pysqleet31.1.3 source URL, archive hash and complete project patch are provided above and in the root README.
The patch adjusts Python3.10/MSVC build compatibility and exposes SQLite resource-limit APIs; the sqleet encryption and SQLite engine implementations are unchanged.
Other Python component versions are pinned in `apps/windows/packaging/windows/requirements.txt`; their versioned source releases are available
through PyPI. Notices also include bundled native implementations such as libffi and Argon2/Blake2.

To replace a library, exit Cangoo, back up the program and your data, and build an interface-compatible Windows x64
library with the matching Python ABI. Runtime libraries are stored beside the executable under `_internal`.
Qt and plugins are under `_internal/PySide6`; replace bindings and dependent Qt libraries coherently.
WebEngine additionally needs its matching helper executable, resource packs and translations.
Test with a separate database and restore the backed-up program if interfaces are incompatible.
Third-party library bytes are not pinned by the application; frontend resource integrity is a separate boundary.
Rights granted by the component licenses, including modification and debugging those modifications, remain intact.


## Inno安装器 / Inno installer

当前安装器使用Inno Setup 7.1.0。官方来源及编译器文件摘要见`apps/windows/packaging/windows/inno_tool_lock.json`；原始许可以`inno_license.txt`随构建成品保留；公开源码中的原文见 `third_party/inno_license.txt`。自有安装脚本和明确标为MIT的原生辅助源码按项目许可声明提供，第三方许可不被替换。

The installer uses Inno Setup 7.1.0, pinned in `apps/windows/packaging/windows/inno_tool_lock.json`. The original license is supplied as `inno_license.txt` with build outputs and in the public source tree under `third_party/inno_license.txt`. Project licensing applies to original scripts and explicitly marked native helpers; third-party notices remain unchanged.


[Inno原始许可 / Inno original license](../third_party/inno_license.txt)
