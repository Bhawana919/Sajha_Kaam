# Start the Sajha Kaam backend. Run from anywhere:
#   .\sajha-kaam\backend\start.ps1
# First time only, install the dependencies (from the Sajha_Kaam_Hackathon_Kit folder):
#   pip install -r requirements.txt
param([int]$Port = 8000)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
# Use a local .venv if someone made one; otherwise the normal Python on PATH.
$venvPython = Join-Path $here ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

& $python -c "import fastapi, sqlmodel, nacl, PIL, bcrypt, jwt, yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    $kit = Split-Path -Parent (Split-Path -Parent $here)
    Write-Host "Some packages are missing. Install them once, then run this script again:" -ForegroundColor Yellow
    Write-Host "  pip install -r `"$kit\requirements.txt`""
    exit 1
}

Set-Location $here
Write-Host "Sajha Kaam API on http://0.0.0.0:$Port  (docs: http://localhost:$Port/docs)  Ctrl+C to stop"
& $python -m uvicorn app.main:app --host 0.0.0.0 --port $Port
