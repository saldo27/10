# ⚙️ Parámetros del Sistema - Referencia Rápida

## 🔒 MODO ESTRICTO (Reparto Inicial)

### Restricciones Absolutas (NUNCA se violan):
```
✅ Mandatory shifts       → NUNCA modificados
✅ Incompatibilidades     → SIEMPRE bloqueadas  
✅ Days off               → NUNCA asignados
✅ Target máximo          → +10% del objetivo (ajustado por % jornada)
✅ Gap mínimo             → Sin reducción
✅ Patrón 7/14            → PROHIBIDO absolutamente
✅ Balance mensual        → ±1 turno máximo
✅ Balance weekend        → ±1 fin de semana máximo
```

### Fórmulas:
```python
# Target permitido
max_allowed_shifts = target_shifts × (work_percentage / 100) × 1.10

# Gap mínimo
min_gap = gap_between_shifts  # Sin reducción

# Balance mensual
expected_monthly = (target / 12) × days_in_month
tolerance = ±1 turno

# Balance weekend  
expected_weekends = total_weekends / num_workers
tolerance = ±1 weekend
```

---

## 🔓 MODO RELAJADO (Optimización Iterativa)

### Límites de Relajación:
```
✅ Target máximo          → +10% (IGUAL que estricto, NO aumenta)
✅ Gap mínimo             → Permite gap-1 SOLAMENTE (si déficit ≥3 guardias)
✅ Patrón 7/14            → Permite si déficit >10% del target
✅ Balance mensual        → Tolerancia ±10%
✅ Balance weekend        → Tolerancia ±10%
```

### Restricciones que NUNCA se relajan:
```
❌ Mandatory shifts       → NUNCA modificados
❌ Incompatibilidades     → SIEMPRE bloqueadas
❌ Days off               → NUNCA asignados
```

### Fórmulas:
```python
# Target: SIEMPRE +10% (sin cambios)
max_allowed_shifts = target_shifts × (work_percentage / 100) × 1.10

# Gap: Permite reducción -1 con déficit
current_shifts = len(worker_assignments)
deficit = target_shifts - current_shifts
if deficit >= 3:
    min_gap = gap_between_shifts - 1  # SOLO -1
else:
    min_gap = gap_between_shifts  # Normal

# Patrón 7/14: Permite con déficit crítico
deficit_percentage = (deficit / target_shifts) × 100
if deficit_percentage > 10:  # >10% del target
    allow_7_14_violation = True

# Balance mensual: Tolerancia ±10%
expected_monthly = (target / 12) × days_in_month
tolerance = expected_monthly × 0.10

# Balance weekend: Tolerancia ±10%
expected_weekends = total_weekends / num_workers  
tolerance = expected_weekends × 0.10
```

---

## 📊 Comparativa Rápida

| Parámetro | Estricto | Relajado | Notas |
|-----------|----------|----------|-------|
| Target | +10% | +10% | **NO aumenta** |
| Gap | Normal | gap-1 | Solo si déficit ≥3 |
| 7/14 | ❌ | ✅ | Solo si déficit >10% |
| Mensual | ±1 | ±10% | Porcentaje |
| Weekend | ±1 | ±10% | Porcentaje |
| Mandatory | ❌ | ❌ | **NUNCA relaja** |
| Incomp | ❌ | ❌ | **NUNCA relaja** |
| Days off | ❌ | ❌ | **NUNCA relaja** |

---

## 🎯 Thresholds Clave

```python
# Target
TARGET_TOLERANCE = 0.10  # +10% SIEMPRE

# Gap reduction
GAP_REDUCTION = -1              # SOLO -1
GAP_DEFICIT_THRESHOLD = 3       # Requiere déficit ≥3 guardias

# Patrón 7/14
PATTERN_7_14_DEFICIT_PCT = 10   # Permite si déficit >10%

# Balance
BALANCE_TOLERANCE = 0.10        # ±10%
```

---

## 🔧 Configuración en Código

### Activar modo estricto:
```python
scheduler.schedule_builder.enable_strict_mode()
```

### Activar modo relajado:
```python
scheduler.schedule_builder.enable_relaxed_mode()
```

### Verificar modo actual:
```python
is_strict = scheduler.schedule_builder.is_strict_mode()
```

---

## 📈 Resultados Esperados

### Fase Inicial (Estricto):
- ✅ 90-95% shifts asignados
- ✅ 0 violations críticas (mandatory, incomp, days off)
- ✅ 0 violations patrón 7/14
- ✅ 15-25 violations balance

### Fase Iteración (Relajado):
- ✅ 98-100% shifts asignados  
- ✅ 0 violations críticas
- ✅ 0-3 violations patrón 7/14 (solo con déficit >10%)
- ✅ 0-5 violations balance

---

## 📝 Notas Importantes

1. **Target +10% es LÍMITE MÁXIMO:**
   - NO aumenta en modo relajado
   - Se mantiene en +10% en ambos modos
   - Ajustado por work_percentage

2. **Gap reduction es LIMITADA:**
   - Solo permite -1 (no -2, -3, etc.)
   - Requiere déficit ≥3 guardias
   - Solo en modo relajado

3. **Patrón 7/14 usa PORCENTAJE:**
   - Déficit >10% del target
   - No es valor absoluto
   - Ejemplo: target=55 → déficit >5.5 guardias

4. **Balance usa TOLERANCIA PORCENTUAL:**
   - ±10% de la distribución esperada
   - Aplica a guardias/mes y weekends
   - Más flexible que ±1 absoluto

---

## 🚀 Para Testing

```python
# Verificar que target NO excede +10%
for worker in workers:
    assert worker.current_shifts <= worker.target * 1.10

# Verificar gap mínimo (con posible -1)
min_allowed = base_gap - 1 if deficit >= 3 else base_gap
assert all_gaps >= min_allowed

# Verificar patrón 7/14 solo con déficit >10%
if deficit_pct > 10:
    # Puede violar 7/14
else:
    # NO debe violar 7/14

# Verificar balance ±10%
expected = calculate_expected()
assert abs(actual - expected) <= expected * 0.10
```
