# init.ps1 - Verificacion integral de Phoenix Reflex (PowerShell)
# Uso: .\init.ps1  (desde la raiz del repo)
# Exit 0 = OK. Exit 1 = hay fallos.

$script:nPass = 0
$script:nFail = 0
$script:nWarn = 0

function CheckOk   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green;  $script:nPass = $script:nPass + 1 }
function CheckFail { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red;    $script:nFail = $script:nFail + 1 }
function CheckWarn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow; $script:nWarn = $script:nWarn + 1 }
function CheckSep  { Write-Host "---" }

Write-Host "=== Phoenix Reflex - Verificacion integral ===" -ForegroundColor Cyan
CheckSep

# 1. Entorno
Write-Host "# 1. Entorno"

$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pyCmd) {
    $pyVer = (& python --version 2>&1)
    CheckOk "Python: $pyVer"
} else {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $pyVer = (& py --version 2>&1)
        CheckOk "Python (py launcher): $pyVer"
    } else {
        CheckFail "Python no encontrado - instala Python 3.12+"
    }
}

CheckSep

# 2. Archivos base del workflow SDD
Write-Host "# 2. Arnes SDD"

$requiredFiles = @(
    "AGENTS.md", "CLAUDE.md", "CHECKPOINTS.md", "feature_list.json",
    "docs/architecture.md", "docs/conventions.md", "docs/specs.md", "docs/verification.md",
    ".claude/agents/leader.md", ".claude/agents/spec_author.md",
    ".claude/agents/implementer.md", ".claude/agents/reviewer.md",
    "progress/current.md", "progress/history.md"
)

foreach ($f in $requiredFiles) {
    if (Test-Path $f) {
        CheckOk "Existe $f"
    } else {
        CheckFail "Falta $f"
    }
}

foreach ($d in @("specs", "progress", "docs")) {
    if (Test-Path $d -PathType Container) {
        CheckOk "Directorio $d/"
    } else {
        CheckFail "Falta directorio $d/"
    }
}

CheckSep

# 3. Validar feature_list.json
Write-Host "# 3. feature_list.json"

if (Test-Path "feature_list.json") {
    $jsCode = "const fs=require('fs');let data;try{data=JSON.parse(fs.readFileSync('feature_list.json','utf8'))}catch(e){console.log('[FAIL] JSON invalido: '+e.message);process.exit(1)};const valid=['pending','spec_ready','in_progress','review_pending','done','blocked'];let fail=0;const ip=data.features.filter(f=>f.status==='in_progress');if(ip.length>1){console.log('[FAIL] Mas de 1 feature in_progress: '+ip.map(f=>f.name).join(', '));fail++;}else{console.log('[OK]   Max 1 feature in_progress ('+ip.length+')');};for(const f of data.features){if(!valid.includes(f.status)){console.log('[FAIL] Status invalido en '+f.name+': '+f.status);fail++;}};if(fail===0)console.log('[OK]   Estados validos');if(fail>0)process.exit(1);"
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) {
        $result = & node -e $jsCode 2>&1
        Write-Host $result
        if ($LASTEXITCODE -eq 0) {
            CheckOk "feature_list.json valido"
        } else {
            CheckFail "feature_list.json invalido"
        }
    } else {
        CheckWarn "node no disponible - saltando validacion JSON"
    }
} else {
    CheckFail "feature_list.json no existe"
}

CheckSep

# 4. Import check Python
Write-Host "# 4. Import check Python"

$importCheck = & python -c "import phoenix_reflex; import phoenix_reflex_agent; print('ok')" 2>&1
if ($LASTEXITCODE -eq 0) {
    CheckOk "import phoenix_reflex + phoenix_reflex_agent OK"
} else {
    $errStr = "$importCheck"
    if ($errStr -match "ModuleNotFoundError") {
        CheckWarn "Dependencias no instaladas (activa el venv y ejecuta: pip install -r requirements.txt)`n       $errStr"
    } else {
        CheckFail "Import error: $errStr"
    }
}

CheckSep

# 5. Tests
Write-Host "# 5. Tests"

$testFiles = Get-ChildItem -Path "tests" -Recurse -Filter "test_*.py" -ErrorAction SilentlyContinue

if ($testFiles -and $testFiles.Count -gt 0) {
    $testOut = & python -m pytest tests/ --tb=short -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        CheckOk "Tests verdes ($($testFiles.Count) archivos de test)"
    } else {
        CheckFail "Tests en rojo:`n$testOut"
    }
} else {
    CheckWarn "Sin archivos de test aun en tests/ (normal para este proyecto)"
}

CheckSep

# 6. Verificar .env o .env.example
Write-Host "# 6. Variables de entorno"

if (Test-Path ".env") {
    CheckOk ".env existe"
} elseif (Test-Path ".env.example") {
    CheckWarn ".env no existe (usa .env.example como plantilla)"
} else {
    CheckFail "Ni .env ni .env.example encontrados"
}

CheckSep

# Resumen
Write-Host "=== Resumen ===" -ForegroundColor Cyan
Write-Host "  OK:   $script:nPass"
Write-Host "  WARN: $script:nWarn"
Write-Host "  FAIL: $script:nFail"

if ($script:nFail -gt 0) {
    Write-Host "=== RESULTADO: FAIL ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== RESULTADO: OK - listo para trabajar ===" -ForegroundColor Green
    exit 0
}
