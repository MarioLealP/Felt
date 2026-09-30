Write-Host "Stopping running Felt instances..."
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "felt_animation" -or $_.CommandLine -match "felt-tray" -or $_.CommandLine -match "felt_tray" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Stop-Process -Name "FeltOverlay" -ErrorAction SilentlyContinue
# The overlay can also run as the stock Godot.exe with --main-pack FeltOverlay.pck
# (Smart App Control blocks the exported exe) - stop only that one, never an editor.
Get-WmiObject Win32_Process -Filter "Name='Godot.exe'" | Where-Object { $_.CommandLine -match "FeltOverlay.pck" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

Write-Host "Starting Felt Animation (also launches the overlay)..."
Set-Location -Path "E:\Felt\felt-animation"
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m felt_animation" -WindowStyle Hidden

# felt-tray starts through the venv's signed python.exe, not the uv-generated
# .exe launcher: Smart App Control blocks those whenever a re-sync
# regenerates them with a new hash (2026-09-26, felt-tray couldn't be
# restarted). felt-animation above already starts this way.
Write-Host "Starting Felt Tray..."
Set-Location -Path "E:\Felt\felt-tray"
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m felt_tray" -WindowStyle Hidden

Write-Host "Felt successfully launched in the background!"
Start-Sleep -Seconds 2
