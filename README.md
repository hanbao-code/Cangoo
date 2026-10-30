# 小仓 / Cangoo

小仓是一款适用于 Windows 和 Android 的本地密码管理器，支持加密记事、加密备份和设备间传输。

[下载](https://github.com/hanbao-code/Cangoo/releases) · [版本说明](release_notes.md) · [电脑版手册](docs/user_guide_zh.md) · [安卓版手册](docs/android/user_guide_zh.md) · [从源码构建](docs/building.md) · [English](#english)

## 主要功能

- 管理密码与加密记事，支持搜索、收藏和排序。
- 生成动态验证码，保存恢复码及其使用标记。
- 生成随机密码，在本机检查密码强度和重复使用情况。
- 导出加密备份，恢复前比较记录差异。
- 通过局域网或蓝牙传输资料；备份与发送均可自定义选择密码和记事。
- 提供中英文界面与离线手册、主题、字号和自动锁定设置。

## 下载与安装

| 平台 | 版本 | 系统要求 | 安装方式 |
|---|---|---|---|
| Windows | 1.1.2 | Windows 10（1809及以上）或 Windows 11，x64 | 运行安装包，或完整解压便携包后运行 |
| Android | 1.0.2 | Android 10及以上，arm64 | 下载并安装 APK |

文件及 SHA-256 校验清单见[发行页面](https://github.com/hanbao-code/Cangoo/releases)。Windows 文件未使用代码签名，系统可能提示发行者未知；请核对来源和校验值。

从旧 MSI 安装版升级时，请先备份并保留资料卸载旧版，再安装新版，详见[电脑版手册](docs/user_guide_zh.md#安装迁移与卸载)。移动便携版时保留整个目录，以及另存的密码库。

设备传输需要 Windows 1.1.1、Android 1.0.1 或更新的兼容版本。使用旧版接收自定义选择时，范围文字可能沿用旧名称，实际只包含发送端选中的记录。

## 资料与隐私

密码库保存在你的设备上，查看、编辑和密码强度分析均在本机完成。小仓不提供云端密码库，也无法找回主密码或备份密码，请定期备份并分别保管密码和文件。

版本检查读取 GitHub 的公开发行信息，不发送密码库内容或主密码，可在设置中关闭自动检查。设备传输由双方确认后加密发送，接收端核对并确认导入后才写入密码库，不会自动持续同步。

## 反馈与许可

使用问题可在[Telegram 交流群](https://t.me/+kQEszbuHNEgxOGRh)反馈；安全漏洞请按[安全问题报告说明](SECURITY.md)私下报告。请提供版本、操作步骤和错误提示，不发送真实密码、密码库或备份。

小仓采用 **AGPL-3.0-only**，附[针对 Windows 随包 OpenSSL 的限定附加许可](OPENSSL_EXCEPTION.md)。明确标记为 MIT 的自有安装器辅助源码单独适用其许可；其他第三方材料保留各自许可。详见[许可说明](LICENSE.md)、[许可证全文](COPYING)和[第三方来源](docs/third_party_sources.md)。

## English

Cangoo is a local password manager for Windows and Android, with encrypted notes, encrypted backups and device-to-device transfers.

[Downloads](https://github.com/hanbao-code/Cangoo/releases) · [Release notes](release_notes.md) · [Windows guide](docs/user_guide_en.md) · [Android guide](docs/android/user_guide_en.md) · [Build from source](docs/building.md#english)

### Features

- Manage passwords and encrypted notes with search, favorites and sorting.
- Generate one-time codes and store recovery codes with usage markers.
- Generate random passwords and check password strength and reuse locally.
- Export encrypted backups and compare records before restoring them.
- Transfer data over a local network or Bluetooth; choose individual passwords and notes for backups and transfers.
- Use Chinese or English, offline guides, themes, text sizes and auto-lock settings.

### Download and install

| Platform | Version | Requirements | Installation |
|---|---|---|---|
| Windows | 1.1.2 | Windows 10 version 1809 or later, or Windows 11; x64 | Run the installer, or fully extract and run the portable edition |
| Android | 1.0.2 | Android 10 or later; arm64 | Download and install the APK |

Files and SHA-256 checksums are on the [releases page](https://github.com/hanbao-code/Cangoo/releases). Windows files are not code-signed and may trigger an unknown-publisher warning. Check the source and checksum before installation.

When upgrading from the previous MSI installer, back up and uninstall it with data cleanup unchecked, then install the new version. See the [Windows guide](docs/user_guide_en.md#install-migrate-and-uninstall). When moving the portable edition, keep the entire folder and any vaults stored elsewhere.

Device transfer requires Windows 1.1.1, Android 1.0.1 or later compatible versions. An older receiver may show its original scope label for a custom selection, but receives only the selected records.

### Data and privacy

Vaults are stored on your devices. Viewing, editing and password-strength analysis take place locally. Cangoo provides neither cloud vault storage nor master-password or backup-password recovery. Back up regularly and keep backup passwords separately from the files.

Update checks read public release information from GitHub without sending vault contents or master passwords. Automatic checks can be disabled in Settings. Device transfers are encrypted after both sides confirm; received records are written to the vault only after you review and confirm the import. Transfers do not keep vaults synchronized afterwards.

### Feedback and license

Ask for help in the [Telegram group](https://t.me/+kQEszbuHNEgxOGRh). Report security vulnerabilities [privately](SECURITY.md). Include versions, steps and error messages, but never send real passwords, vaults or backups.

Cangoo uses **AGPL-3.0-only**, with a [limited additional permission for OpenSSL bundled with Windows](OPENSSL_EXCEPTION.md). Original installer helpers explicitly marked as MIT use their separate license; third-party materials retain their own licenses. See the [license notice](LICENSE.md), [full license text](COPYING) and [third-party sources](docs/third_party_sources.md).
