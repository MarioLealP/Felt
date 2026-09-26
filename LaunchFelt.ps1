Write-Host "Checking local Ollama (felt-animation's reaction picker)..."
$ollamaUp = $false
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    if ($resp.StatusCode -eq 200) { $ollamaUp = $true }
} catch {}

if (-not $ollamaUp) {
    Write-Host "  Not running - starting it (headless, no tray icon)..."
    Start-ScheduledTask -TaskName "OllamaServe"
    # Give it a few seconds, but don't block the rest of the launch on it -
    # felt-animation falls back gracefully (no reaction classification,
    # just plain replies) if Ollama isn't up yet by the time it's needed.
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) { $ollamaUp = $true; break }
        } catch {}
    }
    if ($ollamaUp) { Write-Host "  Ollama is up." } else { Write-Host "  Still starting - felt-animation will pick it up once it's ready." }
} else {
    Write-Host "  Already running."
}

Write-Host "Stopping running Felt instances..."
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "felt_animation" -or $_.CommandLine -match "felt-tray" -or $_.CommandLine -match "felt_tray" -or $_.CommandLine -match "felt_vision" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Stop-Process -Name "FeltOverlay" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host "Starting Felt Animation (also launches the overlay)..."
Set-Location -Path "E:\Felt\felt-animation"
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m felt_animation" -WindowStyle Hidden

# Without this running, felt-tray's desktop watcher silently fails every
# single trigger (connection refused) with nothing visible anywhere -
# confirmed live, 2026-09-22: this is why screen-reaction voice/animation
# never happened, not a bug in the reaction logic itself.
# Both start through the venv's signed python.exe, not the uv-generated
# .exe launchers: Smart App Control blocks those whenever a re-sync
# regenerates them with a new hash (2026-09-26, felt-tray couldn't be
# restarted). felt-animation above already starts this way.
Write-Host "Starting Felt Vision..."
Set-Location -Path "E:\Felt\felt-vision"
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList '-c "from felt_vision.main import run; run()"' -WindowStyle Hidden

Write-Host "Starting Felt Tray..."
Set-Location -Path "E:\Felt\felt-tray"
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m felt_tray" -WindowStyle Hidden

Write-Host "Felt successfully launched in the background!"
Start-Sleep -Seconds 2
