[CmdletBinding()]
param(
    [string]$RepoPath = "",
    [string]$CondaEnv = "rtd",
    [string]$Branch = "main",
    [string]$CommitMessage = "camera calibration update",
    [string]$Room = "cork",
    [string]$ServerIp = "",
    [switch]$NoMulticast
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoPath)) {
    $scriptRoot = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($scriptRoot)) {
        $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    if ([string]::IsNullOrWhiteSpace($scriptRoot)) {
        throw "Unable to resolve script location; pass -RepoPath explicitly."
    }
    $RepoPath = (Resolve-Path (Join-Path $scriptRoot "..")).Path
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    Write-Host ""
    Write-Host "== $Label ==" -ForegroundColor Cyan
    & $Action
}

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Args)

    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Initialize-Conda {
    $conda = Get-Command conda -ErrorAction SilentlyContinue
    if (-not $conda) {
        throw "conda command not found. Install Anaconda/Miniconda or add it to PATH."
    }

    $hook = (& $conda.Source "shell.powershell" "hook" 2>$null | Out-String)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($hook)) {
        throw "Unable to initialize conda PowerShell hook via $($conda.Source)"
    }

    Invoke-Expression $hook
    conda activate $CondaEnv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate conda env '$CondaEnv'"
    }

    Write-Host "Conda env active: $CondaEnv"
}

Push-Location $RepoPath
try {
    Invoke-Step "Preflight" {
        if (-not (Test-Path ".git")) {
            throw "RepoPath is not a git repository: $RepoPath"
        }

        $dirty = git status --porcelain
        if ($LASTEXITCODE -ne 0) {
            throw "git status failed with exit code $LASTEXITCODE"
        }
        if ($dirty) {
            throw "Working tree is not clean. Commit/stash changes before running this script."
        }
    }

    Invoke-Step "Activate conda environment" {
        Initialize-Conda
    }

    Invoke-Step "Sync repository" {
        Invoke-Git @("fetch", "origin")
        Invoke-Git @("checkout", $Branch)
        Invoke-Git @("pull", "--ff-only", "origin", $Branch)
    }

    Invoke-Step "Update camera calibration" {
        if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
            $env:PYTHONPATH = $RepoPath
        }
        else {
            $env:PYTHONPATH = "$RepoPath;$($env:PYTHONPATH)"
        }

        $cmd = @("scripts/update_calib.py", "--room", $Room)
        if ($ServerIp) {
            $cmd += @("--server-ip", $ServerIp)
        }
        if ($NoMulticast) {
            $cmd += "--no-multicast"
        }

        & python @cmd
        if ($LASTEXITCODE -ne 0) {
            throw "update_calib.py failed with exit code $LASTEXITCODE"
        }
    }

    Invoke-Step "Commit and push snapshot" {
        Invoke-Git @("add", "optitrack_motive/calib")

        & git diff --cached --quiet -- "optitrack_motive/calib"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "No calibration changes detected; nothing to commit."
            return
        }
        if ($LASTEXITCODE -ne 1) {
            throw "git diff --cached --quiet failed with exit code $LASTEXITCODE"
        }

        Invoke-Git @("commit", "-m", $CommitMessage)
        Invoke-Git @("push", "origin", $Branch)
        Write-Host "Push complete."
    }
}
finally {
    Pop-Location
}
