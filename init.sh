#!/usr/bin/env bash
# init.sh - Verificacion integral de Phoenix Reflex (bash / Git Bash / WSL)
# Uso: bash ./init.sh
# Exit 0 = OK. Exit 1 = hay fallos.

nPass=0
nFail=0
nWarn=0

ok()   { echo "[OK]   $1"; nPass=$((nPass+1)); }
fail() { echo "[FAIL] $1"; nFail=$((nFail+1)); }
warn() { echo "[WARN] $1"; nWarn=$((nWarn+1)); }
sep()  { echo "---"; }

echo "=== Phoenix Reflex - Verificacion integral ==="
sep

# 1. Entorno
echo "# 1. Entorno"

if command -v python3 &>/dev/null; then
    ok "Python3: $(python3 --version 2>&1)"
elif command -v python &>/dev/null; then
    ok "Python: $(python --version 2>&1)"
else
    fail "Python no encontrado - instala Python 3.12+"
fi

sep

# 2. Archivos base del workflow SDD
echo "# 2. Arnes SDD"

required_files=(
    "AGENTS.md" "CLAUDE.md" "CHECKPOINTS.md" "feature_list.json"
    "docs/architecture.md" "docs/conventions.md" "docs/specs.md" "docs/verification.md"
    ".claude/agents/leader.md" ".claude/agents/spec_author.md"
    ".claude/agents/implementer.md" ".claude/agents/reviewer.md"
    "progress/current.md" "progress/history.md"
)

for f in "${required_files[@]}"; do
    if [ -f "$f" ]; then
        ok "Existe $f"
    else
        fail "Falta $f"
    fi
done

for d in specs progress docs; do
    if [ -d "$d" ]; then
        ok "Directorio $d/"
    else
        fail "Falta directorio $d/"
    fi
done

sep

# 3. Validar feature_list.json
echo "# 3. feature_list.json"

if [ -f "feature_list.json" ]; then
    if command -v node &>/dev/null; then
        node -e "
const fs=require('fs');
let data;
try { data=JSON.parse(fs.readFileSync('feature_list.json','utf8')); }
catch(e) { console.log('[FAIL] JSON invalido: '+e.message); process.exit(1); }
const valid=['pending','spec_ready','in_progress','review_pending','done','blocked'];
let fail=0;
const ip=data.features.filter(f=>f.status==='in_progress');
if(ip.length>1){console.log('[FAIL] Mas de 1 feature in_progress: '+ip.map(f=>f.name).join(', '));fail++;}
else{console.log('[OK]   Max 1 feature in_progress ('+ip.length+')');}
for(const f of data.features){
  if(!valid.includes(f.status)){console.log('[FAIL] Status invalido en '+f.name+': '+f.status);fail++;}
}
if(fail===0)console.log('[OK]   Estados validos');
if(fail>0)process.exit(1);
" && ok "feature_list.json valido" || fail "feature_list.json invalido"
    else
        warn "node no disponible - saltando validacion JSON"
    fi
else
    fail "feature_list.json no existe"
fi

sep

# 4. Import check Python
echo "# 4. Import check Python"

PY=python3
command -v python3 &>/dev/null || PY=python

if $PY -c "import phoenix_reflex; import phoenix_reflex_agent; print('ok')" 2>/dev/null; then
    ok "import phoenix_reflex + phoenix_reflex_agent OK"
else
    fail "Import error - revisa dependencias y PYTHONPATH"
fi

sep

# 5. Tests
echo "# 5. Tests"

if [ -d "tests" ] && ls tests/test_*.py 2>/dev/null | grep -q .; then
    count=$(ls tests/test_*.py 2>/dev/null | wc -l)
    if $PY -m pytest tests/ --tb=short -q 2>/dev/null; then
        ok "Tests verdes ($count archivos de test)"
    else
        fail "Tests en rojo (ejecuta: pytest tests/ -v)"
    fi
else
    warn "Sin archivos de test aun en tests/ (normal para este proyecto)"
fi

sep

# 6. Variables de entorno
echo "# 6. Variables de entorno"

if [ -f ".env" ]; then
    ok ".env existe"
elif [ -f ".env.example" ]; then
    warn ".env no existe (usa .env.example como plantilla)"
else
    fail "Ni .env ni .env.example encontrados"
fi

sep

# Resumen
echo "=== Resumen ==="
echo "  OK:   $nPass"
echo "  WARN: $nWarn"
echo "  FAIL: $nFail"

if [ $nFail -gt 0 ]; then
    echo "=== RESULTADO: FAIL ==="
    exit 1
else
    echo "=== RESULTADO: OK - listo para trabajar ==="
    exit 0
fi
