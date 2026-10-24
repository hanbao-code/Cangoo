# 数据库驱动构建 / Database driver build

以下构建小仓Windows版使用的 `pysqleet 31.1.3`。先按[构建说明](../docs/building.md)在仓库根创建 `.venv`、安装固定依赖，并将 `PDM_WORK_ROOT` 设置为自己选择的绝对工作目录。

已使用的工具链为Python 3.10.11 x64、Visual C++ Build Tools 2022（MSVC 14.44.35207、Windows SDK 10.0.26100.0）。在仓库根打开PowerShell，逐条执行；任何步骤失败都应停止，不继续安装不完整的产物。

```powershell
$repoRoot = (Get-Location).Path
if (-not $env:PDM_WORK_ROOT -or -not [IO.Path]::IsPathRooted($env:PDM_WORK_ROOT)) {
    throw '请先设置PDM_WORK_ROOT为自己选择的绝对工作目录'
}
$driverRoot = Join-Path $env:PDM_WORK_ROOT 'pysqleet_31_1_3'
New-Item -ItemType Directory -Path $driverRoot -ErrorAction Stop | Out-Null
$archive = Join-Path $driverRoot 'pysqleet-31.1.3.tar.gz'
Invoke-WebRequest -Uri 'https://files.pythonhosted.org/packages/c8/e4/b2271580532bb88e2c42d9f2b386f43e29675fc93269009c26240ebff9dc/pysqleet-31.1.3.tar.gz' -OutFile $archive
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne '941e14b7533eeffcfee666c12e8ecf6e4b72317daafe3d0e788dc8540c8a277a') {
    throw '驱动源码摘要不匹配'
}
tar -xf $archive -C $driverRoot
if ($LASTEXITCODE -ne 0) { throw '源码解包失败' }
Push-Location "$driverRoot/pysqleet-31.1.3"
try {
    git -c core.autocrlf=false apply --unidiff-zero "$repoRoot/apps/windows/packaging/windows/pysqleet_31_1_3.patch"
    if ($LASTEXITCODE -ne 0) { throw '驱动补丁应用失败' }
    & "$repoRoot/.venv/Scripts/python.exe" -B setup.py bdist_wheel
    if ($LASTEXITCODE -ne 0) { throw '驱动构建失败' }
} finally { Pop-Location }
& "$repoRoot/.venv/Scripts/python.exe" -m pip install --no-deps --no-index "$driverRoot/pysqleet-31.1.3/dist/pysqleet-31.1.3-cp310-cp310-win_amd64.whl"
```

使用新的驱动源码目录，不向同一源码重复应用补丁。补丁只调整Python 3.10/MSVC构建兼容，不修改sqleet/SQLite实现。不同工具链生成的二进制不保证逐字节相同；修改或替换驱动后先用测试数据库验证读写、备份和改密。库替换说明见[第三方来源与库替换](../docs/third_party_sources.md)。

## English

This builds `pysqleet 31.1.3` for Cangoo on Windows. First follow [Building from source](../docs/building.md#english) to create the root `.venv`, install the pinned dependencies and set `PDM_WORK_ROOT` to an absolute work directory of your choice.

The build has used Python 3.10.11 x64 and Visual C++ Build Tools 2022, with MSVC 14.44.35207 and Windows SDK 10.0.26100.0. Run the PowerShell commands above from the repository root. Stop on any failure. Use a fresh driver source directory and never apply the patch twice.

The patch only adjusts Python 3.10/MSVC build compatibility; sqleet/SQLite is unchanged. Different toolchains are not guaranteed to produce identical bytes. Before adopting a modified driver, verify reading, writing, backups and password changes with test databases. See [library replacement](../docs/third_party_sources.md).
