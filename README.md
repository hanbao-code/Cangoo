# 小仓 / Cangoo

一款 Windows 离线密码与加密记事管理工具。

[下载](https://github.com/hanbao-code/Cangoo/releases) · [使用手册](docs/user_guide_zh.md) · [问题反馈](https://github.com/hanbao-code/Cangoo/issues) · [English](#english)

## 预览

![小仓密码库](docs/images/vault_zh.png)

## 下载与安装

前往[发布页面](https://github.com/hanbao-code/Cangoo/releases)下载，适用于 Windows 10/11 x64（Intel/AMD 64 位）电脑。

| 类型 | 使用方式 |
|---|---|
| 安装版 | 运行安装程序，可选择安装范围和目录。 |
| 便携版 | 完整解压后运行；迁移时保留整个目录及另存的数据库。 |

安装、备份、迁移和更新步骤见[使用手册](docs/user_guide_zh.md)，更新内容见[版本说明](release_notes.md)。

## 功能

- 密码与加密记事管理，支持搜索和收藏。
- 弱密码、重复密码和过期密码检查。
- 密码生成与强度检测。
- 快捷搜索、受控复制与自动锁定。
- 加密备份与恢复，离线中英帮助、主题和字号设置。

## 反馈与联系

普通问题请提交[项目议题](https://github.com/hanbao-code/Cangoo/issues)，安全漏洞请使用[私密报告渠道](SECURITY.md)。

联系与授权申请：通过[Telegram交流群](https://t.me/+kQEszbuHNEgxOGRh)联系管理员；需要私下沟通时，请私聊管理员。

## 数据与许可

小仓在本地处理和保存数据，不通过网络发送密码库或主密码。数据库、主密码及备份由你自行保管。

个人、非商业用途免费；其他使用范围见[软件许可协议](LICENSE.md)。[第三方许可及来源](docs/third_party_sources.md)单独提供。

## 致谢（Acknowledgements）

感谢以下项目及其维护者：

- [Python](https://www.python.org/)：通用编程语言及其运行环境。
- [Qt](https://www.qt.io/)：跨平台应用开发框架。
- [PySide6](https://doc.qt.io/qtforpython-6/)：Qt 官方的 Python 绑定。
- [Shiboken](https://doc.qt.io/qtforpython-6/shiboken6/index.html)：为 C++ 库生成 Python 绑定的工具。
- [Qt WebEngine](https://doc.qt.io/qt-6/qtwebengine-index.html)：基于 Chromium 的嵌入式网页引擎。
- [Chromium](https://www.chromium.org/)：开源浏览器项目。
- [SQLite](https://www.sqlite.org/)：嵌入式关系型数据库引擎。
- [sqleet](https://github.com/resilar/sqleet)：SQLite 数据库加密扩展。
- [pysqleet](https://github.com/robertkearns/pysqleet)：sqleet 的 Python 绑定。
- [PyCryptodome](https://www.pycryptodome.org/)：提供多种密码算法的 Python 库。
- [argon2-cffi](https://github.com/hynek/argon2-cffi)：Argon2 密码哈希算法的 Python 绑定。
- [CFFI](https://github.com/python-cffi/cffi)：让 Python 调用 C 代码的外部函数接口。
- [pypinyin](https://github.com/mozillazg/python-pinyin)：将汉字转换为拼音的 Python 库。
- [pinyin-pro](https://github.com/zh-lx/pinyin-pro)：提供中文转拼音、拼音匹配等功能的 JavaScript 库。
- [zxcvbn](https://github.com/dropbox/zxcvbn)：基于常见密码模式分析的密码强度估算库。
- [zxcvbn-python](https://github.com/dwolfhub/zxcvbn-python)：zxcvbn 的 Python 实现。
- [Phosphor Icons](https://github.com/phosphor-icons/core)：风格统一、提供多种粗细的开源图标库。
- [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope)：开源无衬线字体。
- [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono)：面向开发者的开源等宽字体。
- [PyInstaller](https://pyinstaller.org/)：将 Python 程序及其依赖打包为可分发应用的工具。
- [Inno Setup](https://jrsoftware.org/isinfo.php)：Windows 安装程序制作工具。

更多组件的来源与版权信息见[第三方说明](docs/third_party_sources.md)及[许可原文](third_party/notices.txt)。

## English

Cangoo is an offline password and encrypted-note manager for Windows.

[Download](https://github.com/hanbao-code/Cangoo/releases) · [User guide](docs/user_guide_en.md) · [Feedback](https://github.com/hanbao-code/Cangoo/issues)

### Preview

![Cangoo password vault](docs/images/vault_en.png)

### Download and install

Download from the [releases page](https://github.com/hanbao-code/Cangoo/releases) for Windows 10/11 x64.

| Edition | Getting started |
|---|---|
| Installer | Run Setup and choose the installation scope and directory. |
| Portable | Extract the entire archive before running. Preserve the full folder and any external databases when moving it. |

See the [user guide](docs/user_guide_en.md) for installation, backup, migration and updates, and the [release notes](release_notes.md) for changes.

### Features

- Password and encrypted-note management with search, favorites and filtered views.
- Checks for weak, reused and expired passwords.
- Password generation and strength estimates.
- Quick Bar, controlled copying and automatic locking.
- Encrypted backup and restore, offline Chinese/English help, themes and text-size settings.

### Feedback and contact

Use [project issues](https://github.com/hanbao-code/Cangoo/issues) for ordinary feedback and [private reporting](SECURITY.md) for security vulnerabilities.

For contact and permission requests, reach an administrator through the [Telegram group](https://t.me/+kQEszbuHNEgxOGRh). Use a private message when needed.

### Data and license

Cangoo processes and stores data locally without sending your databases or master passwords over the network. Keep your databases, master passwords and backups safe.

Personal, non-commercial use is free. See the [Software License Agreement](LICENSE.md) for the full terms and [third-party licenses and sources](docs/third_party_sources.md) for component information.

### Acknowledgements

Thanks to the following projects and their maintainers:

- [Python](https://www.python.org/): A general-purpose programming language and runtime.
- [Qt](https://www.qt.io/): A cross-platform application development framework.
- [PySide6](https://doc.qt.io/qtforpython-6/): The official Python bindings for Qt.
- [Shiboken](https://doc.qt.io/qtforpython-6/shiboken6/index.html): A tool for generating Python bindings for C++ libraries.
- [Qt WebEngine](https://doc.qt.io/qt-6/qtwebengine-index.html): A Chromium-based embedded web engine.
- [Chromium](https://www.chromium.org/): An open-source browser project.
- [SQLite](https://www.sqlite.org/): An embedded relational database engine.
- [sqleet](https://github.com/resilar/sqleet): An encryption extension for SQLite databases.
- [pysqleet](https://github.com/robertkearns/pysqleet): Python bindings for sqleet.
- [PyCryptodome](https://www.pycryptodome.org/): A Python library implementing cryptographic algorithms.
- [argon2-cffi](https://github.com/hynek/argon2-cffi): Python bindings for the Argon2 password-hashing algorithm.
- [CFFI](https://github.com/python-cffi/cffi): A foreign function interface for calling C code from Python.
- [pypinyin](https://github.com/mozillazg/python-pinyin): A Python library for converting Chinese characters to pinyin.
- [pinyin-pro](https://github.com/zh-lx/pinyin-pro): A JavaScript library for Chinese-to-pinyin conversion and pinyin matching.
- [zxcvbn](https://github.com/dropbox/zxcvbn): A password-strength estimator based on common password patterns.
- [zxcvbn-python](https://github.com/dwolfhub/zxcvbn-python): A Python implementation of zxcvbn.
- [Phosphor Icons](https://github.com/phosphor-icons/core): An open-source icon family with a consistent style and multiple weights.
- [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope): An open-source sans-serif typeface.
- [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono): An open-source monospaced typeface for developers.
- [PyInstaller](https://pyinstaller.org/): A tool for bundling Python applications and their dependencies for distribution.
- [Inno Setup](https://jrsoftware.org/isinfo.php): A tool for creating Windows installers.

See [third-party sources](docs/third_party_sources.md) and [license notices](third_party/notices.txt) for further component and copyright information.
