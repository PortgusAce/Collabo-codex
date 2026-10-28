param([string]$AnchorThreadId, [switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Security
$taskBase = $PSScriptRoot
$taskPython = Join-Path $taskBase '.venv/Scripts/python.exe'
$taskManage = Join-Path $taskBase 'tools/manage.py'
$taskRuntime = Join-Path $taskBase '.runtime'
New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
$taskFilesPath = Join-Path $taskRuntime 'files.json'
$taskTunnelPath = Join-Path $taskRuntime 'tunnel.json'
$taskKeyPath = Join-Path $taskRuntime 'runtime-key.dpapi'
$taskUtf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $taskUtf8

function Read-TaskJson([string]$Path) {
    if (Test-Path -LiteralPath $Path) { return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    return $null
}
function Write-TaskJson([string]$Path, $Value) {
    $taskTemp = $Path + '.tmp'
    [IO.File]::WriteAllText($taskTemp, ($Value | ConvertTo-Json -Depth 6), $taskUtf8)
    Move-Item -LiteralPath $taskTemp -Destination $Path -Force
}
function Invoke-TaskManager([string[]]$ManagerArgs) {
    if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run Install.cmd first to create the Python environment.' }
    $taskOutput = & $taskPython $taskManage @ManagerArgs 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw $taskOutput.Trim() }
    return $taskOutput.Trim()
}
function Show-TaskError([string]$Text) {
    [Windows.Forms.MessageBox]::Show($Text, 'Collabo-codex', 'OK', 'Error') | Out-Null
}

$taskForm = New-Object Windows.Forms.Form
$taskForm.Text = 'Collabo-codex setup'
$taskIconPath = Join-Path $taskBase 'assets/icon.ico'
if (Test-Path -LiteralPath $taskIconPath) { $taskForm.Icon = New-Object Drawing.Icon($taskIconPath) }
$taskForm.ClientSize = New-Object Drawing.Size(720, 530)
$taskForm.StartPosition = 'CenterScreen'
$taskForm.FormBorderStyle = 'FixedDialog'
$taskForm.MaximizeBox = $false
function Add-TaskLabel([string]$Text, [int]$X, [int]$Y, [int]$Width = 650) {
    $taskLabel = New-Object Windows.Forms.Label
    $taskLabel.Text = $Text; $taskLabel.Location = New-Object Drawing.Point($X,$Y)
    $taskLabel.Size = New-Object Drawing.Size($Width,22); $taskForm.Controls.Add($taskLabel)
}
function Add-TaskBox([int]$Y) {
    $taskBox = New-Object Windows.Forms.TextBox
    $taskBox.Location = New-Object Drawing.Point(150,$Y); $taskBox.Width = 548
    $taskForm.Controls.Add($taskBox); return $taskBox
}
Add-TaskLabel 'One-time account setup: create a Tunnel + runtime key, then enter them here.' 18 15
Add-TaskLabel 'Tunnel ID' 18 55 125
$taskTunnelBox = Add-TaskBox 52
Add-TaskLabel 'Runtime API key' 18 90 125
$taskKeyBox = Add-TaskBox 87; $taskKeyBox.UseSystemPasswordChar = $true
Add-TaskLabel 'Proxy (optional)' 18 125 125
$taskProxyBox = Add-TaskBox 122
Add-TaskLabel 'Allowed file-reading directories (includes subfolders; empty means no file access)' 18 165
$taskRoots = New-Object Windows.Forms.ListBox
$taskRoots.Location = New-Object Drawing.Point(18,194)
$taskRoots.Size = New-Object Drawing.Size(570,180)
$taskForm.Controls.Add($taskRoots)
$taskAdd = New-Object Windows.Forms.Button
$taskAdd.Text = 'Add folder'; $taskAdd.Location = New-Object Drawing.Point(600,194)
$taskAdd.Size = New-Object Drawing.Size(98,32)
$taskAdd.Add_Click({
    $taskPicker = New-Object Windows.Forms.FolderBrowserDialog
    $taskPicker.Description = 'Allow file reading in this directory and its subfolders'
    try {
        if ($taskPicker.ShowDialog() -eq 'OK' -and -not $taskRoots.Items.Contains($taskPicker.SelectedPath)) {
            $taskRoots.Items.Add($taskPicker.SelectedPath) | Out-Null
        }
    } finally { $taskPicker.Dispose() }
})
$taskForm.Controls.Add($taskAdd)
$taskRemove = New-Object Windows.Forms.Button
$taskRemove.Text = 'Remove'; $taskRemove.Location = New-Object Drawing.Point(600,236)
$taskRemove.Size = New-Object Drawing.Size(98,32)
$taskRemove.Add_Click({ if ($taskRoots.SelectedIndex -ge 0) { $taskRoots.Items.RemoveAt($taskRoots.SelectedIndex) } })
$taskForm.Controls.Add($taskRemove)
Add-TaskLabel 'Blank key keeps the saved key. Keys use Windows user encryption; never paste them into chat.' 18 385
Add-TaskLabel 'Task/project execution has its own desktop permissions, separate from file-reading directories.' 18 411
$taskStatus = New-Object Windows.Forms.Label
$taskStatus.Location = New-Object Drawing.Point(18,440); $taskStatus.Size = New-Object Drawing.Size(680,24)
$taskStatus.Text = 'Save directories alone, or save credentials and connect.'
$taskForm.Controls.Add($taskStatus)
$taskSavedFiles = Read-TaskJson $taskFilesPath
if ($taskSavedFiles) { foreach ($taskRoot in $taskSavedFiles.roots) { $taskRoots.Items.Add([string]$taskRoot) | Out-Null } }
$taskSavedTunnel = Read-TaskJson $taskTunnelPath
if ($taskSavedTunnel) { $taskTunnelBox.Text = $taskSavedTunnel.tunnel_id; $taskProxyBox.Text = $taskSavedTunnel.proxy }

function Save-TaskSettings {
    $taskPaths = @()
    foreach ($taskRoot in $taskRoots.Items) {
        if ($taskRoot.StartsWith('\\') -or -not [IO.Path]::IsPathRooted($taskRoot) -or -not (Test-Path -LiteralPath $taskRoot -PathType Container)) {
            throw 'Choose existing local directories using Add folder.'
        }
        $taskPaths += (Get-Item -LiteralPath $taskRoot).FullName
    }
    $taskTunnelId = $taskTunnelBox.Text.Trim()
    if ($taskTunnelId -and $taskTunnelId -notmatch '^tunnel_(?:[a-z0-9]{4}_)?[a-z0-9]{32}$') { throw 'Enter a valid Tunnel ID.' }
    $taskProxy = $taskProxyBox.Text.Trim()
    if ($taskProxy) {
        $taskUri = [Uri]$taskProxy
        if ($taskUri.Scheme -notin @('http','https') -or -not $taskUri.Host -or $taskUri.Port -le 0) { throw 'Proxy must be an HTTP(S) URL including its port.' }
    }
    Write-TaskJson $taskFilesPath @{ roots = @($taskPaths); max_file_mb = 64; conversion_timeout_seconds = 45 }
    Write-TaskJson $taskTunnelPath @{ tunnel_id = $taskTunnelId; proxy = $taskProxy }
    if ($taskKeyBox.Text.Trim()) {
        $taskBytes = [Text.Encoding]::UTF8.GetBytes($taskKeyBox.Text.Trim())
        try {
            $taskEncrypted = [Security.Cryptography.ProtectedData]::Protect($taskBytes,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
            [IO.File]::WriteAllText($taskKeyPath,[Convert]::ToBase64String($taskEncrypted),$taskUtf8)
        } finally { [Array]::Clear($taskBytes,0,$taskBytes.Length); $taskKeyBox.Clear() }
    }
}
$taskSave = New-Object Windows.Forms.Button
$taskSave.Text = 'Save settings'; $taskSave.Location = New-Object Drawing.Point(330,478)
$taskSave.Size = New-Object Drawing.Size(160,34)
$taskSave.Add_Click({ try { Save-TaskSettings; $taskStatus.Text = 'Saved. File-reading permissions apply on the next tool call.' } catch { Show-TaskError $_.Exception.Message } })
$taskForm.Controls.Add($taskSave)
$taskConnect = New-Object Windows.Forms.Button
$taskConnect.Text = 'Save and connect'; $taskConnect.Location = New-Object Drawing.Point(505,478)
$taskConnect.Size = New-Object Drawing.Size(193,34)
$taskConnect.Add_Click({
    try {
        Save-TaskSettings
        if (-not (Test-Path -LiteralPath $taskKeyPath)) { throw 'Enter a runtime API key first.' }
        $taskForm.UseWaitCursor = $true; $taskConnect.Enabled = $false; $taskSave.Enabled = $false
        $taskStatus.Text = 'Installing/checking the official tunnel client, then connecting...'; [Windows.Forms.Application]::DoEvents()
        if (-not (Test-Path -LiteralPath (Join-Path $taskRuntime 'tunnel-install.json'))) {
            $taskInstallArgs = @('install-tunnel')
            if ($taskProxyBox.Text.Trim()) { $taskInstallArgs += @('--proxy',$taskProxyBox.Text.Trim()) }
            Invoke-TaskManager -ManagerArgs $taskInstallArgs | Out-Null
        }
        $taskConnected = Invoke-TaskManager -ManagerArgs @('connect') | ConvertFrom-Json
        $taskStatus.Text = 'Tunnel is locally ready. Add it as a custom MCP plugin in ChatGPT and test a tool call.'
        [Windows.Forms.MessageBox]::Show('Local tunnel ready. Next: ChatGPT Plugins > Add custom MCP server > Tunnel. Use your Tunnel ID and No authentication.','Collabo-codex') | Out-Null
    } catch { Show-TaskError $_.Exception.Message }
    finally { $taskForm.UseWaitCursor = $false; $taskConnect.Enabled = $true; $taskSave.Enabled = $true }
})
$taskForm.Controls.Add($taskConnect)
if ($AnchorThreadId -and $env:CODEX_APP_TOOLS_PIPE_PATH -and (Test-Path -LiteralPath $taskPython)) {
    try { Invoke-TaskManager -ManagerArgs @('bind-desktop','--anchor-thread-id',$AnchorThreadId) | Out-Null }
    catch { $taskStatus.Text = 'Desktop binding failed; see docs/desktop-bridge.md. File tools are still usable.' }
}
try {
    if ($ValidateOnly) {
        @{ controls = $taskForm.Controls.Count; key_is_masked = $taskKeyBox.UseSystemPasswordChar; default_roots = $taskRoots.Items.Count } | ConvertTo-Json -Compress
    } else { $taskForm.ShowDialog() | Out-Null }
}
finally { $taskKeyBox.Clear(); $taskForm.Dispose() }
