<#
.SYNOPSIS
  Build the printable cheatsheet PDF from CHEATSHEET.md.

.DESCRIPTION
  Renders CHEATSHEET.md to assets/cheatsheet.pdf for printing at A4.
  Tries pandoc first; falls back to a simple HTML render via the browser
  if pandoc is not available.

.EXAMPLE
  pwsh tools/build-cheatsheet.ps1
#>

[CmdletBinding()]
param(
    [string]$Source,
    [string]$OutDir
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Source) { $Source = Join-Path $here '..\CHEATSHEET.md' }
if (-not $OutDir) { $OutDir = Join-Path $here '..\assets' }

if (-not (Test-Path $Source)) { Write-Error "missing $Source"; exit 1 }
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$pdfOut  = Join-Path $OutDir 'cheatsheet.pdf'
$htmlOut = Join-Path $OutDir 'cheatsheet.html'

if (Get-Command pandoc -ErrorAction SilentlyContinue) {
    Write-Host "  pandoc -> $pdfOut"
    & pandoc $Source -o $pdfOut `
        --pdf-engine=wkhtmltopdf `
        --metadata title="Context Engineering — Cheatsheet" `
        --variable geometry:a4paper `
        --variable geometry:margin=15mm
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "pandoc failed; producing HTML instead."
    } else {
        Write-Host ("done: {0}" -f $pdfOut) -ForegroundColor Green
        exit 0
    }
}

# Fallback: minimal standalone HTML
$body = (Get-Content -Raw -Path $Source -Encoding UTF8)
$html = @"
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" />
<title>Context Engineering — Cheatsheet</title>
<style>
 :root { --ink:#1A1A1A; --bg:#FAFAF7; --primary:#5B7FBF; --accent:#D98E5F; }
 body { font: 13px/1.45 'Inter', system-ui, sans-serif; color:var(--ink); background:var(--bg);
        max-width: 980px; margin: 24px auto; padding: 0 16px; }
 h1,h2,h3 { color: var(--primary); }
 code, pre { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 12px; }
 table { border-collapse: collapse; width: 100%; margin: 8px 0 16px; }
 th, td { border: 1px solid rgba(26,26,26,0.15); padding: 6px 8px; text-align: left; }
 th { background: rgba(91,127,191,0.08); }
 @media print { body { margin: 0; padding: 8mm; } }
</style>
</head><body>
<pre style="white-space: pre-wrap; font-family: inherit;">
$([System.Web.HttpUtility]::HtmlEncode($body))
</pre>
</body></html>
"@
Add-Type -AssemblyName System.Web
$html | Set-Content -Path $htmlOut -Encoding UTF8
Write-Host ("done: {0}" -f $htmlOut) -ForegroundColor Green
Write-Host "Open it in a browser and use 'Print to PDF' for the printable artefact."
