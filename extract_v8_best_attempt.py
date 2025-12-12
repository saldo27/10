#!/usr/bin/env python3
"""
Extraer asignaciones y verificación de tolerancia del mejor intento v8
"""

import re
from collections import defaultdict

log_file = "test_120days_v8.log"

# Configuración workers
workers_config = {
    1: {'target': 18, 'pct': 100}, 2: {'target': 18, 'pct': 100}, 3: {'target': 18, 'pct': 100},
    4: {'target': 18, 'pct': 100}, 5: {'target': 18, 'pct': 100}, 6: {'target': 18, 'pct': 100},
    7: {'target': 18, 'pct': 100}, 8: {'target': 18, 'pct': 100}, 9: {'target': 18, 'pct': 100},
    10: {'target': 18, 'pct': 100}, 11: {'target': 18, 'pct': 100}, 12: {'target': 18, 'pct': 100},
    13: {'target': 18, 'pct': 100}, 14: {'target': 18, 'pct': 100}, 15: {'target': 18, 'pct': 100},
    16: {'target': 18, 'pct': 100}, 17: {'target': 18, 'pct': 100}, 18: {'target': 18, 'pct': 100},
    19: {'target': 18, 'pct': 100}, 20: {'target': 18, 'pct': 100}, 21: {'target': 18, 'pct': 100},
    22: {'target': 14, 'pct': 80}, 23: {'target': 14, 'pct': 80}, 24: {'target': 14, 'pct': 80},
    25: {'target': 12, 'pct': 66}, 26: {'target': 12, 'pct': 66},
    27: {'target': 10, 'pct': 60},
    28: {'target': 9, 'pct': 50}, 29: {'target': 9, 'pct': 50}
}

print("=" * 90)
print("EXTRACCIÓN MEJOR INTENTO V8 - #24")
print("=" * 90)

with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Buscar bloque del intento 24
pattern = r'Attempt 24/40.*?(?=Attempt 25/40|$)'
match = re.search(pattern, content, re.DOTALL)

if not match:
    print("❌ No se encontró el intento 24")
    exit()

attempt_24 = match.group(0)

# Buscar asignaciones de workers en este intento
# Patrón: "Worker X assignments: Y" o "Worker X: Y shifts"
assignments = {}
patterns = [
    r'Worker (\d+): (\d+) shifts',
    r'Worker (\d+) assignments: (\d+)',
    r'Worker (\d+).*?asignados: (\d+)'
]

for pattern in patterns:
    matches = re.finditer(pattern, attempt_24)
    for m in matches:
        worker_id = int(m.group(1))
        shifts = int(m.group(2))
        if worker_id not in assignments:
            assignments[worker_id] = shifts

# Si no encontramos asignaciones en ese formato, buscar en el resultado final
if not assignments:
    # Buscar en la sección de resultados
    result_pattern = r'📊 Attempt 24 Results:.*?(?=INFO:|$)'
    result_match = re.search(result_pattern, attempt_24, re.DOTALL)
    if result_match:
        result_section = result_match.group(0)
        # Intentar otros patrones
        for pattern in [r'W(\d+):(\d+)', r'(\d+):(\d+) turnos']:
            matches = re.finditer(pattern, result_section)
            for m in matches:
                worker_id = int(m.group(1))
                shifts = int(m.group(2))
                if 1 <= worker_id <= 29:
                    assignments[worker_id] = shifts

# Si aún no hay asignaciones, contar desde el schedule JSON del intento
if not assignments:
    print("⚠️  No se encontraron asignaciones explícitas en logs")
    print("    Buscando en estructura del schedule...")
    
    # Buscar en formato schedule JSON
    schedule_pattern = r'"worker_id":\s*(\d+)'
    matches = re.finditer(schedule_pattern, attempt_24)
    worker_counts = defaultdict(int)
    for m in matches:
        worker_id = int(m.group(1))
        if 1 <= worker_id <= 29:
            worker_counts[worker_id] += 1
    
    if worker_counts:
        assignments = dict(worker_counts)

