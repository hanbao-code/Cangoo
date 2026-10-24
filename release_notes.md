# 小仓版本说明 / Cangoo release notes

电脑版与安卓版各有自己的版本号。文件与校验清单见[发行页面](https://github.com/hanbao-code/Cangoo/releases)，操作步骤见[电脑版手册](docs/user_guide_zh.md)和[安卓版手册](docs/android/user_guide_zh.md)。

## Windows 1.1.0

适用于 Windows 10（1809及以上）或 Windows 11 的 x64 电脑，提供安装版和便携版。

- **恢复码随账号保存：**逐条查看、复制、手动标记已用，也可撤销误标；备份会保留整组恢复码及其已用标记。
- **查找更方便：**密码名称、账号和记事标题支持中文拼音全拼或首字母搜索；设置也可按名称或说明查找。
- **密码检查持续更新：**保存记录后在本机继续检查密码强度，未完成和失败状态明确显示；需要时可重新检查全部密码，不必逐条打开记录。
- **导入前看清差异：**逐项对照备份或接收资料与当前库的记录；密码等敏感内容默认隐藏，点击一次即可同时查看两侧。支持筛选和批量处理，翻页后仍保留勾选，相同内容自动跳过。
- **设备间传输：**局域网或蓝牙发送全部、仅密码或仅记事；两端核对显示的数字，确认一致后传输。接收端收齐资料后可继续比较和导入，发送端无需保持连接。局域网支持查找附近设备和手动地址连接。
- **按需检查更新：**设置启动检查间隔，也可手动检查；可暂停某版本提醒7天或不再提醒该版本，下载与安装由你决定。
- **安装与维护：**同一个安装包提供安装、修复和卸载入口，支持中文与英文。

### 卸载与资料

卸载默认保留资料。确需清理时，先核对备份，勾选清理并点击“卸载并清除所选资料”；程序成功卸载后才清除当前 Windows 用户的默认库、设置和本机安全记录，且无法撤销。其他密码库、所有备份和其他 Windows 用户的数据都会保留。无法确认身份或清理范围时会保留并提示，请以页面显示的资料处理结果为准。

### 旧库与备份

升级前请制作加密备份。首次打开需要升级的旧库时，小仓会先保存一份升级前的原样加密副本，再升级数据库。Windows 1.0.0不能直接读取新版含恢复码的库；如需回用旧版，请先复制一份升级前保存的数据库副本，再用旧版打开这份复制文件，并保留当前新版库。升级前的副本不含后来新增或修改的资料。

旧版加密备份仍可导入，但其中没有恢复码。若用它覆盖当前含恢复码的记录，整组恢复码会被清空；导入预览会提示，选择跳过可保留当前记录。

Windows 文件未使用代码签名，系统可能提示发行者未知。请从[本项目发行页面](https://github.com/hanbao-code/Cangoo/releases)取得文件并核对 SHA-256 清单；校验值不能替代代码签名。

## Android 1.0.0

适用于 Android 10及以上的 arm64 手机。

- 在本地保存密码和加密记事，按名称、账号或记事内容查找，使用收藏和最近打开记录快速取用。
- 显示动态验证码，保存恢复码并管理本地已用标记。
- 生成随机密码，在本机检查密码强度和重复使用情况。
- 导出加密备份，恢复前对照差异、筛选并批量处理；长文可单独打开比较。
- 通过局域网或蓝牙与另一台设备传输资料，接收后确认导入；与 Windows 1.1.0互通。
- 在设备支持时，为各密码库独立启用生物识别快捷解锁，并设置无操作或离开软件时锁库。
- 提供中英文离线帮助、主题和字号设置，以及可关闭的启动版本检查和随时可用的手动检查。

迁移资料时，可使用小仓加密备份或设备传输。接收后先核对记录和重要内容；主密码、软件设置和生物识别绑定不随资料迁移，需在新设备分别设置。

APK 签名证书 SHA-256：

`5d7d3d425c4cc8b2dd301723d1afbeb63afce476cea8bdc8e277d2cb8e04d126`

## Windows 1.0.0

提供密码与加密记事管理、安全体检、密码生成与强度检测、快捷搜索条、加密备份恢复和中英文离线帮助，包含安装版和便携版。此版本不支持恢复码；使用新版资料前，请留意上方的旧库与备份说明。

## 许可

Windows 1.1.0与Android 1.0.0采用 AGPL-3.0-only，Windows 随包 OpenSSL 另有[限定附加许可](OPENSSL_EXCEPTION.md)。明确标记为 MIT 的自有安装辅助源码单独适用[该目录许可](apps/windows/packaging/windows/native/LICENSE)；WiX 及其派生材料保留 MS-RL，其他第三方材料保留各自许可。见[许可说明](LICENSE.md)、[许可证全文](COPYING)和[第三方许可及来源](docs/third_party_sources.md)。

## English

Windows and Android have separate version numbers. See the [releases page](https://github.com/hanbao-code/Cangoo/releases) for files and checksums, and the [Windows](docs/user_guide_en.md) or [Android](docs/android/user_guide_en.md) guide for instructions.

### Windows 1.1.0

For x64 computers running Windows 10 version 1809 or later, or Windows 11. Package types are installer and portable.

- **Keep recovery codes with each account:** view, copy and manually mark individual codes used, or undo an accidental mark. Backups preserve the full set of recovery codes and their used marks.
- **Find records more easily:** search Chinese password names, accounts and note titles using full pinyin or initials. Find settings by name or description too.
- **Keep password checks current:** password-strength checks continue locally after saving. Pending and failed checks are shown clearly; run a full check when needed without opening each record.
- **See differences before importing:** compare records from a backup or received data with your current vault. Passwords and other sensitive values start hidden; reveal both sides with one click. Filter results and apply bulk actions, with selections kept when you change pages. Identical content is skipped automatically.
- **Transfer between devices:** send everything, passwords only or notes only over a local network or Bluetooth after checking that both screens show the same numbers. Once all the data has arrived, the receiver can continue comparing and importing without keeping the sender connected. Local network transfers support discovery and manual address entry.
- **Check for updates when you choose:** set a startup-check interval or check manually. Pause reminders for seven days or ignore a particular version. You decide whether to download and install.
- **Install and maintain:** one setup package provides installation, repair and uninstall in Chinese or English.

#### Uninstall and data

Uninstall keeps data by default. If you want cleanup, check your backup first, select the cleanup option and choose Uninstall and clear selected data. Only after successful program removal are the current Windows user's default vault, settings and local security records deleted. This cannot be undone. Other vaults, all backups and other Windows users' data remain. If identity or cleanup scope cannot be verified, data is retained with an explanation; read the displayed data-cleanup result.

#### Older vaults and backups

Make an encrypted backup before upgrading. When an older vault needs upgrading, Cangoo first saves an unchanged encrypted copy, then upgrades the database. Windows 1.0.0 cannot directly read the newer vault format containing recovery codes. To use the older app again, first duplicate the pre-upgrade database copy, then open that duplicate with the older app. Keep your current vault as well. The old copy contains none of the additions or changes made after upgrading.

Older encrypted backups can still be imported, but they do not contain recovery codes. Using one to overwrite a current record with recovery codes removes that entire set. The preview warns about this; skip the record to keep its current contents.

Windows files are not code-signed, so the system may show an unknown-publisher warning. Obtain files from [this project's releases page](https://github.com/hanbao-code/Cangoo/releases) and verify the SHA-256 list. Checksums do not replace code signing.

### Android 1.0.0

For arm64 phones running Android 10 or later.

- Store passwords and encrypted notes locally. Search names, accounts or note contents, and use favorites and recently opened records for quick access.
- Display one-time codes, save recovery codes and manage their local used marks.
- Generate random passwords and check password strength and reuse locally.
- Export encrypted backups, then compare, filter and apply bulk decisions before restoring. Open a separate comparison for long text.
- Transfer contents to another device over a local network or Bluetooth, then confirm the import on the receiver. Compatible with Windows 1.1.0.
- Enable biometric quick unlock separately for each vault on supported devices, and choose inactivity or app-leaving locking.
- Use offline Chinese and English help, themes, text-size settings, optional startup update checks and manual checks anytime.

Move records using a Cangoo encrypted backup or device transfer, then verify the received records and important contents. Master passwords, app settings and biometric bindings are not transferred; configure them separately on the new device.

APK signing certificate SHA-256:

`5d7d3d425c4cc8b2dd301723d1afbeb63afce476cea8bdc8e277d2cb8e04d126`

### Windows 1.0.0

Includes password and encrypted-note management, security checks, password generation and strength estimates, Quick Bar, encrypted backup and restore, and offline Chinese and English help, with installer and portable editions. This version does not support recovery codes. Read the older-vault and backup guidance above before using newer data.

### License

Windows 1.1.0 and Android 1.0.0 use AGPL-3.0-only, with a [limited additional permission](OPENSSL_EXCEPTION.md) for OpenSSL bundled with Windows. Original installer helper source explicitly marked as MIT uses its [separate directory license](apps/windows/packaging/windows/native/LICENSE). WiX and its derivatives retain MS-RL, and other third-party materials retain their own licenses. See the [license notice](LICENSE.md), [full license text](COPYING) and [third-party licenses and sources](docs/third_party_sources.md).
