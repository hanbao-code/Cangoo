# 小仓 / Cangoo

小仓是一款适用于 Windows 和 Android 的本地密码管理器，支持加密记事、加密备份和设备间传输。

账号、密码、动态验证码密钥和恢复码可集中保存在自己的密码库中，按需查找、复制或备份。

[下载与版本](https://github.com/hanbao-code/Cangoo/releases) · [版本说明](release_notes.md) · [电脑版手册](docs/user_guide_zh.md) · [安卓版手册](docs/android/user_guide_zh.md) · [从源码构建](docs/building.md) · [English](#english)

## 主要功能

- **整理密码与记事：**新建、编辑、搜索、收藏和排序；电脑版还支持中文拼音查找。
- **更方便地登录：**按需查看、复制密码和动态验证码；保存恢复码并手动标记已用。
- **生成与检查密码：**生成随机密码，在本机估算密码强度、查找重复使用的密码；电脑版还可按记录的更换时间提醒长期未更换的密码。
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

主密码用于解锁密码库，备份密码用于解密对应的备份文件。请分别妥善保管；小仓不提供这两类密码的找回功能。

创建密码库、保存记录和备份恢复的步骤见对应平台的手册，也可在软件内离线阅读。

## 资料与隐私

密码库保存在你的设备上，查看、编辑和密码强度分析都在本机完成。小仓不提供云端密码库。

- **检查更新时：**联网读取 GitHub 上的公开发行信息，请求不包含密码库内容或主密码。自动检查可在设置中关闭。
- **传输资料时：**由你选择接收设备和资料范围，两端核对数字并确认后加密传送。收齐并校验后，接收端还需比较资料、确认导入，才会写入密码库。传输不会自动让两库持续保持一致。

## 反馈与联系

使用中遇到问题，可加入[Telegram（电报）交流群](https://t.me/+kQEszbuHNEgxOGRh)交流，说明平台、应用及系统版本、操作经过和错误提示。请用虚构资料举例，截图前遮去敏感内容，不发送真实密码、密码库或备份文件。安全漏洞请按[安全问题报告说明](SECURITY.md)私下报告。

## 许可

小仓采用 **AGPL-3.0-only**，附[针对 Windows 随包 OpenSSL 的限定附加许可](OPENSSL_EXCEPTION.md)。见[许可说明](LICENSE.md)和[许可证全文](COPYING)。软件开源不要求公开用户的密码库、记事或备份。

明确标记为 MIT 的自有安装器辅助源码单独适用[该目录许可](apps/windows/packaging/windows/native/LICENSE)；WiX 及其派生材料保留 MS-RL，其他第三方材料保留各自许可。完整范围见[许可说明](LICENSE.md)和[第三方许可及来源](docs/third_party_sources.md)。

## 致谢

[Python](https://www.python.org/) · [Qt](https://www.qt.io/) · [Jetpack Compose](https://developer.android.com/compose) · [SQLite](https://www.sqlite.org/) · [zxcvbn](https://github.com/dropbox/zxcvbn)

## English

Cangoo is a local password manager for Windows and Android, with encrypted notes, encrypted backups and device-to-device transfers.

Keep accounts, passwords, authenticator setup keys and recovery codes in your own vault, ready to find, copy or back up when needed.

[Downloads and versions](https://github.com/hanbao-code/Cangoo/releases) · [Release notes](release_notes.md) · [Windows guide](docs/user_guide_en.md) · [Android guide](docs/android/user_guide_en.md) · [Build from source](docs/building.md#english)

### Features

- **Organize passwords and notes:** create, edit, search, favorite and sort records. Windows also supports pinyin search for Chinese text.
- **Use your login details:** reveal and copy passwords or one-time codes when needed; save recovery codes and mark them used yourself.
- **Generate and check passwords:** generate random passwords, estimate their strength and find reused passwords on your device. Windows also flags long-unchanged passwords using their recorded change dates.
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

The master password unlocks a vault; a backup password decrypts its corresponding backup file. Keep each password safe. Cangoo has no recovery function for either kind of password.

Follow your platform guide to create a vault, save records and back up or restore data. The guides are also available offline inside the app.

### Data and privacy

Vaults are stored on your devices. Viewing, editing and password-strength analysis take place locally. Cangoo does not provide cloud vault storage.

- **Update checks:** the app connects to GitHub to read public release information. The requests contain no vault contents or master password. You can turn off automatic checks in Settings.
- **Device transfers:** you choose the receiver and the data to send. After both sides check the verification numbers and confirm, the selected data is sent encrypted. The receiver must receive and validate it, compare records and confirm the import before it is written to the vault. A transfer does not keep the two vaults synchronized afterwards.

### Feedback and contact

For help using the app, join the [Telegram group](https://t.me/+kQEszbuHNEgxOGRh). Include your platform, app and system versions, steps and the error message. Use made-up data in examples and hide sensitive details in screenshots. Do not send real passwords, vaults or backup files. Report security vulnerabilities [privately](SECURITY.md).

### License

Cangoo uses **AGPL-3.0-only**, with a [limited additional permission for OpenSSL bundled with Windows](OPENSSL_EXCEPTION.md). See the [license notice](LICENSE.md) and [full license text](COPYING). Open-source licensing does not require you to disclose your vaults, notes or backups.

Original installer helper source explicitly marked as MIT uses its [separate directory license](apps/windows/packaging/windows/native/LICENSE). WiX and its derivatives retain MS-RL, and other third-party materials retain their own licenses. See the [license notice](LICENSE.md) and [third-party licenses and sources](docs/third_party_sources.md) for the full scope.

### Acknowledgements

[Python](https://www.python.org/) · [Qt](https://www.qt.io/) · [Jetpack Compose](https://developer.android.com/compose) · [SQLite](https://www.sqlite.org/) · [zxcvbn](https://github.com/dropbox/zxcvbn)
