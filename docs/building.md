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

### 准备安装工具与生成包体

按[Inno工具锁](../apps/windows/packaging/windows/inno_tool_lock.json)的官方来源准备Inno Setup 7.1.0，先核对安装器SHA-256及[原始许可](../third_party/inno_license.txt)。构建器核对ISCC和支持文件，不自动下载或全局安装工具。配置x64 MSVC的`cl.exe`、`INCLUDE`与`LIB`。

按[QtBluetooth构建说明](../apps/windows/packaging/windows/qt_bluetooth_build.md)准备固定DLL及对应源码归档，再执行：

```powershell
Set-Location "$repoRoot/apps/windows"
& "$repoRoot/.venv/Scripts/python.exe" -B tools/build_web_frontend.py --product-only
& "$repoRoot/.venv/Scripts/python.exe" -B tools/build_windows_packages.py `
    --output "$env:PDM_WORK_ROOT/releases/windows" `
    --iscc '<Inno工具目录>/ISCC.exe' `
    --compiler (Get-Command cl.exe).Source
```

每次输出新的 `<版本>_<时间>/`，包含Inno `setup.exe`、同一份程序文件生成的便携ZIP、安装构建记录、Inno原始许可及`sha256sums.txt`。QtBluetooth源码归档和补丁随程序提供。保留完整程序目录，单独复制EXE无法运行。失败会保留诊断目录；构建器不启动安装器或发布文件。

主体许可见[根许可](../LICENSE.md)；明确标为MIT的自有原生安装辅助按[独立MIT许可](../apps/windows/packaging/windows/native/LICENSE)提供，第三方组件各自原文保持。

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

此处构建的架构为 `arm64-v8a`。Release构建启用R8，生成 `app/build/outputs/apk/arm64/release/app-arm64-release-unsigned.apk`。它尚未签名，不能直接安装。开发构建可使用 `:app:assembleArm64Debug`，应用标识为 `app.cangoo.android.dev`，与正式应用不同。

### 本地签名

使用自己创建并长期保管的签名密钥；官方签名私钥不随源码提供。口令由工具交互询问，不放入命令参数、共享配置或仓库。以下命令仍在 `apps/android` 执行：

```powershell
$buildTools = Join-Path $env:ANDROID_HOME 'build-tools/36.1.0'
$unsignedApk = 'app/build/outputs/apk/arm64/release/app-arm64-release-unsigned.apk'
$signedApk = Join-Path $env:PDM_WORK_ROOT 'releases/android/cangoo-1.0.1-android-arm64.apk'
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

Use Inno Setup 7.1.0 from the [pinned tool lock](../apps/windows/packaging/windows/inno_tool_lock.json). Check the official installer hash and [original license](../third_party/inno_license.txt), then supply `--iscc` and the configured x64 MSVC `--compiler`. Prepare the QtBluetooth DLL and corresponding source archive as described in its build notes. Run the frontend and packaging commands from `apps/windows`.

The output contains Inno setup.exe, a portable ZIP from the same application files, a build record, the original Inno license and SHA-256 checksums. QtBluetooth source and patch materials remain in the application payload. The build does not install or publish files. The installer requires Windows 10 1809 or later. Main application and original native helper licensing remain defined in the [root license](../LICENSE.md) and [native MIT license](../apps/windows/packaging/windows/native/LICENSE).

Running `desktop.product_app` uses the current Windows user's Cangoo data directory. Use a separate test account and test databases when validating changes so that everyday data is not affected. Back up existing vaults before upgrading them.

For Android, use JDK 21, Android SDK platform 36, Build Tools 36.1.0 and a separate Python 3.11 interpreter. Set `JAVA_HOME`, `ANDROID_HOME`, `GRADLE_USER_HOME` and `ANDROID_USER_HOME` as shown, then run the included Gradle wrapper from `apps/android`. The first build needs network access; use `--offline` only after dependencies are cached. `:app:assembleArm64Release` enables R8 and produces an unsigned arm64 APK. `:app:assembleArm64Debug` uses the separate `app.cangoo.android.dev` identity.

Sign the release APK with your own long-lived key, using interactive password entry. Check ZIP alignment before signing and verify the signed result; do not modify it afterwards. Your signature cannot replace an official installation with a different signature. Back up and verify data before any uninstall or migration. Keep the same key and increment `versionCode` for later updates. Signing and alignment checks do not establish compatibility with every device. See the Android signing and tool documentation linked above.
