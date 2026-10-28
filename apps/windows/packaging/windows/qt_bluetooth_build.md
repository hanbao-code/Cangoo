# QtBluetooth 构建与来源

小仓于2026年10月27日修改 QtConnectivity 6.9.3 的
`src/bluetooth/qbluetoothsocket_winrt.cpp`：Windows 蓝牙写入改为等待完成事件，
随后仍由原 Qt 逻辑读取结果和处理错误。完整改动见同目录
`qt_bluetooth_6_9_3.patch`，来源、工具版本和摘要见 `qt_bluetooth_lock.json`。
QtCore、QtNetwork 和 PySide 绑定保持上游运行库。

上游版权和许可原文保存在随附源码归档的文件头及 `LICENSES/` 中；补丁不替换这些声明。
库保持独立动态链接。构建时的固定摘要用于核对随版本提供的构建材料，应用运行时不锁定第三方库字节，
不限制相应许可授予的修改、替换和调试权利。

## 准备冻结构建

在项目根（双平台仓库根或独立Windows源码根）的 `build_support/qt_bluetooth/6_9_3/` 放入：

- 与锁文件对应的 `Qt6Bluetooth.dll`，摘要须与锁文件一致。
- 官方 `qtconnectivity-everywhere-src-6.9.3.tar.xz`，摘要须与锁文件一致。

从完整解压的Windows便携包取得对应DLL：`Cangoo/_internal/PySide6/Qt6Bluetooth.dll`；
对应源码归档位于 `Cangoo/_internal/third_party/qt_bluetooth/`。复制到上述 `build_support` 后核对锁文件摘要。

现有 `cangoo.spec` 自动核对材料、替换收集到的 QtBluetooth，并把源码归档、补丁、
锁文件和本说明放入 `_internal/third_party/qt_bluetooth/`。MSI、Inno 和便携包沿用
同一份冻结结果；安装清单和包摘要覆盖这些材料。缺失、版本不匹配或摘要变化时停止构建。
不修改 `.venv`，不自动下载或安装库。

## 从源码重建

使用锁文件所列官方 QtBase MSVC 2022 x64 开发包及 QtConnectivity 源码，先核对 SHA-256。
将开发包解到一个新英文路径下的 `sdk/`，源码解到同级 `src/`，保留上游许可。
在配置好 x64 MSVC、CMake、Ninja 和 Windows SDK 的 PowerShell 中执行：

```powershell
$qtBuild = 'D:/qt_bluetooth_build'
# 双平台仓库使用 <仓库>/apps/windows；独立Windows源码使用其根目录。
$windowsRoot = '<Windows工程或独立源码根目录>'
$patchFile = "$windowsRoot/packaging/windows/qt_bluetooth_6_9_3.patch"
git -C "$qtBuild/src" -c core.autocrlf=false apply --check $patchFile
if ($LASTEXITCODE -ne 0) { throw '补丁检查失败' }
git -C "$qtBuild/src" -c core.autocrlf=false apply $patchFile
if ($LASTEXITCODE -ne 0) { throw '补丁应用失败' }
cmake -S "$qtBuild/src" -B "$qtBuild/build" -G Ninja `
  "-DCMAKE_PREFIX_PATH=$qtBuild/sdk" "-DCMAKE_INSTALL_PREFIX=$qtBuild/install" `
  -DCMAKE_BUILD_TYPE=Release -DBUILD_WITH_PCH=OFF -DBUILD_TESTING=OFF `
  -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF -DQT_BUILD_BENCHMARKS=OFF -DFEATURE_nfc=OFF
if ($LASTEXITCODE -ne 0) { throw 'Qt配置失败' }
cmake --build "$qtBuild/build" --target Bluetooth
if ($LASTEXITCODE -ne 0) { throw 'Qt构建失败' }
```

若 CMake 找不到 `rc.exe` 或 `mt.exe`，通过 `CMAKE_RC_COMPILER`、`CMAKE_MT` 指定
Windows SDK 中的绝对路径，使用正斜线。构建结果为 `build/bin/Qt6Bluetooth.dll`。
补丁后的源码摘要应与锁文件一致。输出 DLL 会受工具和构建路径影响，不能承诺字节可重现；
重新构建的不同字节须重新核验接口、加载及受影响行为，确认兼容后再更新本地构建锁文件，不要仅为通过构建而替换摘要。

此补丁配合PySide6 6.9.3随附的QtCore／QtNetwork使用。
在 Windows 工程或独立源码根运行以下专项检查；输出目录须在仓库外：

```powershell
./tests/tools/native/qt_bluetooth_write_wait_test.ps1 `
  -QtSource "$qtBuild/src/src/bluetooth/qbluetoothsocket_winrt.cpp" `
  -QtSdk "$qtBuild/sdk" `
  -RuntimeDirectory '<解压后的Cangoo目录>/_internal/PySide6' `
  -OutputDirectory "$qtBuild/check"
```

该检查覆盖写等待及错误路径；替换运行库后，还应使用测试资料验证实际蓝牙传输。
