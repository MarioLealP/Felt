$GodotPathFile = "E:\Felt\godot_path.txt"
$GodotExe = ""
if (Test-Path $GodotPathFile) {
    $GodotExe = Get-Content $GodotPathFile
}

if (-not (Test-Path $GodotExe)) {
    Add-Type -AssemblyName System.Windows.Forms
    $FileBrowser = New-Object System.Windows.Forms.OpenFileDialog
    $FileBrowser.Title = "Please select your Godot Engine executable (Godot_v4*.exe)"
    $FileBrowser.Filter = "Godot Executable|Godot_v4*.exe;godot.exe"
    $result = $FileBrowser.ShowDialog()
    if ($result -eq 'OK') {
        $GodotExe = $FileBrowser.FileName
        Set-Content -Path $GodotPathFile -Value $GodotExe
    } else {
        Write-Host "Update cancelled (no Godot executable selected)."
        Start-Sleep -Seconds 3
        exit
    }
}

Write-Host "Stopping running instances..."
Stop-Process -Name "FeltOverlay" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Commit whatever Mario has dropped into the asset folders (new .vrma
# clips, a swapped felt.vrm) before rebuilding, so every export corresponds
# to a real git snapshot - cheap, reversible, and means "manage stuff from
# E:\Felt" actually has a backup/history behind it, not just loose files.
Write-Host "Checking for new/changed assets..."
Set-Location -Path "E:\Felt\felt-character-assets"
git add -A
$staged = git diff --cached --name-only
if ($staged) {
    Write-Host "  Committing asset changes:"
    $staged | ForEach-Object { Write-Host "    $_" }
    git commit -m "Update Felt assets" | Out-Null
    git push
} else {
    Write-Host "  Nothing new."
}

Write-Host "Exporting Godot project..."
Set-Location -Path "E:\Felt\felt-character-assets\felt-godot-overlay"
$process = Start-Process -FilePath $GodotExe -ArgumentList "--headless --export-release `"Windows Desktop`" build/windows/FeltOverlay.exe" -Wait -NoNewWindow -PassThru

if ($process.ExitCode -eq 0) {
    Write-Host "Godot export successful!"
} else {
    Write-Host "Export failed with exit code $($process.ExitCode). Check errors above."
    pause
    exit
}

# Required, not optional - patch-clickthrough.ps1 isn't packed into the
# export (Godot doesn't include loose non-resource files by default), so
# main.gd looks for it as a real sibling of the .exe. Without it,
# click-through never applies and the overlay sits always-on-top,
# blocking every click on the real desktop until killed - a real incident
# that happened during development (2026-09-21).
Copy-Item "patch-clickthrough.ps1" "build\windows\patch-clickthrough.ps1" -Force

Write-Host "Restarting Felt Animation..."
Set-Location -Path "E:\Felt\felt-animation"
# Kill python processes running felt-animation (to be safe)
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "felt_animation" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 1
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m felt_animation" -WindowStyle Hidden

Write-Host "Update and Restart complete!"
Start-Sleep -Seconds 2