if not assignments:
    print("❌ No se pudieron extraer asignaciones del intento 24")
    print("\n🔍 Buscando resumen de balance en el log...")
    
    # Último recurso: buscar cualquier reporte de balance cerca del intento 24
    balance_pattern = r'Worker (\d+).*?(\d+)/(\d+).*?([-+]?\d+\.?\d*)%'
    matches = re.finditer(balance_pattern, attempt_24)
    
    found_any = False
    for m in matches:
        worker_id = int(m.group(1))
        actual = int(m.group(2))
        target = int(m.group(3))
        deviation = float(m.group(4))
        
        if not found_any:
            print(f"\n{'Worker':<10} {'Target':<10} {'Actual':<10} {'Deviation':<15} {'Max +12%':<12} {'Status':<10}")
            print("─" * 85)
            found_any = True
        
        config = workers_config.get(worker_id, {'target': target, 'pct': 100})
        adjusted_target = int(config['target'] * config['pct'] / 100)
        max_allowed = int(adjusted_target * 1.12 + 0.5)
        
        status = "✅ OK" if actual <= max_allowed else f"❌ EXCEDE +{((actual - adjusted_target) / adjusted_target * 100):.1f}%"
        
        print(f"Worker {worker_id:<4} {adjusted_target:<10} {actual:<10} {deviation:>+6.2f}% "
              f"{max_allowed:<12} {status}")
    
    if not found_any:
        print("❌ No se encontró información de balance")
    exit()

# Tenemos asignaciones, procesar
print(f"\n✅ Asignaciones extraídas: {len(assignments)} workers")
print(f"\n{'Worker':<10} {'Target':<10} {'Actual':<10} {'Deviation':<15} {'Max +12%':<12} {'Status':<10}")
print("─" * 85)

violations = []
ok_count = 0
max_excess_pct = 0
max_excess_worker = None

for worker_id in sorted(assignments.keys()):
    config = workers_config.get(worker_id)
    if not config:
        continue
    
    target = config['target']
    pct = config['pct']
    adjusted_target = int(target * pct / 100)
    actual = assignments[worker_id]
    
    max_allowed = int(adjusted_target * 1.12 + 0.5)
    deviation_pct = ((actual - adjusted_target) / adjusted_target * 100) if adjusted_target > 0 else 0
    
    if actual > max_allowed:
        status = f"❌ EXCEDE"
        excess_pct = ((actual - adjusted_target) / adjusted_target * 100)
        violations.append({
            'worker': worker_id,
            'target': adjusted_target,
            'actual': actual,
            'excess_pct': excess_pct
        })
        if excess_pct > max_excess_pct:
            max_excess_pct = excess_pct
            max_excess_worker = worker_id
    else:
        status = "✅ OK"
        ok_count += 1
    
    print(f"Worker {worker_id:<4} {adjusted_target:<10} {actual:<10} {deviation_pct:>+6.2f}% "
          f"{max_allowed:<12} {status}")

print("\n" + "=" * 90)
print("VERIFICACIÓN LÍMITE +12%")
print("=" * 90)

if violations:
    print(f"❌ VIOLACIONES DETECTADAS: {len(violations)}")
    print(f"\n   Peor caso: Worker {max_excess_worker} con +{max_excess_pct:.1f}% (debería ser máx +12%)")
    print(f"\n   Esto indica que el límite +12% NO se está respetando en el intento 24")
    print(f"   (Puede ser que el intento 24 no sea el mejor después de optimización)")
else:
    print(f"✅ TODOS LOS WORKERS DENTRO DEL LÍMITE +12%")
    print(f"\n   Workers verificados: {ok_count}/{len(assignments)}")
    print(f"   Máximo exceso detectado: +{max_excess_pct:.1f}%")
    print(f"\n   🎉 El límite +12% se está respetando correctamente en v8")

print("=" * 90)
