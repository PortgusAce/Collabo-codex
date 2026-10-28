param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
try {
    $taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $taskPython)) {
        if ($PythonPath) {
            $taskBasePython = $PythonPath
        } elseif (Get-Command py.exe -ErrorAction SilentlyContinue) {
            $taskBasePython = (& py.exe -3 -c 'import sys; print(sys.executable)' | Out-String).Trim()
        } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
            $taskBasePython = (Get-Command python.exe).Source
        } else {
            throw 'Install Python 3.11 or newer from python.org, then run Install.cmd again.'
        }
        & $taskBasePython -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ is required"'
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
        & $taskBasePython -m venv (Join-Path $PSScriptRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the project Python environment.' }
    }
    & $taskPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check network/proxy settings, then retry.' }
    Write-Host 'Installed. Open Setup.cmd to choose directories and enter your Tunnel ID and runtime key.'
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
