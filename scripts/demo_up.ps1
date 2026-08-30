# Arranque del MVP para demo: login, documentos y chat.
# Uso:  .\scripts\demo_up.ps1
#       Detecta GPU NVIDIA sola; usa docker-compose.gpu.yaml si hay CUDA.
# CPU:  .\scripts\demo_up.ps1 -NoGpu
# Forzar GPU: .\scripts\demo_up.ps1 -Gpu

param(
    [switch]$Gpu,
    [switch]$NoGpu
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Creado .env desde .env.example. Cambia SECRET_KEY si expones el servicio."
}

function Test-NvidiaGpu {
    try {
        $null = & nvidia-smi -L 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-DockerGpu {
    try {
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { return $false }
        $info = docker info 2>$null | Out-String
        return ($info -match "(?i)Runtimes:.*nvidia|nvidia")
    } catch {
        return $false
    }
}

$useGpu = $false
if ($NoGpu) {
    $useGpu = $false
    Write-Host "GPU desactivada (-NoGpu)."
} elseif ($Gpu) {
    $useGpu = $true
} elseif ((Test-NvidiaGpu) -and (Test-DockerGpu)) {
    $useGpu = $true
    Write-Host "GPU NVIDIA detectada: se activa inferencia CUDA automaticamente."
} else {
    Write-Host "Sin GPU usable en Docker: Ollama arrancara en CPU."
}

$compose = @("compose", "--env-file", ".env", "-f", "docker-compose.yaml")
if ($useGpu) {
    $compose += @("-f", "docker-compose.gpu.yaml")
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
if ($LASTEXITCODE -ne 0 -and -not $useGpu) {
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
Write-Host ""
Write-Host "Procesador activo (CPU/GPU):"
docker compose exec ollama ollama ps

$port = if ($env:FRONTEND_HOST_PORT) { $env:FRONTEND_HOST_PORT } else { "80" }
Write-Host ""
Write-Host "Frontend:  http://localhost:$port"
Write-Host "API docs:  http://localhost:8000/docs"
Write-Host "Demo: registra un usuario, sube un PDF en Documentos y pregunta en el chat."
Write-Host "Inferencia: automatica (RAG agentic fast + modelos calientes tras ollama-init)."
if ($useGpu) {
    Write-Host "GPU: activa (docker-compose.gpu.yaml)."
}
if (-not $ready) {
    Write-Host "La API aun no responde /health. Revisa: docker compose logs -f api ollama-init"
}
