# 小仓 / Cangoo

小仓是一款在本地保存密码和加密记事的应用，支持 Windows 电脑和 Android 手机。你可以把账号、密码、动态验证码密钥和恢复码保存在自己的密码库中，需要时查找、复制或备份。

[下载与版本](https://github.com/hanbao-code/Cangoo/releases) · [版本说明](release_notes.md) · [电脑版手册](docs/user_guide_zh.md) · [安卓版手册](docs/android/user_guide_zh.md) · [从源码构建](docs/building.md) · [English](#english)

## 主要功能

- **整理密码与记事：**新建、编辑、搜索、收藏和排序；电脑版还支持中文拼音查找。
- **更方便地登录：**按需查看、复制密码和动态验证码；保存恢复码并手动标记已用。
- **检查密码安全：**生成随机密码，在本机检查密码强度，以及哪些记录用了相同密码；电脑版还可提醒长期未更换的密码。
- **备份与恢复：**导出加密备份，恢复前逐项对照备份与当前资料；相同内容自动跳过，有差异时由你决定如何处理。
- **在设备间传资料：**通过局域网或蓝牙选择附近设备。核对两端显示的数字，确认一致后发送；接收端收齐资料后，再比较并确认导入。可选全部、仅密码或仅记事。
- **按习惯使用：**中英文界面与离线手册、主题和字号设置、自动锁定及剪贴板清理。电脑版提供快捷搜索条；安卓版可在设备支持时为每个库单独开启生物识别快捷解锁。
- **自己决定更新：**启动时按设定间隔检查，也可随时手动检查；下载和安装由你决定。

## 下载与安装

在[发行页面](https://github.com/hanbao-code/Cangoo/releases)按平台查看版本说明和文件。电脑版与安卓版各有自己的版本号。设备传输从 Windows 1.1.0 和 Android 1.0.0 开始提供。

| 平台 | 系统要求 | 文件与使用方式 | 手册 |
|---|---|---|---|
| Windows | Windows 10（1809及以上）或 Windows 11，x64（Intel/AMD 64位） | 安装版运行 `setup.exe`，按向导安装；便携版完整解压后运行 | [中文](docs/user_guide_zh.md) / [English](docs/user_guide_en.md) |
| Android | Android 10及以上，arm64（64位 ARM） | 将 APK 安装到手机，按系统提示允许本次安装 | [中文](docs/android/user_guide_zh.md) / [English](docs/android/user_guide_en.md) |

Windows 安装包可设置安装位置、使用范围和桌面快捷方式；再次打开可修复或卸载。卸载默认保留资料，主动选择清理前请先备份。搬移便携版时，应保留整个目录及另存的密码库。

Windows 文件未使用代码签名，系统可能提示发行者未知。请从本项目发行页面取得文件，并核对随附的 SHA-256 校验清单；校验值不能替代代码签名。

## 第一次使用

1. 创建密码库并设置主密码。在电脑版中，还需选择数据库文件的保存位置，并记住该位置。
2. 新建并保存一条记录，再试着查找和复制。小仓只保存资料，不会替你修改网站或应用上的密码。
3. 导出一次加密备份，把备份密码与文件分开保管；定期在空库中尝试恢复。

忘记主密码或备份密码后，作者无法代为找回。具体步骤见对应平台的手册，也可在软件内离线阅读。

## 资料与隐私

密码库保存在设备本地，小仓不提供云端托管或自动双向同步。版本检查读取 GitHub 的公开发行信息，不发送密码库内容或主密码。设备传输由你主动发起，两端核对后加密传送所选资料；接收完整并确认导入前，不改动接收端密码库。

## 反馈与联系

遇到问题时，可加入[Telegram（电报）交流群](https://t.me/+kQEszbuHNEgxOGRh)联系管理员，说明使用的是电脑版还是安卓版、应用及系统版本、操作经过和错误提示。需要私下沟通时，可联系管理员私聊；安全漏洞请按[安全问题报告说明](SECURITY.md)私下报告。请勿发送真实密码、数据库、备份或包含敏感信息的截图。

## 许可

小仓采用 **AGPL-3.0-only**，附[针对 Windows 随包 OpenSSL 的限定附加许可](OPENSSL_EXCEPTION.md)。见[许可说明](LICENSE.md)和[许可证全文](COPYING)。软件开源不要求公开用户的密码库、记事或备份。

明确标记为 MIT 的自有安装器辅助源码单独适用[该目录许可](apps/windows/packaging/windows/native/LICENSE)；WiX 及其派生材料保留 MS-RL，其他第三方材料保留各自许可。完整范围见[许可说明](LICENSE.md)和[第三方许可及来源](docs/third_party_sources.md)。

## 致谢

[Python](https://www.python.org/) · [Qt](https://www.qt.io/) · [Jetpack Compose](https://developer.android.com/compose) · [SQLite](https://www.sqlite.org/) · [zxcvbn](https://github.com/dropbox/zxcvbn)

## English

Cangoo is a local password and encrypted-note manager for Windows and Android. Keep accounts, passwords, authenticator setup keys and recovery codes in your own vault, ready to find, copy or back up when needed.

[Downloads and versions](https://github.com/hanbao-code/Cangoo/releases) · [Release notes](release_notes.md) · [Windows guide](docs/user_guide_en.md) · [Android guide](docs/android/user_guide_en.md) · [Build from source](docs/building.md#english)

### Features

- **Organize passwords and notes:** create, edit, search, favorite and sort records. Windows also supports pinyin search for Chinese text.
- **Use your login details:** reveal and copy passwords or one-time codes when needed; save recovery codes and mark them used yourself.
- **Check password security:** generate random passwords and check their strength and which records share a password, all on your device. Windows also flags passwords that have not changed for a long time.
- **Back up and restore:** export encrypted backups and compare their records with the current vault before restoring. Identical content is skipped; you choose how to handle differences.
- **Transfer between devices:** find a nearby device over a local network or Bluetooth. Check that both screens show the same numbers, then send everything, passwords only or notes only. After receiving all the data, the receiver compares it with the current vault and confirms the import.
- **Make the app comfortable to use:** Chinese and English interface and offline guides, themes, text sizes, auto-lock and clipboard cleanup. Windows includes Quick Bar; Android supports per-vault biometric quick unlock when the device supports it.
- **Choose when to update:** check at startup after your selected interval or check manually anytime. You decide whether to download and install.

### Download and install

Use the [releases page](https://github.com/hanbao-code/Cangoo/releases) to view files and notes for your platform. Windows and Android have separate version numbers. Device transfer is available starting with Windows 1.1.0 and Android 1.0.0.

| Platform | System requirements | Package and first step | Guide |
|---|---|---|---|
| Windows | Windows 10 version 1809 or later, or Windows 11; x64 (Intel/AMD 64-bit) | Run the installer's `setup.exe` and follow the wizard, or fully extract the portable archive before running it | [English](docs/user_guide_en.md) / [中文](docs/user_guide_zh.md) |
| Android | Android 10 or later; arm64 (64-bit ARM) | Install the APK on your phone, allowing that installation when the system asks | [English](docs/android/user_guide_en.md) / [中文](docs/android/user_guide_zh.md) |

Windows setup lets you choose the location, installation scope and desktop shortcut. Open it again to repair or uninstall. Uninstall keeps data by default; back up before selecting cleanup. When moving the portable edition, preserve its entire folder and any vaults stored elsewhere.

Windows files are not code-signed, so the system may show an unknown-publisher warning. Obtain files from this project's releases page and check the accompanying SHA-256 list. Checksums do not replace code signing.

### First use

1. Create a vault and set a master password. On Windows, choose where to save the database file and remember that location.
2. Add and save a record, then try finding and copying it. Cangoo stores information; it does not change passwords on websites or apps for you.
3. Export an encrypted backup and keep its password separately from the file. Periodically test a restore into an empty vault.

The author cannot recover forgotten master or backup passwords. Follow the guide for your platform, also available offline inside the app.

### Data and privacy

Vaults remain on your devices; Cangoo does not provide cloud hosting or automatic two-way synchronization. Update checks read public GitHub release information without sending vault contents or the master password. You initiate device transfers and verify both screens before selected contents are sent with encryption. The receiving vault is unchanged until the complete contents have arrived and you confirm their import.

### Feedback and contact

Contact the administrators through our [Telegram group](https://t.me/+kQEszbuHNEgxOGRh) for ordinary feedback. Include your platform, app and system versions, steps and the error message. For private discussions, join the group and message an administrator privately. Use [private reporting](SECURITY.md) for security vulnerabilities. Do not send real passwords, databases, backups or screenshots containing sensitive information.

### License

Cangoo uses **AGPL-3.0-only**, with a [limited additional permission for OpenSSL bundled with Windows](OPENSSL_EXCEPTION.md). See the [license notice](LICENSE.md) and [full license text](COPYING). Open-source licensing does not require you to disclose your vaults, notes or backups.

Original installer helper source explicitly marked as MIT uses its [separate directory license](apps/windows/packaging/windows/native/LICENSE). WiX and its derivatives retain MS-RL, and other third-party materials retain their own licenses. See the [license notice](LICENSE.md) and [third-party licenses and sources](docs/third_party_sources.md) for the full scope.

### Acknowledgements

[Python](https://www.python.org/) · [Qt](https://www.qt.io/) · [Jetpack Compose](https://developer.android.com/compose) · [SQLite](https://www.sqlite.org/) · [zxcvbn](https://github.com/dropbox/zxcvbn)
