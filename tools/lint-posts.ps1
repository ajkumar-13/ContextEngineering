<#
.SYNOPSIS
  Structural lint for series posts.

.DESCRIPTION
  Verifies that each posts/*/index.md follows the locked voice template:
  - Has a "TL;DR" line
  - Has a "Reading time:" line
  - Has an "After reading this you will be able to:" block
  - Has a "## Common pitfalls" section
  - Has a "## Further reading" section
  - Has a "## What to read next" section
  - Does not link to non-existent posts (relative ../NN-slug/index.md)

  Exits non-zero on any failure; prints a per-post summary.

.EXAMPLE
  pwsh tools/lint-posts.ps1
#>

[CmdletBinding()]
param(
    [string]$PostsRoot
)

if (-not $PostsRoot) {
    $PostsRoot = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\posts'
}

$required = @(
    @{ Name = 'TL;DR';            Pattern = '\*\*TL;DR\.\*\*' }
    @{ Name = 'Reading time';     Pattern = '\*\*Reading time:\*\*' }
    @{ Name = 'Outcomes block';   Pattern = '\*\*After reading this you will be able to:\*\*' }
    @{ Name = 'Common pitfalls';  Pattern = '##\s*Common pitfalls' }
    @{ Name = 'Further reading';  Pattern = '##\s*Further reading' }
    @{ Name = 'What to read next';Pattern = '##\s*What to read next' }
)

$existingSlugs = @{}
Get-ChildItem -Path $PostsRoot -Directory | ForEach-Object {
    $existingSlugs[$_.Name] = $true
}

$failures = @()
$rows = @()
foreach ($dir in (Get-ChildItem -Path $PostsRoot -Directory | Sort-Object Name)) {
    $idx = Join-Path $dir.FullName 'index.md'
    if (-not (Test-Path $idx)) {
        $failures += "$($dir.Name): missing index.md"
        continue
    }
    $text = Get-Content -Raw -Path $idx -Encoding UTF8
    $missing = @()
    foreach ($req in $required) {
        if ($text -notmatch $req.Pattern) { $missing += $req.Name }
    }
    # check internal post links
    $brokenLinks = @()
    $linkMatches = [regex]::Matches($text, '\.\./(\d{2}-[a-z0-9-]+)/index\.md')
    foreach ($m in $linkMatches) {
        $slug = $m.Groups[1].Value
        if (-not $existingSlugs.ContainsKey($slug)) {
            $brokenLinks += $slug
        }
    }
    $status = if ($missing.Count -eq 0 -and $brokenLinks.Count -eq 0) { 'ok' } else { 'FAIL' }
    if ($status -eq 'FAIL') {
        $failures += "$($dir.Name): missing=[$($missing -join ', ')] brokenLinks=[$(($brokenLinks | Sort-Object -Unique) -join ', ')]"
    }
    $rows += [pscustomobject]@{
        Post        = $dir.Name
        Missing     = ($missing -join ', ')
        BrokenLinks = (($brokenLinks | Sort-Object -Unique) -join ', ')
        Status      = $status
    }
}

$rows | Format-Table -AutoSize

if ($failures.Count -gt 0) {
    Write-Host ''
    Write-Warning ("{0} post(s) failed lint." -f $failures.Count)
    $failures | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    exit 1
} else {
    Write-Host ''
    Write-Host ("All {0} posts pass lint." -f $rows.Count) -ForegroundColor Green
    exit 0
}
