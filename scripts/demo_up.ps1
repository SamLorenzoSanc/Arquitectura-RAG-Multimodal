# Arranque del MVP para demo: login, documentos y chat.
# Uso:  .\scripts\demo_up.ps1
# GPU:  .\scripts\demo_up.ps1 -Gpu

param(
    [switch]$Gpu
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Creado .env desde .env.example. Cambia SECRET_KEY si expones el servicio."
}

$compose = @("compose", "--env-file", ".env")
if ($Gpu) {
    $compose += @("-f", "docker-compose.yaml", "-f", "docker-compose.gpu.yaml")
}

function Test-Docker {
    docker info 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Docker)) {
    $desktop = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $desktop) {
        Write-Host "Arrancando Docker Desktop..."
        Start-Process $desktop
    }
    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-Docker)) {
        if ((Get-Date) -gt $deadline) {
            throw "Docker Desktop no responde. Abre Docker y vuelve a ejecutar este script."
        }
        Start-Sleep -Seconds 5
    }
}

Write-Host "Construyendo e iniciando servicios..."
& docker @compose up -d --build
if ($LASTEXITCODE -ne 0 -and -not $Gpu) {
    Write-Host "El puerto 80 puede estar ocupado. Reintento en 8080..."
    $env:FRONTEND_HOST_PORT = "8080"
    & docker @compose up -d
}

Write-Host "Esperando API..."
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 3
}

Write-Host "Modelos Ollama:"
docker compose exec ollama ollama list

$port = if ($env:FRONTEND_HOST_PORT) { $env:FRONTEND_HOST_PORT } else { "80" }
Write-Host ""
Write-Host "Frontend:  http://localhost:$port"
Write-Host "API docs:  http://localhost:8000/docs"
Write-Host "Demo: registra un usuario, sube un PDF en Documentos y pregunta en el chat (modo agéntico)."
if (-not $ready) {
    Write-Host "La API aun no responde /health. Revisa: docker compose logs -f api ollama-init"
}
