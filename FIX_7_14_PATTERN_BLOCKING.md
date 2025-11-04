# 🔧 Fix Crítico: Patrón 7/14 Bloqueando Reparto Inicial

## 🚨 Problema Identificado

### Síntomas:
```
Attempt 1: 14 shifts filled  ✅
Attempt 2: 0 shifts filled   ❌ "No fills, will try with relaxation"
Attempt 3: 0 shifts filled   ❌ "No fills, will try with relaxation"
...
Attempt 14: 0 shifts filled  ❌ "No fills possible"

Resultado final: 14/62 shifts (22.5%)
```

### Causa Raíz:

El patrón 7/14 en modo estricto era **ABSOLUTO** (blocking), lo que causaba:

1. **Intento 1:** Cada trabajador recibe 1 turno inicial
   - Worker_1: Jueves 1 de enero
   - Worker_9: Lunes 12 de enero  
   - Worker_11: Martes 13 de enero
   - etc.

2. **Intento 2+:** TODOS los intentos de asignación bloqueados:
   ```
   STRICT: Worker Worker_1 blocked by 7/14 pattern on 2026-01-08
   STRICT: Worker Worker_1 blocked by 7/14 pattern on 2026-01-15
   STRICT: Worker Worker_9 blocked by 7/14 pattern on 2026-01-19
   STRICT: Worker Worker_11 blocked by 7/14 pattern on 2026-01-20
   ```

3. **Efecto dominó:** 
   - Worker asignado a jueves 1 → bloqueado para jueves 8, 15, 22, 29
   - Worker asignado a lunes 12 → bloqueado para lunes 19, 26, etc.
   - Con 14 workers y días Mon-Thu → casi imposible llenar schedule

### Por Qué Era Tan Restrictivo:

```
Trabajador de Lunes-Jueves:
- Target: 55 turnos
- Mes tiene 4-5 lunes, 4-5 martes, etc.
- Si trabaja Lunes 5 → NO puede trabajar Lunes 12, 19, 26

Resultado: Solo puede trabajar 1 lunes al mes = 12 lunes/año
Pero necesita 55 turnos = 55/12 ≈ 4.5 turnos/mes

MATEMÁTICAMENTE IMPOSIBLE satisfacer target con patrón 7/14 absoluto
```

---

## ✅ Solución Implementada

### Cambio en `schedule_builder.py`:

**ANTES (patrón 7/14 absoluto):**
```python
# STRICT MODE: NEVER allow 7/14 pattern violation
if self.use_strict_mode:
    logging.debug(f"STRICT: Worker {worker_id} blocked by 7/14 pattern")
    return False  # BLOQUEO ABSOLUTO
```

**DESPUÉS (patrón 7/14 con excepción por déficit):**
```python
# STRICT MODE: Allow violations if worker has significant deficit
if self.use_strict_mode:
    # Allow 7/14 violation if worker needs at least 3 more shifts
    if target_deficit >= 3:
        logging.debug(f"STRICT: Worker {worker_id} allowed 7/14 pattern override - needs {target_deficit} more shifts")
        continue  # PERMITE CON DÉFICIT
    else:
        logging.debug(f"STRICT: Worker {worker_id} blocked by 7/14 pattern")
        return False  # Solo bloquea si déficit < 3
```

### Rationale:

1. **Déficit ≥ 3 turnos** indica que el worker está significativamente por debajo de su target
2. **Prioridad:** Llenar schedule > Respetar patrón 7/14
3. **Iteración posterior** puede redistribuir para minimizar violations
4. **Sin esta excepción:** Sistema completamente bloqueado (22.5% coverage)

---

## 📊 Comparación de Modos

### Modo Estricto (Fase Inicial):
```python
# Permite 7/14 si worker necesita 3+ turnos más
if target_deficit >= 3:
    allow_7_14_violation = True

# Ejemplo:
Worker con 1 turno asignado, target 55:
- Déficit = 55 - 1 = 54 ≥ 3
- Permite violación de 7/14 ✅
- Puede trabajar Lunes 5, 12, 19, 26 (mismo día semana)
```

### Modo Relajado (Fase Iteración):
```python
# Permite 7/14 si déficit >10% del target
deficit_percentage = (target_deficit / target_shifts) × 100
if deficit_percentage > 10:
    allow_7_14_violation = True

# Ejemplo:
Worker con 50 turnos asignados, target 55:
- Déficit = 55 - 50 = 5
- Porcentaje = (5/55) × 100 = 9.1% < 10%
- NO permite violación ❌
- Debe respetar patrón 7/14
```

### Diferencia Clave:

| Aspecto | Modo Estricto | Modo Relajado |
|---------|---------------|---------------|
| **Threshold** | ≥3 turnos (absoluto) | >10% del target (relativo) |
| **Objetivo** | Llenar schedule inicialmente | Optimizar distribución |
| **Ejemplo 1** | 1/55 → 54 déficit → Permite ✅ | 1/55 → 98% déficit → Permite ✅ |
| **Ejemplo 2** | 52/55 → 3 déficit → Permite ✅ | 52/55 → 5.5% déficit → NO permite ❌ |
| **Ejemplo 3** | 54/55 → 1 déficit → NO permite ❌ | 54/55 → 1.8% déficit → NO permite ❌ |

