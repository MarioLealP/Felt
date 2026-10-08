Write-Host "Checking Felt's services on the Nitro5 (felt-voice STT/TTS + felt-indextts)..."

# felt-voice (STT/TTS) and felt-indextts (the TTS engine it calls) are systemd services there,
# started with benylin's NOPASSWD systemctl. Ollama is gone from the laptop (2026-10 audit:
# Felt's brain is felt-llm on the server's P104). ComfyUI is a user service Mario manages -
# this script only ever starts the two Felt services, never stops or restarts anything, and
# never touches ComfyUI.
foreach ($svc in "felt-voice", "felt-indextts") {
    $state = ssh clockmost-nitro5 "systemctl is-active $svc.service"
    if ($state -eq "active") {
        Write-Host "  ${svc}: already running."
        continue
    }
    Write-Host "  ${svc}: not running - starting..."
    ssh clockmost-nitro5 "sudo -n systemctl start $svc.service"
    Start-Sleep -Seconds 1
    $state = ssh clockmost-nitro5 "systemctl is-active $svc.service"
    if ($state -eq "active") { Write-Host "  ${svc}: started." } else { Write-Host "  ${svc}: FAILED to start (status: $state)." }
}

Write-Host "Nitro5 check complete."
Start-Sleep -Seconds 2
