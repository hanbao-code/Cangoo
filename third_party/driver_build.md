# 数据库驱动构建 / Database driver build

在此目录中新建虚拟环境，使用Python3.10.11 x64、Visual C++ Build Tools 2022（MSVC14.44.35207、Windows SDK10.0.26100.0）。以下仅构建第三方驱动；版本清单兼含原产品的构建依赖，不是产品源码。

Use Python 3.10.11 x64 and Visual C++ Build Tools 2022 (MSVC 14.44.35207, Windows SDK 10.0.26100.0). Run the commands in this directory. They build the third-party driver only; the version list also contains the original product's build dependencies.

```powershell
py -3.10 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
$repoRoot = (Get-Location).Path
$env:PDM_WORK_ROOT = Join-Path $env:LOCALAPPDATA 'cangoo_build'
$driverRoot = Join-Path $env:PDM_WORK_ROOT 'pysqleet_31_1_3'
New-Item -ItemType Directory -Path $driverRoot | Out-Null
$archive = Join-Path $driverRoot 'pysqleet-31.1.3.tar.gz'
Invoke-WebRequest -Uri 'https://files.pythonhosted.org/packages/c8/e4/b2271580532bb88e2c42d9f2b386f43e29675fc93269009c26240ebff9dc/pysqleet-31.1.3.tar.gz' -OutFile $archive
if ((Get-FileHash $archive -Algorithm SHA256).Hash -ne '941e14b7533eeffcfee666c12e8ecf6e4b72317daafe3d0e788dc8540c8a277a') {
    throw '驱动源码摘要不匹配'
}
tar -xf $archive -C $driverRoot
if ($LASTEXITCODE -ne 0) { throw '源码解包失败' }
Push-Location "$driverRoot/pysqleet-31.1.3"
try {
    git -c core.autocrlf=false apply --unidiff-zero "$repoRoot/pysqleet_31_1_3.patch"
    if ($LASTEXITCODE -ne 0) { throw '驱动补丁应用失败' }
    & "$repoRoot/.venv/Scripts/python.exe" -B setup.py bdist_wheel
    if ($LASTEXITCODE -ne 0) { throw '驱动构建失败' }
} finally { Pop-Location }
.venv/Scripts/python.exe -m pip install --no-deps --no-index "$driverRoot/pysqleet-31.1.3/dist/pysqleet-31.1.3-cp310-cp310-win_amd64.whl"
```

使用新的驱动源码目录，不向同一源码重复应用补丁。补丁只调整Python3.10/MSVC构建兼容，不修改sqleet/SQLite实现。替换步骤见[第三方来源与库替换](../docs/third_party_sources.md)。

Use a fresh source directory and do not apply the patch twice. The patch only adjusts Python 3.10/MSVC build compatibility; sqleet/SQLite is unchanged. See [library replacement](../docs/third_party_sources.md).
