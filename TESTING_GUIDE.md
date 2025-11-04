# 🧪 Guía de Testing - Sistema Dual-Mode

## 📋 Checklist Pre-Testing

Antes de ejecutar, verificar:

- [ ] Python environment configurado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Datos de entrada preparados (workers, shifts, dates)
- [ ] Configuración en `scheduler_config.py` correcta
- [ ] Git en commit `8267b2f` o posterior

---

## 🚀 Ejecución del Test

### Comando básico:
```bash
python main.py
```

### Con logging detallado:
```bash
python main.py --verbose
```

### Con archivo de configuración específico:
```bash
python main.py --config my_config.json
```

---

## 🔍 Qué Observar en los Logs

### 1. Activación de Modo Estricto
Buscar al inicio:
```
🔒 STRICT MODE activated for initial distribution phase
   - Target limit: +10% (adjusted by work_percentage)
   - Gap reduction: NOT allowed
   - Pattern 7/14: ABSOLUTELY PROHIBITED
```

**Verificar:**
- ✅ Aparece al inicio de fase de reparto
- ✅ Antes de los múltiples intentos de distribución

### 2. Múltiples Intentos Iniciales
Buscar:
```
🔄 PHASE 1: Multiple initial distribution attempts (strict mode)
   Attempting 20 initial distributions...
   
   Attempt 1/20: 512 shifts assigned, 28 violations
   Attempt 2/20: 518 shifts assigned, 25 violations
   ...
   ✅ Best attempt: 15/20 with 522 shifts and 23 violations
```

**Verificar:**
- ✅ Se realizan múltiples intentos (10-60)
- ✅ Cada intento muestra shifts asignados y violations
- ✅ Se selecciona el mejor intento
- ✅ Violations en rango 15-30

### 3. Activación de Modo Relajado
Buscar:
```
🔓 RELAXED MODE activated for iterative optimization phase
   - Target limit: +10% (NEVER increases above this)
   - Gap reduction: -1 ONLY if deficit ≥3 shifts
   - Pattern 7/14: Allowed if deficit >10% of target
   - Balance tolerance: ±10% for guardias/mes, weekends
```

**Verificar:**
- ✅ Aparece después de fase inicial
- ✅ Antes de comenzar iteraciones
- ✅ Parámetros correctos (+10%, gap-1, ±10%)

### 4. Iteraciones de Optimización
Buscar:
```
Iteration 1/50: 23 violations (target: 8, gap: 7, 7/14: 3, balance: 5)
Iteration 2/50: 20 violations (target: 7, gap: 6, 7/14: 2, balance: 5)
...
Iteration 15/50: 5 violations (target: 2, gap: 1, 7/14: 0, balance: 2)
```

**Verificar:**
- ✅ Se ejecutan 50 iteraciones (no se detiene prematuramente)
- ✅ Violations disminuyen progresivamente
- ✅ Desglose por tipo de violación
- ✅ Convergencia hacia <5 violations

### 5. Relajaciones Aplicadas
Buscar mensajes como:
```
⚠️ Gap reduced by 1 for worker W123 (deficit: 5 shifts)
⚠️ Pattern 7/14 override for worker W456 (deficit: 12% of target)
```

**Verificar:**
- ✅ Gap reduction solo con déficit ≥3
- ✅ Patrón 7/14 solo con déficit >10%
- ✅ No aparecen en fase estricta

### 6. Violations Finales
Buscar al final:
```
📊 FINAL SCHEDULE SUMMARY:
   Total shifts assigned: 555/560 (99.1%)
   
   Violations:
   - Mandatory: 0 ✅
   - Incompatibilities: 0 ✅
   - Days off: 0 ✅
   - Target deviations: 2 ⚠️
   - Gap violations: 0 ✅
   - Pattern 7/14: 1 ⚠️
   - Balance (monthly): 1 ⚠️
   - Balance (weekend): 0 ✅
   
   Total violations: 4 ✅
```

**Verificar:**
- ✅ Mandatory = 0
- ✅ Incompatibilities = 0
- ✅ Days off = 0
- ✅ Total violations ≤ 5
- ✅ >95% shifts asignados

---

## ✅ Criterios de Éxito

### Obligatorios (DEBE cumplirse):
1. **Violations críticas = 0:**
   - Mandatory shifts = 0
   - Incompatibilidades = 0
   - Days off = 0

2. **Sistema completa todas las iteraciones:**
   - No se detiene prematuramente
   - Ejecuta las 50 iteraciones configuradas

3. **Respeta límite de target:**
   - Ningún worker excede +10% de su target
   - Ajustado por work_percentage

### Deseables (Objetivo):
1. **Total violations ≤ 5** al final
2. **>95% de shifts asignados**
3. **Pattern 7/14 violations ≤ 3**
4. **Balance violations ≤ 5**

### Aceptables (Mínimo):
1. **Total violations ≤ 10** al final
2. **>90% de shifts asignados**
3. **Mejora progresiva** en iteraciones

---

## 🔴 Red Flags (Problemas a reportar)

### Críticos:
- ❌ Mandatory violations > 0
- ❌ Incompatibility violations > 0
- ❌ Days off violations > 0
- ❌ Workers con +11% o más sobre target
- ❌ Sistema se detiene antes de 50 iteraciones

