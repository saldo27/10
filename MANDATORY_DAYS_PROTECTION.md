# Protección de Mandatory Days - Cambios Implementados

## Fecha: 24 de Octubre de 2025

## Objetivo
Asegurar que los `mandatory_days` (días obligatorios) de los trabajadores sean **completamente inamovibles** y no puedan ser modificados, eliminados o intercambiados bajo ninguna circunstancia.

## Cambios Realizados

### 1. **scheduler.py - validate_and_fix_final_schedule()**
**Ubicación:** Líneas ~1800-1950

**Problema Detectado:**
- El validador final eliminaba turnos que violaban restricciones SIN verificar si eran mandatory_days
- Esto podía resultar en la eliminación de asignaciones obligatorias

**Solución Implementada:**

#### 1.1 Protección contra incompatibilidades
```python
# ANTES: Eliminaba el trabajador con más asignaciones
worker_to_remove = worker1_id if w1_count >= w2_count else worker2_id

# AHORA: Verifica si alguno tiene mandatory assignment
worker1_is_mandatory = self.schedule_builder._is_mandatory(worker1_id, date)
worker2_is_mandatory = self.schedule_builder._is_mandatory(worker2_id, date)

# Si ambos son mandatory -> ERROR DE CONFIGURACIÓN (no se elimina ninguno)
if worker1_is_mandatory and worker2_is_mandatory:
    logging.error("Both workers have mandatory assignments but are incompatible - configuration error")
    continue  # NO elimina ninguno

# Si uno es mandatory -> elimina el otro
if worker1_is_mandatory:
    worker_to_remove = worker2_id
elif worker2_is_mandatory:
    worker_to_remove = worker1_id
```

#### 1.2 Protección contra violaciones de gap (días mínimos entre turnos)
```python
# ANTES: Eliminaba la asignación posterior (date2)
date_to_remove = date2

# AHORA: Verifica mandatory assignments
date1_is_mandatory = self.schedule_builder._is_mandatory(worker_id, date1)
date2_is_mandatory = self.schedule_builder._is_mandatory(worker_id, date2)

# Si ambos son mandatory -> ERROR DE CONFIGURACIÓN
if date1_is_mandatory and date2_is_mandatory:
    logging.error("Both dates are mandatory but violate gap - configuration error")
    continue  # NO elimina ninguno

# Prioriza mantener el mandatory
if date2_is_mandatory:
    date_to_remove = date1
elif date1_is_mandatory:
    date_to_remove = date2
```

---

### 2. **scheduler.py - _fix_constraint_violations()**
**Ubicación:** Líneas ~1310-1380

**Problema Detectado:**
- Similar al validador final, este método eliminaba turnos sin verificar mandatory_days

**Solución Implementada:**

#### 2.1 Protección para violaciones de gap/pattern
```python
# Verifica mandatory antes de eliminar
date1_is_mandatory = self.schedule_builder._is_mandatory(worker_id, date1)
date2_is_mandatory = self.schedule_builder._is_mandatory(worker_id, date2)

if date1_is_mandatory and date2_is_mandatory:
    logging.error("Cannot fix: both dates are mandatory")
    continue

# Decide qué fecha eliminar basándose en mandatory status
if date2_is_mandatory:
    date_to_unassign = date1
elif date1_is_mandatory:
    date_to_unassign = date2
```

#### 2.2 Protección para incompatibilidades
```python
# Verifica mandatory antes de decidir qué trabajador eliminar
worker_is_mandatory = self.schedule_builder._is_mandatory(worker_id, date)
incompatible_is_mandatory = self.schedule_builder._is_mandatory(incompatible_id, date)

if worker_is_mandatory and incompatible_is_mandatory:
    logging.error("Cannot fix: both workers have mandatory assignments")
    continue

# Prioriza mantener el trabajador con mandatory
if worker_is_mandatory:
    worker_to_unassign = incompatible_id
elif incompatible_is_mandatory:
    worker_to_unassign = worker_id
```

---

### 3. **adjustment_utils.py - _can_worker_release_shift()**
**Ubicación:** Líneas ~166-200

**Problema Detectado:**
- Verificación existente pero no robusta (usaba parsing manual en lugar de DateTimeUtils)
- En caso de error, permitía liberar el turno (fail-unsafe)

