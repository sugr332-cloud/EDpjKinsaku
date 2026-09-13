<#
.SYNOPSIS
Builds the standalone bio_entry binary that EliteIntel's CCoreAdapter invokes directly, instead of
requiring a system Python with EDpjKinsaku pip-installed (see EliteIntel's
docs/ELITEINTEL_INTEGRATION_PLAN.md Phase 8 decision).

.DESCRIPTION
`--onedir`, not `--onefile`: onefile's per-run self-extraction measured ~1.3s of startup overhead in
the Phase 8-A investigation, against CCoreAdapter's 5s timeout - onedir measured ~125ms, in line with
running `python -m app.cli` directly. `--paths` is required because EDpjKinsaku is normally
pip-installed in editable mode, which PyInstaller's static import analysis cannot follow on its own
(it reports `app` itself as a missing module without this).

Output lands in dist/ccore/bio_entry/ (bio_entry.exe plus its _internal/ dependency folder - both
must be copied together, and moved as one unit, since the bootloader resolves _internal relative to
the executable's own location). Copying that folder into EliteIntel's
distribution/ccore/windows/ is a separate, manual step for now; automating the cross-repo copy is
not in scope here.

.NOTES
Requires `pip install -e ".[packaging]"` in the active Python environment first.
#>
$repoRoot = Split-Path -Parent $PSScriptRoot

# Not wrapped with $ErrorActionPreference = "Stop": PyInstaller logs its normal INFO progress to
# stderr, which Windows PowerShell 5.1 turns into a NativeCommandError (setting $? to $false) even on
# a clean exit - check $LASTEXITCODE below instead, which reflects the real process exit code.
pyinstaller --onedir --noconfirm `
    --paths $repoRoot `
    --distpath "$repoRoot\dist\ccore" `
    --workpath "$repoRoot\build\ccore" `
    --specpath "$repoRoot\build\ccore-spec" `
    "$repoRoot\app\cli\bio_entry.py"

if ($LASTEXITCODE -ne 0) {
    Write-Error "pyinstaller exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
