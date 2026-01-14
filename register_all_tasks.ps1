# ============================================
# PowerShell script สำหรับลงทะเบียน Scheduled Tasks ทั้งหมด
# - ซิงค์ทุก 5 นาที
# - Auto Check-In เวลา 10:00 น.
# - Auto Check-Out เวลา 00:00 น. (เที่ยงคืน)
# ============================================

$scriptPath = $PSScriptRoot
$pythonPath = "python"
$appPath = Join-Path $scriptPath "app_secure.py"

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "ZK50-ODOO Scheduled Tasks Registration" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# ตรวจสอบว่าไฟล์ app_secure.py มีอยู่หรือไม่
if (-not (Test-Path $appPath)) {
    Write-Host "Error: app_secure.py not found at $appPath" -ForegroundColor Red
    exit 1
}

# ============================================
# Task 1: ซิงค์ทุก 5 นาที
# ============================================
$taskName1 = "ZK50-ODOO Sync"
Write-Host "Registering: $taskName1" -ForegroundColor Yellow

# ลบ task เก่าถ้ามี
$existingTask = Get-ScheduledTask -TaskName $taskName1 -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName1 -Confirm:$false
}

try {
    $action1 = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$appPath`"" -WorkingDirectory $scriptPath
    $trigger1 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 9999)
    $settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
    $principal1 = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
    
    Register-ScheduledTask -TaskName $taskName1 -Action $action1 -Trigger $trigger1 -Settings $settings1 -Principal $principal1 -Description "Sync attendance from ZKTeco every 5 minutes" | Out-Null
    Write-Host "  ✅ $taskName1 - Every 5 minutes" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Failed: $_" -ForegroundColor Red
}

# ============================================
# Task 2: Auto Check-In เวลา 10:00 น.
# ============================================
$taskName2 = "ZK50-ODOO Auto Check-In"
Write-Host "Registering: $taskName2" -ForegroundColor Yellow

$existingTask = Get-ScheduledTask -TaskName $taskName2 -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName2 -Confirm:$false
}

try {
    $action2 = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$appPath`" --auto-checkin" -WorkingDirectory $scriptPath
    $trigger2 = New-ScheduledTaskTrigger -Daily -At "10:00"
    $settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
    $principal2 = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
    
    Register-ScheduledTask -TaskName $taskName2 -Action $action2 -Trigger $trigger2 -Settings $settings2 -Principal $principal2 -Description "Auto check-in at 10:00 AM for employees without attendance" | Out-Null
    Write-Host "  ✅ $taskName2 - Daily at 10:00 AM" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Failed: $_" -ForegroundColor Red
}

# ============================================
# Task 3: Auto Check-Out เวลา 00:00 น. (เที่ยงคืน)
# ============================================
$taskName3 = "ZK50-ODOO Auto Check-Out"
Write-Host "Registering: $taskName3" -ForegroundColor Yellow

$existingTask = Get-ScheduledTask -TaskName $taskName3 -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName3 -Confirm:$false
}

try {
    $action3 = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$appPath`" --auto-checkout" -WorkingDirectory $scriptPath
    $trigger3 = New-ScheduledTaskTrigger -Daily -At "00:00"
    $settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
    $principal3 = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
    
    Register-ScheduledTask -TaskName $taskName3 -Action $action3 -Trigger $trigger3 -Settings $settings3 -Principal $principal3 -Description "Auto check-out at midnight for pending attendance" | Out-Null
    Write-Host "  ✅ $taskName3 - Daily at 00:00 (Midnight)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Failed: $_" -ForegroundColor Red
}

# ============================================
# สรุปผล
# ============================================
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "REGISTRATION COMPLETE!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "Scheduled Tasks:" -ForegroundColor White
Write-Host "  1. $taskName1    - Every 5 minutes (sync from ZKTeco)" -ForegroundColor White
Write-Host "  2. $taskName2 - Daily 10:00 AM" -ForegroundColor White
Write-Host "  3. $taskName3 - Daily 00:00 (Midnight)" -ForegroundColor White
Write-Host ""
Write-Host "Log file: $scriptPath\sync_output.log" -ForegroundColor Yellow
Write-Host ""
Write-Host "To view tasks: Open Task Scheduler (taskschd.msc)" -ForegroundColor Cyan
Write-Host "To remove all tasks: Run .\unregister_tasks.ps1" -ForegroundColor Cyan
Write-Host ""
