[CmdletBinding()]
param(
    [string]$RepoPath = "",
    [string]$CondaEnv = "rtd",
    [string]$Branch = "main",
    [string]$CommitMessage = "camera calibration update",
    [string]$Room = "cork",
    [ValidateSet("mcal", "natnet")]
    [string]$CalibrationSource = "mcal",
    [string]$McalPath = "C:\ProgramData\OptiTrack\Motive\System Calibration.mcal",
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

function Get-GitStatusLines {
    $status = & git status --porcelain=v1
    if ($LASTEXITCODE -ne 0) {
        throw "git status --porcelain=v1 failed with exit code $LASTEXITCODE"
    }

    return @($status | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

function Assert-WorkingTreeReady {
    $statusLines = Get-GitStatusLines
    if (-not $statusLines) {
        return
    }

    $trackedChanges = @($statusLines | Where-Object { -not $_.StartsWith("?? ") })
    if ($trackedChanges.Count -gt 0) {
        $details = $trackedChanges -join "`n"
        throw "Working tree has tracked git changes. Commit/stash/reset them before running this script:`n$details"
    }

    $untrackedChanges = @($statusLines | Where-Object { $_.StartsWith("?? ") })
    if ($untrackedChanges.Count -gt 0) {
        Write-Warning "Continuing with untracked files present:`n$($untrackedChanges -join "`n")"
    }
}

function Assert-LiveMcalSourceReady {
    $liveMcalPath = "C:\ProgramData\OptiTrack\Motive\System Calibration.mcal"
    if ($CalibrationSource -ne "mcal" -or $McalPath -ne $liveMcalPath) {
        return
    }

    $motiveProcess = Get-Process -Name "Motive" -ErrorAction SilentlyContinue
    if ($motiveProcess) {
        return
    }

    throw @"
Motive is not running.
Start Motive on this machine and then run the shortcut again.

This shortcut reads the live calibration from:
$McalPath
"@
}

$capturedFailure = $null

Push-Location $RepoPath
try {
    Invoke-Step "Preflight" {
        if (-not (Test-Path ".git")) {
            throw "RepoPath is not a git repository: $RepoPath"
        }

        Assert-LiveMcalSourceReady
        Assert-WorkingTreeReady
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

        if ($CalibrationSource -eq "mcal") {
            $cmd = @("scripts/update_calib_from_mcal.py", "--room", $Room, "--mcal-path", $McalPath)
            if ($ServerIp) {
                $cmd += @("--server-ip", $ServerIp)
            }
        }
        else {
            $cmd = @("scripts/update_calib.py", "--room", $Room)
            if ($ServerIp) {
                $cmd += @("--server-ip", $ServerIp)
            }
            if ($NoMulticast) {
                $cmd += "--no-multicast"
            }
        }

        & python @cmd
        if ($LASTEXITCODE -ne 0) {
            throw "$($cmd[0]) failed with exit code $LASTEXITCODE"
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
catch {
    $capturedFailure = $_
}
finally {
    Pop-Location
}

if ($capturedFailure) {
    Write-Host ""
    Write-Host "Calibration save failed:" -ForegroundColor Red
    Write-Host $capturedFailure.Exception.Message -ForegroundColor Red

    exit 1
}