---

## 🎯 Resultados Esperados

### Con el Fix:

#### Intento 1:
- ✅ 14 shifts asignados (1 por trabajador)

#### Intento 2-14:
- ✅ Continúa llenando shifts
- ✅ Workers con déficit ≥3 pueden violar 7/14
- ✅ Progreso gradual hacia 90-95% coverage

#### Resultado Final Fase Inicial:
```
Empty shifts: 48 → 5-10
Shifts asignados: 14 → 52-57 (90-95%)
Violations patrón 7/14: 10-20 (aceptable)
Violations target: 5-10 (aceptable)
```

### Sin el Fix (problema original):
```
Empty shifts: 48 (sin cambios)
Shifts asignados: 14 (solo 22.5%)
Violations: Ninguna (pero schedule incompleto)
```

---

## 🔍 Análisis del Trade-off

### ¿Por qué es aceptable este cambio?

1. **Prioridad correcta:**
   - Mejor: 95% coverage con 15 violations 7/14
   - Peor: 22% coverage con 0 violations 7/14

2. **Violations son recuperables:**
   - Fase iterativa puede redistribuir turnos
   - Objetivo final: <5 violations totales
   - Patrón 7/14 es "soft constraint" (no legal/safety)

3. **Alternative es peor:**
   - Sin fix: schedule 78% vacío
   - Con fix: schedule 5-10% vacío, violations manejables

4. **Matemática del problema:**
   - 14 workers, 62 shifts, ~31 días
   - Sin flexibilidad 7/14: imposible satisfacer targets
   - Con flexibilidad: posible optimizar luego

---

## 📝 Notas de Implementación

### Threshold de 3 turnos:

**¿Por qué 3 y no 5 o 10?**

- **3 turnos** = ~5-6% del target típico (55)
- Suficientemente bajo para evitar abusos
- Suficientemente alto para permitir progreso inicial
- Workers cerca de target (52/55, 53/55, 54/55) respetan patrón

### ¿Cuándo se bloquea aún en modo estricto?

```python
Worker con 53/55 turnos:
- Déficit = 2 < 3
- Bloqueo por 7/14 ✅
- Debe buscar otros días disponibles

Worker con 52/55 turnos:
- Déficit = 3 ≥ 3
- Permite 7/14 ✅
- Puede llenar con mismo día semana
```

---

## 🧪 Testing

### Verificar que funciona:

```bash
# Ejecutar scheduler
python main.py

# Buscar en logs:
grep "STRICT: Worker.*allowed 7/14 pattern override" logs.txt

# Ejemplo esperado:
STRICT: Worker Worker_1 allowed 7/14 pattern override - needs 54 more shifts
STRICT: Worker Worker_9 allowed 7/14 pattern override - needs 54 more shifts
```

### Verificar múltiples intentos exitosos:

```bash
# Buscar progreso en intentos
grep "Attempt.*Filled.*shifts" logs.txt

# Esperado:
Attempt 1: Filled 14 shifts  ✅
Attempt 2: Filled 8 shifts   ✅
Attempt 3: Filled 6 shifts   ✅
...
Attempt 14: Filled 2 shifts  ✅
```

### Verificar coverage final:

```bash
# Buscar resultado de fase inicial
grep "Best attempt" logs.txt

# Esperado:
✅ Best attempt: X/20 with 52-57 shifts and 15-25 violations
```

---

## 🚀 Próximos Pasos

1. **Testing con dataset real** → Verificar 90-95% coverage
2. **Analizar violations finales** → Confirmar <5 después de iteración
3. **Ajustar threshold si necesario** → Puede cambiar 3 a 4-5 si hay abusos
4. **Documentar resultados** → Comparar before/after

---

## 📞 Si Surge Problema

### Síntoma: Muchas violations de 7/14 (>30)

**Ajustar threshold:**
```python
# Cambiar de 3 a 5
if target_deficit >= 5:  # Más estricto
    allow_7_14_violation = True
```

### Síntoma: Aún no llena suficiente (50-60%)

**Reducir threshold:**
```python
# Cambiar de 3 a 2
if target_deficit >= 2:  # Más permisivo
    allow_7_14_violation = True
```

### Síntoma: Violations no se limpian en iteración

**Problema diferente:** Revisar modo relajado
- Verificar threshold 10% funciona correctamente
- Puede necesitar ajustar iterative_optimizer

---

## ✅ Conclusión

**Fix crítico implementado:** Patrón 7/14 ahora permite excepciones en modo estricto cuando worker tiene déficit ≥3 turnos.

**Justificación:** Sin este cambio, sistema completamente bloqueado (22.5% coverage). Con cambio, se espera 90-95% coverage inicial.

**Trade-off aceptable:** 15-25 violations recuperables vs 78% schedule vacío.

**Commit:** `f38d004` - "fix: Allow 7/14 pattern violations in strict mode with deficit ≥3"
