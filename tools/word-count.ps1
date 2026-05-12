<#
.SYNOPSIS
  Word count and reading-time check for every post.

.DESCRIPTION
  Reads each posts/*/index.md, counts words (excluding code blocks and YAML
  frontmatter), reports estimated reading time at 220 wpm, and warns on any
  post outside the target range (default 1800-3500 words).

.EXAMPLE
  pwsh tools/word-count.ps1
  pwsh tools/word-count.ps1 -MinWords 2000 -MaxWords 4000
#>

[CmdletBinding()]
param(
    # Floor reflects the editorial bar of the series: depth-not-padding.
    # Build posts (22, 23) intentionally run shorter because their substance
    # lives in the runnable companion code under code/.
    [int]$MinWords = 900,
    [int]$MaxWords = 3500,
    [int]$WPM      = 220,
    [string]$PostsRoot
)

if (-not $PostsRoot) {
    $PostsRoot = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\posts'
}

function Get-PostBodyText {
    param([string]$Path)
    $raw = Get-Content -Raw -Path $Path -Encoding UTF8
    # strip YAML frontmatter
    $raw = [regex]::Replace($raw, '(?s)^---\s*\n.*?\n---\s*\n', '')
    # strip fenced code blocks
    $raw = [regex]::Replace($raw, '(?s)```.*?```', ' ')
    # strip inline code
    $raw = [regex]::Replace($raw, '`[^`]+`', ' ')
    # strip markdown links, keep label
    $raw = [regex]::Replace($raw, '\[([^\]]+)\]\([^\)]+\)', '$1')
    # strip headings/markup punctuation
    $raw = [regex]::Replace($raw, '[#>*_~|-]+', ' ')
    return $raw
}

$results = @()
$posts = Get-ChildItem -Path $PostsRoot -Directory | Sort-Object Name
foreach ($p in $posts) {
    $idx = Join-Path $p.FullName 'index.md'
    if (-not (Test-Path $idx)) { continue }
    $text = Get-PostBodyText -Path $idx
    $words = ($text -split '\s+' | Where-Object { $_ -match '\w' }).Count
    $minutes = [math]::Round($words / $WPM, 1)
    $status = if ($words -lt $MinWords) { 'SHORT' }
              elseif ($words -gt $MaxWords) { 'LONG' }
              else { 'ok' }
    $results += [pscustomobject]@{
        Post     = $p.Name
        Words    = $words
        Minutes  = $minutes
        Status   = $status
    }
}

$results | Format-Table -AutoSize

$bad = $results | Where-Object { $_.Status -ne 'ok' }
if ($bad) {
    Write-Host ''
    Write-Warning ("{0} post(s) outside target range {1}-{2} words." -f $bad.Count, $MinWords, $MaxWords)
    exit 1
} else {
    Write-Host ''
    Write-Host ("All {0} posts within target range." -f $results.Count) -ForegroundColor Green
    exit 0
}
