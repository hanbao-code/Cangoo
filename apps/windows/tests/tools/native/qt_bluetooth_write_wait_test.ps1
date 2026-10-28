param(
    [Parameter(Mandatory=$true)][string]$QtSource,
    [Parameter(Mandatory=$true)][string]$QtSdk,
    [Parameter(Mandatory=$true)][string]$RuntimeDirectory,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$compiler = (Get-Command cl.exe -ErrorAction Stop).Source
$sourceText = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $QtSource).Path)
$start = $sourceText.IndexOf('static qint64 writeIOStream')
$end = $sourceText.IndexOf([char]10 + 'class SocketWorker', $start)
if ($start -lt 0 -or $end -lt 0) { throw '未找到匹配版本的 writeIOStream' }
$sdk = (Resolve-Path -LiteralPath $QtSdk).Path
$runtime = (Resolve-Path -LiteralPath $RuntimeDirectory).Path
$output = [IO.Path]::GetFullPath($OutputDirectory)
[IO.Directory]::CreateDirectory($output) | Out-Null
[IO.File]::WriteAllText((Join-Path $output 'write_io_stream.inc'), $sourceText.Substring($start, $end - $start), [Text.UTF8Encoding]::new($false))
$test = Join-Path $PSScriptRoot 'qt_bluetooth_write_wait_test.cpp'
$include = $output.Replace('\','/') + '/write_io_stream.inc'
& $compiler /nologo /std:c++17 /Zc:__cplusplus /permissive- /EHsc /MD /utf-8 /DWIN32 /DUNICODE /D_UNICODE /DQT_NO_DEBUG ('/DPDM_WRITE_IO_STREAM_SOURCE="' + $include + '"') /I"$sdk/include" /I"$sdk/include/QtCore" /I"$sdk/include/QtCore/6.9.3" /I"$sdk/include/QtCore/6.9.3/QtCore" $test /Fo"$output/test.obj" /Fe"$output/test.exe" /link /LIBPATH:"$sdk/lib" Qt6Core.lib runtimeobject.lib ole32.lib
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$previousPath = $env:PATH
try {
    $env:PATH = "$runtime;" + $env:PATH
    $testProcess = Start-Process -FilePath "$output/test.exe" -WorkingDirectory $output -WindowStyle Hidden -PassThru -RedirectStandardOutput "$output/stdout.log" -RedirectStandardError "$output/stderr.log"
    if (-not $testProcess.WaitForExit(15000)) { $testProcess.Kill(); $testProcess.WaitForExit(); throw '局部等待测试超时，测试进程已停止' }
    Get-Content -LiteralPath "$output/stdout.log" -Encoding UTF8
    if ($testProcess.ExitCode -ne 0) { Get-Content -LiteralPath "$output/stderr.log" -Encoding UTF8; exit $testProcess.ExitCode }
} finally { $env:PATH = $previousPath }
