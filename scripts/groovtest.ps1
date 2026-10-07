$ErrorActionPreference = "Stop"
$engine = if ($env:GROOVESCRIPTING_PYTHON) { $env:GROOVESCRIPTING_PYTHON } else { "python" }
& $engine -m groovescripting groovtest @args
exit $LASTEXITCODE
