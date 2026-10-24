# 从源码构建 / Building from source

源码保留以下布局，请完整取得仓库，不要只复制某个平台目录：

```text
apps/windows/       Windows程序、前端资源与打包工具
apps/android/       Android应用、Gradle wrapper与构建配置
.venv/              自行创建的Windows Python环境，不随源码提供
```

Android构建按 `../windows` 读取八份评分核心、词表和翻译文件，以及共用许可内容。目录关系、源文件和第三方许可均需保留。下列命令以Windows PowerShell为例，每一步成功后再继续；本地构建不会发布或上传成品。

图标原稿位于 `docs/product/brand_assets/cangoo_c0_d1_o3_original.png`，`apps/windows/tools/export_brand_icons.py` 用于派生两端图标；普通构建直接使用已提供的图标，无需重新生成。

## 工作目录

在仓库根打开PowerShell。将占位值替换为自己选择的绝对目录；下列命令将外部临时文件、下载缓存及选定的成品输出放入该目录。Gradle项目缓存和中间产物仍位于 `apps/android` 内：

```powershell
$repoRoot = (Get-Location).Path
$env:PDM_WORK_ROOT = '<自选的绝对构建工作目录>'
New-Item -ItemType Directory -Force -Path "$env:PDM_WORK_ROOT/temp", "$env:PDM_WORK_ROOT/pip_cache" | Out-Null
$env:TEMP = "$env:PDM_WORK_ROOT/temp"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = "$env:PDM_WORK_ROOT/pip_cache"
```

这些设置只影响当前命令行会话。不要在源码目录内保存密码库、备份、签名私钥或口令。

## Windows

面向Windows 10/11 x64；安装器要求Windows 10 1809或更新系统。使用Python 3.10.11 x64、Git和Visual C++ Build Tools 2022。驱动及原生安装辅助代码采用MSVC 14.44.35207、Windows SDK 10.0.26100.0；运行安装构建前，先在Visual Studio的x64开发者命令行环境中配置 `cl.exe`、`INCLUDE` 和 `LIB`。

先在仓库根创建环境并安装固定依赖：

```powershell
py -3.10 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r apps/windows/packaging/windows/requirements.txt
```

再按[数据库驱动构建](../third_party/driver_build.md)校验、应用补丁并安装 `pysqleet 31.1.3`。不要用其他SQLite驱动代替它；驱动补丁位于 `apps/windows/packaging/windows/pysqleet_31_1_3.patch`。

### 准备固定安装工具

安装包使用WiX 7.0.0和独立的.NET Runtime 10.0.13。具体官方归档、SHA-512和解包布局以[tool_lock.json](../apps/windows/packaging/windows/msi/tool_lock.json)为准。

**下载和使用WiX官方二进制前，请自行阅读[其维护协议](../apps/windows/packaging/windows/msi/third_party/wix_osmf_eula.txt)，确认适用于你的条件。** 该协议与源码的MS-RL许可不同；是否需要付费，应按该协议和你的使用情况判断。

决定使用后，在一个新的工具目录按锁文件下载、核验和解包。不要覆盖已有工具目录：

```powershell
$toolchainRoot = Join-Path $env:PDM_WORK_ROOT 'wix_7_0_0'
$toolLock = Get-Content -LiteralPath "$repoRoot/apps/windows/packaging/windows/msi/tool_lock.json" -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $toolchainRoot -ErrorAction Stop | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($item in @($toolLock.runtime) + @($toolLock.packages)) {
    $archive = Join-Path $toolchainRoot $item.archive
    New-Item -ItemType Directory -Force -Path (Split-Path $archive) | Out-Null
    Invoke-WebRequest -Uri $item.url -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA512).Hash -ne $item.sha512) {
        throw "工具归档摘要不匹配：$($item.archive)"
    }
    [IO.Compression.ZipFile]::ExtractToDirectory($archive, (Join-Path $toolchainRoot $item.directory))
}
$wixSourceArchive = Join-Path $toolchainRoot $toolLock.source_archive.filename
Invoke-WebRequest -Uri $toolLock.source_archive.url -OutFile $wixSourceArchive
if ((Get-FileHash -LiteralPath $wixSourceArchive -Algorithm SHA256).Hash -ne $toolLock.source_archive.sha256) {
    throw 'WiX对应源码归档摘要不匹配'
}
```

构建器还会核对解包后的实际文件。它不自动下载工具、不全局安装，也不写入全局协议接受状态。

### 生成安装包与便携包

先生成前端资源：

```powershell
Set-Location "$repoRoot/apps/windows"
& "$repoRoot/.venv/Scripts/python.exe" -B tools/build_web_frontend.py --product-only
```

