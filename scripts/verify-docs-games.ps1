<#
.SYNOPSIS
  Verifica ca `docs/games` nu contina linkuri markdown spre `../zpl-engine-sdk/...` sau literali `C:\Dev` (rupe pe GitHub / nu sunt portabile).

.PARAMETER RepoRoot
  Rădăcina monorepo-ului SDK (folder care contine `docs/`). Implicit: părintele acestui script (`scripts/` -> radacina repo).

.EXAMPLE
  ./scripts/verify-docs-games.ps1
  pwsh ./scripts/verify-docs-games.ps1 -RepoRoot /home/runner/work/zpl-engine-sdk/zpl-engine-sdk
#>
param(
  [string]$RepoRoot = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = "Stop"
$utf8 = [System.Text.UTF8Encoding]::new($false)
$Dst = Join-Path $RepoRoot "docs/games"

if (-not (Test-Path $Dst)) {
  Write-Host "SKIP: nu exista $Dst"
  exit 0
}

$patterns = @(
  @{ Name = 'md-link paren ../zpl-engine-sdk/'; Regex = '\]\(\.\./zpl-engine-sdk/' }
  @{ Name = 'md-link paren ../../zpl-engine-sdk/'; Regex = '\]\(\.\./\.\./zpl-engine-sdk/' }
  @{ Name = 'Windows path C:\Dev in games docs'; Regex = 'C:\\Dev' }
)

$failed = $false
Get-ChildItem -Path $Dst -Recurse -Filter "*.md" | ForEach-Object {
  $text = [System.IO.File]::ReadAllText($_.FullName, $utf8)
  $rel = $_.FullName.Substring($RepoRoot.Length).TrimStart([char[]]"/\")
  foreach ($p in $patterns) {
    if ($text -match $p.Regex) {
      Write-Warning ("FAIL {0} in {1}" -f $p.Name, $rel)
      $failed = $true
    }
  }
}

if ($failed) {
  Write-Error "Verificare esuata in docs/games."
  exit 1
}
Write-Host 'OK: docs/games - fara linkuri relative zpl-engine-sdk si fara literal C:\Dev in fisiere.'
