# Switch this repository to the Conzura GitHub identity
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$GitUser = "bala-fullstack-developer-conzura"
$GitEmail = "298310367+bala-fullstack-developer-conzura@users.noreply.github.com"

Write-Host "==> Setting local git identity for this repo" -ForegroundColor Cyan
git config --local user.name $GitUser
git config --local user.email $GitEmail

Write-Host "    user.name:  $(git config --local user.name)"
Write-Host "    user.email: $(git config --local user.email)"

Write-Host ""
Write-Host "==> GitHub CLI account" -ForegroundColor Cyan
if (Get-Command gh -ErrorAction SilentlyContinue) {
    $switch = gh auth switch -u $GitUser 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Active gh account: $GitUser" -ForegroundColor Green
    } else {
        Write-Host "    $GitUser is not logged in to GitHub CLI yet." -ForegroundColor Yellow
        Write-Host "    Run this once in your terminal:"
        Write-Host "      gh auth login -h github.com -p https -w" -ForegroundColor White
        Write-Host "    Then switch with:"
        Write-Host "      gh auth switch -u $GitUser" -ForegroundColor White
    }
    gh auth status 2>&1 | Select-String "Logged in|Active account"
} else {
    Write-Host "    gh CLI not installed. Install from https://cli.github.com/" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Current remote:" -ForegroundColor Cyan
git remote -v

Write-Host ""
Write-Host "Done. Commits in this repo will use $GitUser." -ForegroundColor Green
