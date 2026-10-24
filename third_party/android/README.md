# 安卓第三方来源与许可 / Android third-party sources and licenses

本目录提供Android 1.0.0 arm64所用组件、原生库的来源及25项随包许可正文。版本与支持范围见[版本说明](../../release_notes.md)。

These materials provide component and native-library sources and 25 bundled license texts for Android 1.0.0 arm64. See the [release notes](../../release_notes.md) for version and platform support.

[双端第三方材料入口 / All platform sources](../../docs/third_party_sources.md) · [中文手册](../../docs/android/user_guide_zh.md) · [English guide](../../docs/android/user_guide_en.md)

## 界面、存储与数据处理 / UI, storage and data handling

| 组件 / Component | 当前版本 / Version | 许可原文 / License text | 官方来源 / Upstream source |
|---|---|---|---|
| AndroidX Compose（原生界面组件）：UI、Foundation | 1.9.4 | [Apache 2.0](licenses/androidx_license.txt) | [UI 制品 / UI artifact](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.9.4/ui-android-1.9.4.aar)、[Foundation 制品 / Foundation artifact](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.9.4/foundation-android-1.9.4.aar) |
| AndroidX Material 3（原生界面组件） | 1.4.0 | [Apache 2.0](licenses/androidx_license.txt) | [固定版本制品 / Versioned artifact](https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3-android/1.4.0/material3-android-1.4.0.aar) |
| AndroidX Activity Compose（界面宿主） | 1.11.0 | [Apache 2.0](licenses/androidx_license.txt) | [固定版本制品 / Versioned artifact](https://dl.google.com/dl/android/maven2/androidx/activity/activity-compose/1.11.0/activity-compose-1.11.0.aar) |
| AndroidX Lifecycle ViewModel Compose、KTX（生命周期组件） | 2.9.4 | [Apache 2.0](licenses/androidx_license.txt) | [Compose 制品 / Compose artifact](https://dl.google.com/dl/android/maven2/androidx/lifecycle/lifecycle-viewmodel-compose-android/2.9.4/lifecycle-viewmodel-compose-android-2.9.4.aar)、[KTX 制品 / KTX artifact](https://dl.google.com/dl/android/maven2/androidx/lifecycle/lifecycle-viewmodel-ktx/2.9.4/lifecycle-viewmodel-ktx-2.9.4.aar) |
| AndroidX Room Runtime、KTX（数据库访问组件） | 2.8.5 | [Apache 2.0](licenses/androidx_license.txt) | [Runtime 制品 / Runtime artifact](https://dl.google.com/dl/android/maven2/androidx/room/room-runtime-android/2.8.5/room-runtime-android-2.8.5.aar)、[KTX 制品 / KTX artifact](https://dl.google.com/dl/android/maven2/androidx/room/room-ktx/2.8.5/room-ktx-2.8.5.aar) |
| kotlinx.coroutines（协程运行库） | 1.8.1 | [Apache 2.0及NOTICE / Apache 2.0 and NOTICE](licenses/kotlinx_coroutines_1_8_1_license.txt) | [固定版本来源 / Versioned source](https://github.com/Kotlin/kotlinx.coroutines/tree/1.8.1) |
| SQLCipher Android（数据库加密组件） | 4.19.1 | [安卓组件许可 / Android license](licenses/sqlcipher_android_4_19_1_license.txt)、[引擎许可 / Engine license](licenses/sqlcipher_engine_license.txt)、[LibTomCrypt 许可](licenses/libtomcrypt_license.txt) | [固定版本源码 / Versioned source](https://github.com/sqlcipher/sqlcipher-android/tree/v4.19.1)、[许可说明 / License information](https://www.zetetic.net/sqlcipher/license/) |
| Bouncy Castle（密码学库） | 1.86 | [MIT 许可原文 / MIT license](licenses/bouncycastle_1_86_license.html) | [固定版本源码 / Versioned source](https://github.com/bcgit/bc-java/tree/r1rv86) |
| Gson（结构化数据解析库） | 2.14.0 | [许可及版权 / License and copyright](licenses/gson_license.txt) | [固定版本源码 / Versioned source](https://github.com/google/gson/tree/gson-parent-2.14.0) |
| Jackson Core（结构化数据解析库） | 2.22.3 | [主体及内嵌实现的许可声明 / Component and embedded notices](licenses/jackson_core_license.txt) | [固定版本制品 / Versioned artifacts](https://repo.maven.apache.org/maven2/com/fasterxml/jackson/core/jackson-core/2.22.3/) |
| Radix Icons（图标原始路径） | 1.3.2 | [MIT 许可 / MIT license](licenses/radix_icons_license.txt) | [官方项目 / Upstream project](https://github.com/radix-ui/icons) |

Compose（界面工具包）版本由 `2025.10.01` 依赖集合固定。上述8份 AndroidX（安卓扩展库）制品内的许可原文一致，本目录只保留一份相同字节的文本；它不代替其他传递组件可能带有的独立声明。[AndroidX 官方来源](https://android.googlesource.com/platform/frameworks/support/)

The Compose versions are pinned by the `2025.10.01` dependency platform. The eight AndroidX artifacts above contain identical license text, retained once without changes. Other transitive components may require separate notices. [AndroidX upstream source](https://android.googlesource.com/platform/frameworks/support/)

SQLCipher Android（数据库加密组件）4.19.1 的固定源码指向引擎提交 `c4b275a47932888216bade83aff2bbc73df0ff85` 和 LibTomCrypt（密码学实现）提交 `476a9579ae94f32b9ea9e2747bfb04b302370259`；本目录分别保留对应[引擎许可来源](https://raw.githubusercontent.com/sqlcipher/sqlcipher/c4b275a47932888216bade83aff2bbc73df0ff85/LICENSE.md)与[LibTomCrypt 许可来源](https://raw.githubusercontent.com/sqlcipher/libtomcrypt/476a9579ae94f32b9ea9e2747bfb04b302370259/LICENSE)。其中的 SQLite（数据库引擎）及安卓来源代码仍按各自原始声明处理。

The SQLCipher Android 4.19.1 source pins engine commit `c4b275a47932888216bade83aff2bbc73df0ff85` and LibTomCrypt commit `476a9579ae94f32b9ea9e2747bfb04b302370259`. Their corresponding license texts are retained here. SQLite and Android-derived code retain their respective original notices.

## 密码强度运行组件 / Password-strength runtime

以下原文与当前应用资源逐字节一致；[原始来源与 SHA-256 摘要清单 / Original sources and SHA-256 hashes](licenses/password_strength/sources.json)保留各文件的原始出处及摘要。
清单中 `assets/chaquopy/…` 表示安装包内归档成员，不是本机文件路径。

These texts match the current app resources byte for byte. The linked manifest records original sources and SHA-256 hashes. Paths beginning with `assets/chaquopy/…` identify archive members inside an installation package, not local machine paths.

| 组件 / Component | 许可原文 / License text |
|---|---|
| Python 3.11.17（语言运行时） | [Python 许可 / Python license](licenses/password_strength/python_3_11_17_license.txt) |
| Chaquopy 17.1.0（安卓 Python 集成运行库） | [许可 / License](licenses/password_strength/chaquopy_17_1_0_license.txt) |
| OpenSSL 3.5.9（Python运行时密码学库） | [Apache 2.0](licenses/openssl_3_5_9_license.txt) · [固定版本来源 / Versioned source](https://github.com/openssl/openssl/tree/openssl-3.5.9) |
| bzip2 1.0.8（Python运行时压缩库） | [许可 / License](licenses/bzip2_1_0_8_license.txt) · [官方源码 / Official source](https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz) |
| libffi 3.4.4（Python运行时外部函数接口） | [MIT及arm64来源版权 / MIT and arm64 source notices](licenses/libffi_3_4_4_license.txt) · [官方源码 / Official source](https://github.com/libffi/libffi/releases/download/v3.4.4/libffi-3.4.4.tar.gz) |
| zxcvbn 4.5.0（密码强度估计库） | [许可 / License](licenses/password_strength/zxcvbn_4_5_0_license.txt) |
| pypinyin 0.55.0（拼音处理库） | [许可 / License](licenses/password_strength/pypinyin_0_55_0_license.txt) |
| pinyin-data 0.15.0（拼音数据） | [许可 / License](licenses/password_strength/pinyin_data_0_15_license.txt) |
| phrase-pinyin-data 0.19.0（词语拼音数据） | [许可 / License](licenses/password_strength/phrase_pinyin_data_0_19_license.txt) |
| pyelftools 0.26（随附二进制解析组件） | [许可 / License](licenses/password_strength/pyelftools_license.txt) |
| pyelftools 0.26 随附 Construct（数据解析组件） | [许可 / License](licenses/password_strength/construct_bundled_pyelftools_0_26_license.txt) |
| setuptools 68.2.2（运行库随附组件） | [许可 / License](licenses/password_strength/setuptools_license.txt) |

Python 3.11的原生依赖版本由[Chaquopy 17.1.0固定构建配方](https://github.com/chaquo/chaquopy/blob/17.1.0/target/python/build.sh)确认；`libcrypto_chaquopy.so`和`libssl_chaquopy.so`是转接到同包OpenSSL 3.5.9的[兼容库](https://github.com/chaquo/chaquopy/blob/17.1.0/target/package-target.sh)，不是另一套OpenSSL版本。bzip2与libffi分别链接在`_bz2`、`_ctypes`扩展内。

同包还包含SQLite 3.53.4及链接到`_lzma`的liblzma 5.4.6。[SQLite版权说明](https://www.sqlite.org/copyright.html)及[固定版XZ许可说明](https://github.com/tukaani-project/xz/blob/v5.4.6/COPYING)将这两项运行库列为公有领域；XZ的GPL命令行脚本不随应用分发。

The pinned [Chaquopy 17.1.0 build recipe](https://github.com/chaquo/chaquopy/blob/17.1.0/target/python/build.sh) identifies the Python 3.11 native dependencies. The `libcrypto_chaquopy.so` and `libssl_chaquopy.so` files are [compatibility libraries](https://github.com/chaquo/chaquopy/blob/17.1.0/target/package-target.sh) linked to the same packaged OpenSSL 3.5.9, not another OpenSSL version. bzip2 and libffi are linked into the `_bz2` and `_ctypes` extensions.

SQLite 3.53.4 and liblzma 5.4.6, linked into `_lzma`, are also included. The [SQLite copyright statement](https://www.sqlite.org/copyright.html) and [versioned XZ licensing summary](https://github.com/tukaani-project/xz/blob/v5.4.6/COPYING) identify these runtime libraries as public domain. XZ’s GPL command-line scripts are not distributed with the app.

本目录保留第三方许可原文，不修改其条款。软件自有许可不限制第三方许可授予的权利。

Third-party license texts are retained without changing their terms. The app's own license does not restrict rights granted by these third-party licenses.
