param(
  [switch]$WithOllama
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "[NebulaKB] $Message" -ForegroundColor Cyan
}

function Ensure-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $Name"
  }
}

function New-RandomString {
  param([int]$Length = 24)
  $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".ToCharArray()
  $bytes = New-Object byte[] $Length
  [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
  $builder = New-Object System.Text.StringBuilder
  foreach ($b in $bytes) {
    [void]$builder.Append($chars[$b % $chars.Length])
  }
  return $builder.ToString()
}

function New-SecretKey {
  $bytes = New-Object byte[] 48
  [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
  $token = [Convert]::ToBase64String($bytes)
  $token = $token.Replace("+", "").Replace("/", "").TrimEnd("=")
  if ($token.Length -lt 48) {
    return $token + (New-RandomString -Length (48 - $token.Length))
  }
  return $token.Substring(0, 48)
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"
$ComposeFile = Join-Path $ProjectRoot "docker-compose.dev.yml"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

Ensure-Command "python"
Ensure-Command "docker"

& docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "docker compose is required. Please install/upgrade Docker Desktop."
}

& docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Docker daemon is not running. Please start Docker Desktop first."
}

if (-not (Test-Path $EnvFile)) {
  Copy-Item $EnvExample $EnvFile
  Write-Step "Created .env from template."
}

$lines = Get-Content -Path $EnvFile -Encoding UTF8
$map = [ordered]@{}
$order = New-Object 'System.Collections.Generic.List[string]'

foreach ($line in $lines) {
  $trimmed = $line.TrimStart()
  if ($trimmed.StartsWith("#")) {
    continue
  }
  $index = $line.IndexOf("=")
  if ($index -lt 1) {
    continue
  }
  $key = $line.Substring(0, $index)
  $value = $line.Substring($index + 1)
  $map[$key] = $value
  $order.Add($key)
}

function Get-EnvValue {
  param([string]$Primary, [string]$Legacy, [string]$Default)
  if ($map.Contains($Primary) -and -not [string]::IsNullOrWhiteSpace([string]$map[$Primary])) {
    return [string]$map[$Primary]
  }
  if ($Legacy -and $map.Contains($Legacy) -and -not [string]::IsNullOrWhiteSpace([string]$map[$Legacy])) {
    return [string]$map[$Legacy]
  }
  return $Default
}

function Sync-LegacyValue {
  param([string]$Primary, [string]$Legacy)
  if (-not $map.Contains($Primary)) {
    return
  }
  if ((-not $map.Contains($Legacy)) -or [string]::IsNullOrWhiteSpace([string]$map[$Legacy]) -or [string]$map[$Legacy] -like "*CHANGE_ME_*") {
    $map[$Legacy] = [string]$map[$Primary]
    if (-not $order.Contains($Legacy)) { $order.Add($Legacy) }
  }
}

$dbPasswordBefore = Get-EnvValue "NEBULA_DB_PASSWORD" "LZKB_DB_PASSWORD" ""
$redisPasswordBefore = Get-EnvValue "NEBULA_REDIS_PASSWORD" "LZKB_REDIS_PASSWORD" ""

if ((-not $map.Contains("SECRET_KEY")) -or [string]::IsNullOrWhiteSpace([string]$map["SECRET_KEY"]) -or [string]$map["SECRET_KEY"] -like "*CHANGE_ME_*") {
  $map["SECRET_KEY"] = New-SecretKey
  if (-not $order.Contains("SECRET_KEY")) { $order.Add("SECRET_KEY") }
}

if ((-not $map.Contains("NEBULA_DB_PASSWORD")) -and $map.Contains("LZKB_DB_PASSWORD")) {
  $map["NEBULA_DB_PASSWORD"] = [string]$map["LZKB_DB_PASSWORD"]
  if (-not $order.Contains("NEBULA_DB_PASSWORD")) { $order.Add("NEBULA_DB_PASSWORD") }
}

if ((-not $map.Contains("NEBULA_REDIS_PASSWORD")) -and $map.Contains("LZKB_REDIS_PASSWORD")) {
  $map["NEBULA_REDIS_PASSWORD"] = [string]$map["LZKB_REDIS_PASSWORD"]
  if (-not $order.Contains("NEBULA_REDIS_PASSWORD")) { $order.Add("NEBULA_REDIS_PASSWORD") }
}

if ((-not $map.Contains("NEBULA_DB_PASSWORD")) -or [string]::IsNullOrWhiteSpace([string]$map["NEBULA_DB_PASSWORD"]) -or [string]$map["NEBULA_DB_PASSWORD"] -like "*CHANGE_ME_*") {
  $map["NEBULA_DB_PASSWORD"] = New-RandomString -Length 24
  if (-not $order.Contains("NEBULA_DB_PASSWORD")) { $order.Add("NEBULA_DB_PASSWORD") }
}

if ((-not $map.Contains("NEBULA_REDIS_PASSWORD")) -or [string]::IsNullOrWhiteSpace([string]$map["NEBULA_REDIS_PASSWORD"]) -or [string]$map["NEBULA_REDIS_PASSWORD"] -like "*CHANGE_ME_*") {
  $map["NEBULA_REDIS_PASSWORD"] = New-RandomString -Length 24
  if (-not $order.Contains("NEBULA_REDIS_PASSWORD")) { $order.Add("NEBULA_REDIS_PASSWORD") }
}

Sync-LegacyValue "NEBULA_DB_PASSWORD" "LZKB_DB_PASSWORD"
Sync-LegacyValue "NEBULA_REDIS_PASSWORD" "LZKB_REDIS_PASSWORD"

$dbUser = Get-EnvValue "NEBULA_DB_USER" "LZKB_DB_USER" "root"
$dbHost = Get-EnvValue "NEBULA_DB_HOST" "LZKB_DB_HOST" "127.0.0.1"
$dbPort = Get-EnvValue "NEBULA_DB_PORT" "LZKB_DB_PORT" "5432"
$dbName = Get-EnvValue "NEBULA_DB_NAME" "LZKB_DB_NAME" "nebula"
$redisHost = Get-EnvValue "NEBULA_REDIS_HOST" "LZKB_REDIS_HOST" "127.0.0.1"
$redisPort = Get-EnvValue "NEBULA_REDIS_PORT" "LZKB_REDIS_PORT" "6379"
$redisDb = Get-EnvValue "NEBULA_REDIS_DB" "LZKB_REDIS_DB" "0"

$dbUrl = "postgresql://$dbUser:$($map["NEBULA_DB_PASSWORD"])@$dbHost:$dbPort/$dbName"
$redisUrl = "redis://:$($map["NEBULA_REDIS_PASSWORD"])@$redisHost:$redisPort/$redisDb"

$rewriteDbUrl = (-not $map.Contains("DATABASE_URL")) -or [string]$map["DATABASE_URL"] -like "*CHANGE_ME_DB_PASSWORD*"
if (-not $rewriteDbUrl -and $dbPasswordBefore -and [string]$map["DATABASE_URL"] -like "*$dbPasswordBefore*" -and [string]$map["NEBULA_DB_PASSWORD"] -ne $dbPasswordBefore) {
  $rewriteDbUrl = $true
}
if ($rewriteDbUrl) {
  $map["DATABASE_URL"] = $dbUrl
  if (-not $order.Contains("DATABASE_URL")) { $order.Add("DATABASE_URL") }
}

$rewriteRedisUrl = (-not $map.Contains("REDIS_URL")) -or [string]$map["REDIS_URL"] -like "*CHANGE_ME_REDIS_PASSWORD*"
if (-not $rewriteRedisUrl -and $redisPasswordBefore -and [string]$map["REDIS_URL"] -like "*$redisPasswordBefore*" -and [string]$map["NEBULA_REDIS_PASSWORD"] -ne $redisPasswordBefore) {
  $rewriteRedisUrl = $true
}
if ($rewriteRedisUrl) {
  $map["REDIS_URL"] = $redisUrl
  if (-not $order.Contains("REDIS_URL")) { $order.Add("REDIS_URL") }
}

$newLines = New-Object 'System.Collections.Generic.List[string]'
$seen = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($line in $lines) {
  $trimmed = $line.TrimStart()
  if ($trimmed.StartsWith("#")) {
    $newLines.Add($line)
    continue
  }
  $index = $line.IndexOf("=")
  if ($index -lt 1) {
    $newLines.Add($line)
    continue
  }
  $key = $line.Substring(0, $index)
  if ($map.Contains($key)) {
    $newLines.Add("$key=$($map[$key])")
    [void]$seen.Add($key)
  } else {
    $newLines.Add($line)
  }
}

foreach ($key in $order) {
  if ($map.Contains($key) -and -not $seen.Contains($key)) {
    $newLines.Add("$key=$($map[$key])")
    [void]$seen.Add($key)
  }
}

Set-Content -Path $EnvFile -Value $newLines -Encoding UTF8
Write-Step "Updated .env secrets for local development."

if (-not (Test-Path $VenvPython)) {
  & python -m venv (Join-Path $ProjectRoot ".venv")
}

$VenvPython = (Resolve-Path $VenvPython).Path

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e .

$composeArgs = @("--env-file", $EnvFile, "-f", $ComposeFile)
$services = @("postgres", "redis")
if ($WithOllama) {
  $services += "ollama"
}

& docker compose @composeArgs up -d @services

$ready = $false
for ($i = 1; $i -le 30; $i++) {
  & docker compose @composeArgs exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' *> $null
  if ($LASTEXITCODE -eq 0) {
    $ready = $true
    break
  }
  Start-Sleep -Seconds 2
}

if (-not $ready) {
  throw "PostgreSQL did not become ready in time."
}

& docker compose @composeArgs exec -T postgres sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'

& $VenvPython "apps/manage.py" "migrate"

Write-Host ""
Write-Host "Quick install completed." -ForegroundColor Green
Write-Host ""
Write-Host "Run backend:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python .\main.py dev web"
Write-Host ""
Write-Host "Frontend dev server:" -ForegroundColor Yellow
Write-Host "  cd .\ui"
Write-Host "  npm install"
Write-Host "  npm run dev"