### Importantes:
- ⚠️ Violations no disminuyen después de 20 iteraciones
- ⚠️ Pattern 7/14 violations con déficit <10%
- ⚠️ Gap reduction sin déficit ≥3
- ⚠️ Total violations >15 al final

### Menores:
- ⚠️ Balance violations >5
- ⚠️ <90% shifts asignados
- ⚠️ Intentos iniciales con >35 violations

---

## 📊 Análisis de Resultados

### 1. Exportar schedule a JSON:
```python
python main.py --export schedule.json
```

### 2. Verificar distribución de workers:
```python
import json

with open('schedule.json') as f:
    data = json.load(f)

for worker in data['workers']:
    target = worker['target_shifts']
    current = worker['assigned_shifts']
    percentage = (current / target - 1) * 100
    
    print(f"{worker['id']}: {current}/{target} ({percentage:+.1f}%)")
```

**Verificar:**
- ✅ Todos los workers ≤ +10%
- ✅ Déficits significativos (>20%) reducidos
- ✅ Distribución equilibrada

### 3. Verificar gaps:
```python
for worker in data['workers']:
    shifts = sorted(worker['assignments'])
    gaps = [shifts[i+1] - shifts[i] for i in range(len(shifts)-1)]
    
    min_gap = min(gaps) if gaps else float('inf')
    expected_gap = worker['gap_between_shifts']
    
    print(f"{worker['id']}: min_gap={min_gap}, expected={expected_gap}")
```

**Verificar:**
- ✅ min_gap >= expected_gap - 1
- ✅ Gap-1 solo en workers con déficit alto

### 4. Verificar patrón 7/14:
```python
from datetime import datetime, timedelta

for worker in data['workers']:
    dates = [datetime.fromisoformat(d) for d in worker['assignment_dates']]
    
    for i, d1 in enumerate(dates):
        weekday = d1.weekday()
        if weekday <= 3:  # Lun-Jue
            for d2 in dates[i+1:]:
                diff = (d2 - d1).days
                if diff in [7, 14] and d2.weekday() == weekday:
                    deficit_pct = worker['deficit_percentage']
                    print(f"⚠️ 7/14 violation: {worker['id']} on {d1} and {d2} (deficit: {deficit_pct}%)")
```

**Verificar:**
- ✅ Violations solo con déficit >10%
- ✅ No hay violations en fase estricta

---

## 🐛 Troubleshooting

### Problema: Sistema se detiene prematuramente
**Solución:**
```python
# Verificar en iterative_optimizer.py línea ~45
# Debe ser:
if violations == 0:  # Solo detener si perfecto
    break
```

### Problema: Target excede +10%
**Solución:**
```python
# Verificar en schedule_builder.py línea ~940
# Debe ser:
tolerance = 0.10  # FIJO, no progresivo
```

### Problema: Gap reduction sin déficit
**Solución:**
```python
# Verificar en schedule_builder.py línea ~1020
# Debe tener:
if deficit >= 3:  # Requiere déficit ≥3
    min_gap = base_gap - 1
```

### Problema: Violations no disminuyen
**Causas posibles:**
1. Dataset muy restrictivo (muchos mandatory, incomp)
2. Target muy alto para días disponibles
3. Gap mínimo muy grande (reduce combinaciones)
4. Patrón 7/14 demasiado restrictivo para workers de lunes-jueves

**Solución:**
- Revisar configuración de constraints
- Verificar que work_percentage esté correcto
- Considerar ajustar target de workers problemáticos

---

## 📈 Comparación Antes/Después

Para evaluar la mejora del sistema dual-mode:

### Métricas clave:
1. **Violations críticas:** Antes vs Después
2. **Total violations:** Antes vs Después
3. **% shifts asignados:** Antes vs Después
4. **Workers con déficit >20%:** Antes vs Después
5. **Tiempo de ejecución:** Antes vs Después

### Ejemplo de reporte:
```
MEJORA CON SISTEMA DUAL-MODE:

Violations críticas:
- Antes: 3-8 violations
- Después: 0 violations ✅

Total violations:
- Antes: 29-33 violations
- Después: 4-6 violations ✅

Workers con déficit >20%:
- Antes: 5-8 workers
- Después: 0 workers ✅

% Shifts asignados:
- Antes: 88-92%
- Después: 96-99% ✅

Tiempo:
- Antes: ~45 segundos
- Después: ~60 segundos (aceptable)
```

---

## 📞 Reporte de Issues

Si encuentras problemas, incluye:

1. **Logs completos** (especialmente fase inicial y primera iteración)
2. **Configuración usada** (scheduler_config.py)
3. **Estadísticas de violations** por tipo
4. **Distribución de workers** (target vs asignado)
5. **Commit hash** (git rev-parse HEAD)

---

## ✅ Checklist Post-Testing

- [ ] Violations críticas = 0
- [ ] Total violations ≤ 5
- [ ] Se ejecutan 50 iteraciones
- [ ] Target ≤ +10% para todos
- [ ] Logs muestran modo estricto → relajado
- [ ] Relajaciones solo con déficit suficiente
- [ ] Distribución equilibrada
- [ ] >95% shifts asignados