阅读并确认接受 WiX 维护协议后，在下面命令末尾添加 `--accept-wix-eula`。未添加时，构建器会在开始构建前退出。

```powershell
& "$repoRoot/.venv/Scripts/python.exe" -B tools/build_windows_packages.py `
    --output "$env:PDM_WORK_ROOT/releases/windows" `
    --toolchain $toolchainRoot `
    --wix-source-archive $wixSourceArchive `
    --compiler (Get-Command cl.exe).Source
```

`--toolchain`是按锁文件准备的目录，`--wix-source-archive`是与固定WiX提交对应的完整源码ZIP；二者分别校验。`--compiler`是MSVC的 `cl.exe`，不能代替x64的 `INCLUDE`／`LIB` 环境。

每次输出独立的 `<版本>_<时间>` 目录，包含Burn `setup.exe`、从同一份程序文件生成的便携ZIP、安装构建记录、完整WiX源码归档 `wix-b8977d6f88e7b68e000bac226a2814f236770570.zip` 及 `sha256sums.txt`。源码归档必须随安装包一同交付，不能仅用上游链接代替；无需将该归档提交到 Git。用户通过 `setup.exe` 安装和维护程序，MSI 已包含在其中。

保留完整程序目录；只复制EXE不能正常运行。构建失败时会报告保留的诊断目录，请修正输入后重新构建，仅使用构建成功的完整输出。

主体软件的AGPL-3.0-only及限定OpenSSL例外见[根许可](../LICENSE.md)。仅明确标记为MIT的自有原生安装辅助源码适用[独立MIT许可](../apps/windows/packaging/windows/native/LICENSE)；WiX上游及其派生主题等材料保留[MS-RL](../apps/windows/packaging/windows/msi/third_party/wix_license.txt)。

需要从源码运行时，在 `apps/windows` 执行：

```powershell
Set-Location "$repoRoot/apps/windows"
& "$repoRoot/.venv/Scripts/python.exe" -B -m desktop.product_app
```

此命令会使用当前 Windows 用户的小仓数据目录。验证修改时，请使用独立的测试账号和测试库，以免影响日常资料；升级正在使用的数据库前先备份。第三方库的来源与替换方法见[第三方说明](third_party_sources.md)。

## Android

使用JDK 21、Android SDK平台36、Build Tools 36.1.0及Python 3.11。Gradle 9.4.1由wrapper取得，Android构建插件及依赖版本由工程固定。构建Python与Windows的Python 3.10环境分开，Chaquopy依赖由Gradle安装到构建目录。

填写本机工具路径，并在同一PowerShell会话中设置缓存位置：

```powershell
$env:JAVA_HOME = '<JDK 21绝对目录>'
$env:ANDROID_HOME = '<Android SDK绝对目录>'
$strengthPython = '<Python 3.11解释器绝对路径>'
$env:GRADLE_USER_HOME = "$env:PDM_WORK_ROOT/android/gradle"
$env:ANDROID_USER_HOME = "$env:PDM_WORK_ROOT/android/user_home"
New-Item -ItemType Directory -Force -Path $env:GRADLE_USER_HOME, $env:ANDROID_USER_HOME | Out-Null
Set-Location "$repoRoot/apps/android"
./gradlew.bat "-PstrengthBuildPython=$strengthPython" :app:assembleArm64Release
```

首次构建需要联网取得Gradle、依赖和Python组件；仅在所需内容已缓存时使用 `--offline`。也可在未入库的 `local.properties` 设置本机 `sdk.dir`。构建前会核对共用许可与生成资源；修改许可真源后运行 `scripts/generate_legal_content.py` 更新，再构建。

当前首发架构为 `arm64-v8a`。Release构建启用R8，生成 `app/build/outputs/apk/arm64/release/app-arm64-release-unsigned.apk`。它尚未签名，不能直接安装。开发构建可使用 `:app:assembleArm64Debug`，应用标识为 `app.cangoo.android.dev`，与正式应用不同。

### 本地签名

使用自己创建并长期保管的签名密钥；官方签名私钥不随源码提供。口令由工具交互询问，不放入命令参数、共享配置或仓库。以下命令仍在 `apps/android` 执行：

```powershell
$buildTools = Join-Path $env:ANDROID_HOME 'build-tools/36.1.0'
$unsignedApk = 'app/build/outputs/apk/arm64/release/app-arm64-release-unsigned.apk'
$signedApk = Join-Path $env:PDM_WORK_ROOT 'releases/android/cangoo-1.0.0-android-arm64.apk'
New-Item -ItemType Directory -Force -Path (Split-Path $signedApk) | Out-Null
& "$buildTools/zipalign.exe" -c -P 16 -v 4 $unsignedApk
& "$buildTools/apksigner.bat" sign --ks '<自己的密钥文件绝对路径>' `
    --ks-key-alias '<密钥别名>' --v4-signing-enabled false --out $signedApk $unsignedApk