**Solución Implementada:**
```python
# MEJORADO: Usa DateTimeUtils para consistencia
from utilities import DateTimeUtils
date_utils = DateTimeUtils()
mandatory_dates = date_utils.parse_dates(mandatory_str)

# Verifica si la fecha es mandatory
for mandatory_date in mandatory_dates:
    if mandatory_date.date() == date.date():
        logging.info(f"Worker {worker_id} CANNOT release - MANDATORY assignment")
        return False  # NO puede liberar

# CRÍTICO: En caso de error, NO permite liberar (fail-safe)
except Exception as e:
    logging.error(f"Error parsing mandatory_days: {e}")
    return False  # Fail-safe: asume que NO puede liberar
```

---

### 4. **incremental_updater.py - unassign_worker_from_shift()**
**Ubicación:** Líneas ~130-145

**Problema Detectado:**
- Permitía desasignar cualquier trabajador sin verificar mandatory_days

**Solución Implementada:**
```python
# NUEVO: Verifica mandatory ANTES de desasignar
if hasattr(self.scheduler, 'schedule_builder') and self.scheduler.schedule_builder:
    if self.scheduler.schedule_builder._is_mandatory(current_worker, shift_date):
        logging.warning(f"Cannot unassign - MANDATORY assignment")
        return UpdateResult(
            False, 
            f"Cannot unassign: Worker {current_worker} has a MANDATORY assignment on {shift_date}"
        )
```

---

### 5. **incremental_updater.py - _check_swap_constraints()**
**Ubicación:** Líneas ~393-420

**Problema Detectado:**
- Los swaps (intercambios) podían mover mandatory_days sin restricción

**Solución Implementada:**
```python
# NUEVO: Verifica mandatory PRIMERO antes de cualquier otra validación
if worker1:
    if self.scheduler.schedule_builder._is_mandatory(worker1, shift_date1):
        constraints_ok = False
        conflicts.append(f"Worker {worker1} has MANDATORY assignment - cannot swap")

if worker2:
    if self.scheduler.schedule_builder._is_mandatory(worker2, shift_date2):
        constraints_ok = False
        conflicts.append(f"Worker {worker2} has MANDATORY assignment - cannot swap")

# Si hay mandatory, detiene inmediatamente
if not constraints_ok:
    return UpdateResult(
        False, 
        "Cannot swap: one or more assignments are MANDATORY and cannot be moved",
        conflicts=conflicts
    )
```

---

## Resultado

### ✅ Protecciones Implementadas

1. **Validación Final**: Los mandatory_days nunca se eliminan durante la validación final
2. **Corrección de Violaciones**: No se eliminan mandatory_days al corregir violaciones de restricciones
3. **Ajustes Manuales**: No se pueden liberar (release) mandatory_days manualmente
4. **Desasignaciones**: No se pueden desasignar mandatory_days en tiempo real
5. **Intercambios (Swaps)**: No se pueden intercambiar mandatory_days con otros turnos

### ⚠️ Manejo de Errores de Configuración

Cuando se detectan conflictos de configuración (ej: dos trabajadores incompatibles ambos con mandatory el mismo día):
- Se registra un **ERROR** en los logs
- NO se elimina ninguna asignación mandatory
- Se informa al usuario que debe corregir los datos de configuración

### 📋 Logging Mejorado

Todos los casos donde se protegen mandatory_days ahora generan logs claros:
- `logging.info()` cuando se detecta y respeta un mandatory
- `logging.error()` cuando hay errores de configuración irresolubles
- Mensajes específicos indicando que la asignación es "MANDATORY" e "inamovible"

---

## Testing Recomendado

Para verificar que las protecciones funcionan correctamente:

1. ✅ Crear un horario con mandatory_days que violen restricciones de gap
2. ✅ Crear mandatory_days para trabajadores incompatibles en el mismo día
3. ✅ Intentar desasignar manualmente un mandatory_day
4. ✅ Intentar intercambiar un mandatory_day con otro turno
5. ✅ Verificar que los logs muestren claramente los errores de configuración

---

## Notas Importantes

- Los `mandatory_days` ahora son **verdaderamente inamovibles**
- Si hay problemas de configuración (mandatory que violan restricciones), el sistema los **reporta pero no los corrige automáticamente**
- El usuario debe revisar y corregir los datos de trabajadores si hay errores de configuración
- La protección es **fail-safe**: en caso de duda, NO se permite modificar un mandatory_day

---

**Autor:** GitHub Copilot  
**Fecha:** 24 de Octubre de 2025  
**Versión:** 1.0
