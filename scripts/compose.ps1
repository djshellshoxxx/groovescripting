$ErrorActionPreference = 'Stop'
$pythonExe = if ($env:GROOVESCRIPTING_PYTHON) { $env:GROOVESCRIPTING_PYTHON } else { 'python' }
$projectRoot = Split-Path $PSScriptRoot -Parent
& $pythonExe -m groovescripting groovseq (Join-Path $projectRoot 'examples/first-groove.json') @args
exit $LASTEXITCODE
