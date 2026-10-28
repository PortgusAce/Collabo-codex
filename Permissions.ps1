param([switch]$ValidateOnly, [switch]$SelfTest, [string]$PreviewPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$taskUtf8 = New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding = $taskUtf8
if ($SelfTest) {
    $taskRuntime = Join-Path $PSScriptRoot 'test-output/permissions-selftest'
} else {
    $taskRuntime = Join-Path $PSScriptRoot '.runtime'
}
New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
$taskFilesPath = Join-Path $taskRuntime 'files.json'
$taskChoicesPath = Join-Path $taskRuntime 'directories-ui.json'
$script:taskLoading = $true

function Read-DirectoryJson([string]$Path) {
    if (Test-Path -LiteralPath $Path) { return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    return $null
}
function Write-DirectoryJson([string]$Path, $Value) {
    $taskTemp = $Path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    try {
        [IO.File]::WriteAllText($taskTemp, ($Value | ConvertTo-Json -Depth 6), $taskUtf8)
        Move-Item -LiteralPath $taskTemp -Destination $Path -Force
    } finally { if (Test-Path -LiteralPath $taskTemp) { Remove-Item -LiteralPath $taskTemp } }
}

$taskForm = New-Object Windows.Forms.Form
$taskForm.Text = 'Collabo-codex · 目录读取权限'
$taskForm.ClientSize = New-Object Drawing.Size(760,470)
$taskForm.StartPosition = 'CenterScreen'
$taskForm.FormBorderStyle = 'FixedDialog'
$taskForm.MaximizeBox = $false
$taskForm.Icon = New-Object Drawing.Icon((Join-Path $PSScriptRoot 'assets/icon.ico'))
$taskForm.Font = New-Object Drawing.Font('Microsoft YaHei UI',10)
$taskHeader = New-Object Windows.Forms.Label
$taskHeader.Text = '勾选即授权，取消勾选即撤销；每次操作立即保存。'
$taskHeader.Location = New-Object Drawing.Point(18,15)
$taskHeader.Size = New-Object Drawing.Size(724,25)
$taskForm.Controls.Add($taskHeader)
$taskHelp = New-Object Windows.Forms.Label
$taskHelp.Text = '包括子目录。若父目录仍被授权，取消子目录不会阻止通过父目录读取。'
$taskHelp.Location = New-Object Drawing.Point(18,44)
$taskHelp.Size = New-Object Drawing.Size(724,25)
$taskForm.Controls.Add($taskHelp)
$taskList = New-Object Windows.Forms.CheckedListBox
$taskList.Location = New-Object Drawing.Point(18,120)
$taskList.Size = New-Object Drawing.Size(724,255)
$taskList.CheckOnClick = $true
$taskList.HorizontalScrollbar = $true
$taskForm.Controls.Add($taskList)
$taskStatus = New-Object Windows.Forms.Label
$taskStatus.Location = New-Object Drawing.Point(18,390)
$taskStatus.Size = New-Object Drawing.Size(724,55)
$taskForm.Controls.Add($taskStatus)

function Save-DirectorySelection([int]$ChangedIndex = -1, $NewState = 'Unchecked') {
    $taskActive = @()
    foreach ($taskIndex in 0..($taskList.Items.Count-1)) {
        if ($taskIndex -lt 0 -or $taskIndex -ge $taskList.Items.Count) { continue }
        $taskChecked = $taskList.GetItemChecked($taskIndex)
        if ($taskIndex -eq $ChangedIndex) { $taskChecked = ([string]$NewState -eq 'Checked') }
        if ($taskChecked) { $taskActive += [string]$taskList.Items[$taskIndex] }
    }
    $taskConfig = Read-DirectoryJson $taskFilesPath
    if (-not $taskConfig) { $taskConfig = [pscustomobject]@{ roots=@(); max_file_mb=64; conversion_timeout_seconds=45 } }
    $taskConfig.roots = @($taskActive)
    Write-DirectoryJson $taskChoicesPath @{ directories = @($taskList.Items | ForEach-Object { [string]$_ }) }
    Write-DirectoryJson $taskFilesPath $taskConfig
    $taskStatus.Text = "已保存：允许读取 $($taskActive.Count) 个目录。下一次工具调用即生效，无需重连或刷新插件。"
}
function Load-DirectorySelection {
    $script:taskLoading = $true
    try {
        $taskConfig = Read-DirectoryJson $taskFilesPath
        try { $taskChoices = Read-DirectoryJson $taskChoicesPath } catch { $taskChoices = $null }
        $taskList.Items.Clear()
        $taskActive = @($taskConfig.roots | Where-Object { $_ })
        foreach ($taskPath in @($taskActive + @($taskChoices.directories)) | Where-Object { $_ } | Select-Object -Unique) {
            $taskList.Items.Add([string]$taskPath, ($taskPath -in $taskActive)) | Out-Null
        }
        $taskStatus.Text = "当前允许读取 $($taskActive.Count) 个目录。无需填写 Tunnel 或密钥。"
    } finally { $script:taskLoading = $false }
}
function Show-DirectoryError($ErrorRecord) {
    if ($SelfTest) { throw $ErrorRecord }
    [Windows.Forms.MessageBox]::Show($ErrorRecord.Exception.Message,'Collabo-codex','OK','Error') | Out-Null
}
function Import-DirectoryProjects($Projects) {
    $script:taskLoading = $true
    try {
        foreach ($taskProject in $Projects) {
            $taskPath = [string]$taskProject.path
            if ($taskPath -and -not $taskPath.StartsWith('\\') -and [IO.Path]::IsPathRooted($taskPath) -and (Test-Path -LiteralPath $taskPath -PathType Container)) {
                $taskIndex = $taskList.Items.IndexOf($taskPath)
                if ($taskIndex -lt 0) { $taskList.Items.Add($taskPath,$true) | Out-Null }
                else { $taskList.SetItemChecked($taskIndex,$true) }
            }
        }
    } finally { $script:taskLoading = $false }
    Save-DirectorySelection
}
$taskList.Add_ItemCheck({ param($sender,$event)
    if ($script:taskLoading) { return }
    try { Save-DirectorySelection $event.Index $event.NewValue }
    catch { $event.NewValue = $event.CurrentValue; Show-DirectoryError $_ }
})
function Add-DirectoryButton([string]$Text, [int]$X, [int]$Width, [scriptblock]$Action) {
    $taskButton = New-Object Windows.Forms.Button
    $taskButton.Text = $Text
    $taskButton.Location = New-Object Drawing.Point($X,80)
    $taskButton.Size = New-Object Drawing.Size($Width,32)
    $taskButton.Add_Click($Action)
    $taskForm.Controls.Add($taskButton)
}
Add-DirectoryButton '添加目录' 18 112 {
    $taskPicker = New-Object Windows.Forms.FolderBrowserDialog
    try {
        if ($taskPicker.ShowDialog() -eq 'OK') {
            $taskIndex = $taskList.Items.IndexOf($taskPicker.SelectedPath)
            if ($taskIndex -lt 0) { $taskList.Items.Add($taskPicker.SelectedPath,$true) | Out-Null }
            else { $taskList.SetItemChecked($taskIndex,$true) }
        }
    } catch { Show-DirectoryError $_ } finally { $taskPicker.Dispose() }
}
Add-DirectoryButton '导入本地项目' 140 164 {
    try {
        $taskForm.UseWaitCursor = $true
        $taskStatus.Text = '正在读取桌面已保存的本地项目…'
        [Windows.Forms.Application]::DoEvents()
        $taskOutput = & (Join-Path $PSScriptRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'tools/manage.py') list-local-projects 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { throw '无法读取本地项目。请保持桌面打开，并按 docs/desktop-bridge.md 重新绑定。' }
        $taskProjects = ($taskOutput | ConvertFrom-Json).projects
        Import-DirectoryProjects $taskProjects
    } catch { Load-DirectorySelection; Show-DirectoryError $_ }
    finally { $script:taskLoading = $false; $taskForm.UseWaitCursor = $false }
}
Add-DirectoryButton '移除所选项' 314 142 {
    try { if ($taskList.SelectedIndex -ge 0) { $taskList.Items.RemoveAt($taskList.SelectedIndex); Save-DirectorySelection } }
    catch { Load-DirectorySelection; Show-DirectoryError $_ }
}
Add-DirectoryButton '全部取消授权' 466 154 {
    try {
        $script:taskLoading = $true
        for ($taskIndex=0; $taskIndex -lt $taskList.Items.Count; $taskIndex++) { $taskList.SetItemChecked($taskIndex,$false) }
        $script:taskLoading = $false
        Save-DirectorySelection
    } catch { Load-DirectorySelection; Show-DirectoryError $_ }
    finally { $script:taskLoading = $false }
}
Add-DirectoryButton '重新加载' 630 112 { try { Load-DirectorySelection } catch { Show-DirectoryError $_ } }

try {
    Load-DirectorySelection
    if ($SelfTest) {
        $taskList.Items.Clear()
        $taskSample = Join-Path $taskRuntime 'sample'
        New-Item -ItemType Directory -Path $taskSample -Force | Out-Null
        Write-DirectoryJson $taskFilesPath @{ roots=@(); max_file_mb=23; conversion_timeout_seconds=17 }
        $taskList.Items.Add($taskSample,$true) | Out-Null
        if ((Read-DirectoryJson $taskFilesPath).roots.Count -ne 1) { throw 'Checkbox grant failed' }
        $taskList.SetItemChecked(0,$false)
        if ((Read-DirectoryJson $taskFilesPath).roots.Count -ne 0) { throw 'Checkbox revocation failed' }
        Load-DirectorySelection
        if ($taskList.Items.Count -ne 1 -or $taskList.GetItemChecked(0)) { throw 'Unchecked directory was not remembered' }
        $taskList.SetItemChecked(0,$true)
        if ((Read-DirectoryJson $taskFilesPath).max_file_mb -ne 23) { throw 'Custom file limits changed' }
        $taskProjectFolder = Join-Path $taskRuntime '项目二'
        New-Item -ItemType Directory -Path $taskProjectFolder -Force | Out-Null
        Import-DirectoryProjects @(@{path=$taskSample},@{path=$taskProjectFolder},@{path=$taskProjectFolder},@{path='https://example.com'},@{path='\\server\share'})
        if ((Read-DirectoryJson $taskFilesPath).roots.Count -ne 2) { throw 'Project import or deduplication failed' }
        $taskList.Items.Clear(); Save-DirectorySelection
        if ((Read-DirectoryJson $taskFilesPath).roots.Count -ne 0) { throw 'Removing all directories failed' }
        @{ checkbox_grant=$true; checkbox_revoke=$true; remembers_unchecked=$true; preserves_limits=$true; project_import=$true } | ConvertTo-Json -Compress
    } elseif ($ValidateOnly) {
        @{ controls=$taskForm.Controls.Count; directories=$taskList.Items.Count; icon_loaded=($null -ne $taskForm.Icon) } | ConvertTo-Json -Compress
    } elseif ($PreviewPath) {
        $taskForm.Show(); $taskForm.Refresh()
        $taskBitmap = New-Object Drawing.Bitmap($taskForm.Width,$taskForm.Height)
        try { $taskForm.DrawToBitmap($taskBitmap,(New-Object Drawing.Rectangle(0,0,$taskForm.Width,$taskForm.Height))); $taskBitmap.Save($PreviewPath) }
        finally { $taskBitmap.Dispose() }
    } else { $taskForm.ShowDialog() | Out-Null }
} finally { $taskForm.Dispose() }
