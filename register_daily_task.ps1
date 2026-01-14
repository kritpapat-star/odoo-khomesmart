# ===========================================================================
# PowerShell Script: Register Windows Scheduled Task
# For syncing ZKTeco -> Odoo daily at 19:00
# ===========================================================================

$TaskName = "ZK50-ODOO Daily Sync"
$TaskDescription = "Sync attendance data from ZKTeco to Odoo daily at 19:00."

# Define batch file path
$ScriptPath = "C:\Users\NEW\Desktop\ZK50-ODOO\run_sync.bat"
$WorkingDirectory = "C:\Users\NEW\Desktop\ZK50-ODOO"

# Check if file exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "Error: File $ScriptPath not found." -ForegroundColor Red
    exit 1
}

Write-Host "Creating Scheduled Task: $TaskName" -ForegroundColor Cyan
Write-Host "Schedule: Daily at 19:00" -ForegroundColor Yellow

# Create Action
$Action = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory $WorkingDirectory

# Create Trigger (Daily at 19:00)
$Trigger = New-ScheduledTaskTrigger -Daily -At "19:00"

# Create Settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Create Principal
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

# Remove existing task if any
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Register new task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Description $TaskDescription `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal

Write-Host ""
Write-Host "SUCCESS: Scheduled Task created!" -ForegroundColor Green
Write-Host ""
Write-Host "Details:" -ForegroundColor Cyan
Write-Host "  Task Name    : $TaskName"
Write-Host "  Schedule     : Daily at 19:00"
Write-Host "  Script       : $ScriptPath"
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  View Task    : Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Run Now      : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Remove Task  : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host ""