& "$buildTools/apksigner.bat" verify --verbose --print-certs $signedApk
Get-FileHash -LiteralPath $signedApk -Algorithm SHA256
```

若对齐或签名检查失败，先修正未签名包；签名后不得再改包。正式安装要求应用标识和签名匹配；自己签名的包不能直接覆盖官方签名应用。不要为安装测试包而卸载含真实资料的应用，先制作并验证独立加密备份。

签名和对齐检查不等于所有设备兼容性验证。后续更新需保持同一签名并递增 `versionCode`。工具说明见Android官方的[应用签名](https://developer.android.com/studio/publish/app-signing)、[zipalign](https://developer.android.com/tools/zipalign)和[apksigner](https://developer.android.com/tools/apksigner)。

## English

Keep `apps/windows` and `apps/android` together. The Android build reads eight shared password-strength source, dictionary and translation files, plus the shared license content, from `../windows`. Do not flatten or split these directories.

The original icon image is `docs/product/brand_assets/cangoo_c0_d1_o3_original.png`; `apps/windows/tools/export_brand_icons.py` derives the platform icons. Ordinary builds use the supplied icons without regenerating them.

Run the PowerShell commands above one step at a time and stop on failure. Start at the repository root, set `PDM_WORK_ROOT` to an absolute writable work directory of your choice, and replace every tool-path placeholder. These commands keep external temporary files, download caches and selected release output in that work directory. Gradle project caches and intermediate output remain under `apps/android`. Build commands do not publish or upload artifacts.

For Windows, create `.venv` at the repository root with Python 3.10.11 x64 and install `apps/windows/packaging/windows/requirements.txt`. Build the pinned database driver using [these instructions](../third_party/driver_build.md#english). Configure the x64 MSVC 14.44.35207 / Windows SDK 10.0.26100.0 development environment, including `cl.exe`, `INCLUDE` and `LIB`.

The installer uses WiX 7.0.0 with a standalone .NET Runtime 10.0.13. Read the [WiX binary maintenance agreement](../apps/windows/packaging/windows/msi/third_party/wix_osmf_eula.txt) and make your own applicability and acceptance decision before downloading or using the binaries. Prepare a fresh tool directory using the URLs, SHA-512 hashes and extraction paths in [tool_lock.json](../apps/windows/packaging/windows/msi/tool_lock.json). The PowerShell loop above checks each archive before extracting it. Nothing is installed globally.

Run the frontend and packaging commands from `apps/windows`. `--toolchain` names the prepared tool directory and `--compiler` names MSVC `cl.exe`. After reading and accepting the WiX maintenance agreement, add `--accept-wix-eula` to the command; without it, the builder exits before building. Pass the complete source ZIP from the same WiX commit as `--wix-source-archive`. The output contains a Burn setup.exe with its internal MSI, a portable ZIP using the same application files, a build record, `wix-b8977d6f88e7b68e000bac226a2814f236770570.zip` and SHA-256 checksums. Distribute this source archive with the installer; an upstream URL alone is not a replacement. There is no need to commit the archive to Git. Users install and maintain the app through setup.exe, which includes the MSI. The installer requires Windows 10 1809 or later.

The main application remains AGPL-3.0-only with the limited OpenSSL exception. Only original native helpers explicitly marked as MIT have the separate MIT scope defined in the [root license](../LICENSE.md) and [native license](../apps/windows/packaging/windows/native/LICENSE). Upstream WiX code and its derivatives retain MS-RL. Running `desktop.product_app` uses the current Windows user's Cangoo data directory. Use a separate test account and test databases when validating changes so that everyday data is not affected. Back up existing vaults before upgrading them.

For Android, use JDK 21, Android SDK platform 36, Build Tools 36.1.0 and a separate Python 3.11 interpreter. Set `JAVA_HOME`, `ANDROID_HOME`, `GRADLE_USER_HOME` and `ANDROID_USER_HOME` as shown, then run the included Gradle wrapper from `apps/android`. The first build needs network access; use `--offline` only after dependencies are cached. `:app:assembleArm64Release` enables R8 and produces an unsigned arm64 APK. `:app:assembleArm64Debug` uses the separate `app.cangoo.android.dev` identity.

Sign the release APK with your own long-lived key, using interactive password entry. Check ZIP alignment before signing and verify the signed result; do not modify it afterwards. Your signature cannot replace an official installation with a different signature. Back up and verify data before any uninstall or migration. Keep the same key and increment `versionCode` for later updates. Signing and alignment checks do not establish compatibility with every device. See the Android signing and tool documentation linked above.
