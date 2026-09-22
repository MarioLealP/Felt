Write-Host "Checking Felt's services on the Nitro5 (STT/TTS + the GPU-backed Ollama the server's brain calls)..."

# felt-voice (STT/TTS) and ollama are real systemd services there with scoped
# NOPASSWD sudo for benylin (systemctl only - confirmed 2026-09-22). ComfyUI
# is NOT a systemd service - Mario hand-swaps it with Ollama for the 6GB VRAM
# budget (never auto-restart Ollama, never touch ComfyUI here) - this script
# only ever starts felt-voice/ollama, never stops or restarts anything, and
# never touches ComfyUI at all.
$check = ssh clockmost-nitro5 "systemctl is-active felt-voice.service ollama.service"
$lines = $check -split "`n"
$feltVoiceActive = $lines[0] -eq "active"
$ollamaActive = $lines[1] -eq "active"

if ($feltVoiceActive) {
    Write-Host "  felt-voice: already running."
} else {
    Write-Host "  felt-voice: not running - starting..."
    ssh clockmost-nitro5 "sudo -n systemctl start felt-voice.service"
    Start-Sleep -Seconds 1
    $status = ssh clockmost-nitro5 "systemctl is-active felt-voice.service"
    if ($status -eq "active") { Write-Host "  felt-voice: started." } else { Write-Host "  felt-voice: FAILED to start (status: $status)." }
}

if ($ollamaActive) {
    Write-Host "  ollama: already running."
} else {
    Write-Host "  ollama: not running - starting..."
    ssh clockmost-nitro5 "sudo -n systemctl start ollama.service"
    Start-Sleep -Seconds 1
    $status = ssh clockmost-nitro5 "systemctl is-active ollama.service"
    if ($status -eq "active") { Write-Host "  ollama: started." } else { Write-Host "  ollama: FAILED to start (status: $status) - is ComfyUI using the GPU right now instead? Swap it back by hand first." }
}

Write-Host "Nitro5 check complete."
Start-Sleep -Seconds 2
