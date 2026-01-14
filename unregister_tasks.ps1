# ============================================
# PowerShell script สำหรับลบ Scheduled Tasks ทั้งหมด
# ============================================

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Removing ZK50-ODOO Scheduled Tasks" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$tasks = @(
    "ZK50-ODOO Sync",
    "ZK50-ODOO Auto Check-In",
    "ZK50-ODOO Auto Check-Out"
)

foreach ($taskName in $tasks) {
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "  ✅ Removed: $taskName" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Not found: $taskName" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "All tasks removed!" -ForegroundColor Green
Write-Host ""
