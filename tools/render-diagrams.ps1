<#
.SYNOPSIS
  Re-render diagram source files to SVG / PNG exports.

.DESCRIPTION
  Walks assets/diagrams/src/ and re-exports each source to
  assets/diagrams/exports/ alongside any existing artefact.

  Supported formats:
    .mmd        -> SVG via @mermaid-js/mermaid-cli (npx -y mmdc)
    .drawio     -> SVG via drawio-desktop CLI (if available on PATH)
    .svg        -> copied verbatim (already exported)
    .excalidraw -> requires manual export (warns)

  Skips files whose target export is newer than the source.

.EXAMPLE
  pwsh tools/render-diagrams.ps1
  pwsh tools/render-diagrams.ps1 -Force
#>

[CmdletBinding()]
param(
    [switch]$Force,
    [string]$Root
)

if (-not $Root) {
    $Root = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\assets\diagrams'
}

$srcDir = Join-Path $Root 'src'
$outDir = Join-Path $Root 'exports'
if (-not (Test-Path $srcDir)) { Write-Warning "no source dir: $srcDir"; exit 0 }
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

function Need-Render($src, $dst) {
    if ($Force) { return $true }
    if (-not (Test-Path $dst)) { return $true }
    return ((Get-Item $src).LastWriteTime -gt (Get-Item $dst).LastWriteTime)
}

$rendered = 0; $skipped = 0; $warned = 0
foreach ($f in Get-ChildItem -Path $srcDir -File -Recurse) {
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $dst  = Join-Path $outDir "$stem.svg"
    switch ($f.Extension.ToLower()) {
        '.mmd' {
            if (Need-Render $f.FullName $dst) {
                Write-Host "  mermaid: $($f.Name) -> $stem.svg"
                & npx -y @mermaid-js/mermaid-cli -i $f.FullName -o $dst -b transparent
                $rendered++
            } else { $skipped++ }
        }
        '.drawio' {
            if (Need-Render $f.FullName $dst) {
                Write-Host "  drawio:  $($f.Name) -> $stem.svg"
                & drawio --export --format svg --output $dst $f.FullName
                $rendered++
            } else { $skipped++ }
        }
        '.svg' {
            if (Need-Render $f.FullName $dst) {
                Copy-Item $f.FullName $dst -Force
                Write-Host "  svg:     $($f.Name) -> $stem.svg (copied)"
                $rendered++
            } else { $skipped++ }
        }
        '.excalidraw' {
            Write-Warning "  $($f.Name): .excalidraw must be exported manually from excalidraw.com / app"
            $warned++
        }
        default {
            Write-Verbose "  ignored: $($f.Name)"
        }
    }
}

Write-Host ''
Write-Host ("rendered={0} skipped={1} warned={2}" -f $rendered, $skipped, $warned)
