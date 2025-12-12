# 🔒 CORRECCIÓN CRÍTICA: Protección Centralizada de Turnos Mandatory

## 📋 Problema Identificado

Los turnos **mandatory** asignados en la **fase inicial** (antes de las iteraciones de optimización) están siendo **modificados o eliminados** durante las fases de mejora iterativa, violando la restricción fundamental de que estos turnos son OBLIGATORIOS e INMUTABLES.

### Síntomas del Problema:
- ✅ Turnos mandatory se asignan correctamente en `_assign_mandatory_guards()`
- ✅ Se añaden a `_locked_mandatory` set
- ❌ Durante la optimización iterativa, algunos métodos NO verifican `_locked_mandatory`
- ❌ Los turnos mandatory pueden ser movidos, intercambiados o eliminados
- ❌ Al final, algunos trabajadores no tienen sus mandatory_days asignados

## 🔧 Solución Implementada

Se ha implementado una **verificación CENTRALIZADA** que DEBE ser llamada ANTES de cualquier modificación de asignaciones.

### 1. Nuevos Métodos Centralizados

#### `_is_slot_protected_mandatory(date, post)`
Verifica si un slot específico está ocupado por un turno mandatory que NO puede ser modificado.

```python
def _is_slot_protected_mandatory(self, date, post):
    """
    CRITICAL: Verificación CENTRALIZADA de protección mandatory.
    
    Returns:
        tuple: (is_protected, worker_id)
            - is_protected: True si el slot está protegido
            - worker_id: ID del trabajador si está protegido, None en caso contrario
    """
    # Verificar que el slot existe y tiene un trabajador asignado
    if date not in self.schedule or len(self.schedule[date]) <= post:
        return False, None
    
    worker_id = self.schedule[date][post]
    if worker_id is None:
        return False, None
    
    # Verificar si está en el conjunto de mandatory bloqueados
    if (worker_id, date) in self._locked_mandatory:
        return True, worker_id
    
    # Verificar si es mandatory según la configuración del trabajador
    if self._is_mandatory(worker_id, date):
        return True, worker_id
    
    return False, None
```

#### `_can_modify_assignment(worker_id, date, operation_name)`
Verifica si una asignación puede ser modificada/eliminada.

```python
def _can_modify_assignment(self, worker_id, date, operation_name="unknown"):
    """
    CRITICAL: Verificación CENTRALIZADA antes de modificar/eliminar una asignación.
    
    Este método DEBE ser llamado ANTES de:
    - Mover un trabajador a otra fecha
    - Reasignar un trabajador a otro puesto  
    - Eliminar una asignación
    - Intercambiar trabajadores (swap)
    
    Returns:
        bool: True si se puede modificar, False si está protegido
    """
    # Verificar locked mandatory
    if (worker_id, date) in self._locked_mandatory:
        logging.info(f"🚫 BLOCKED {operation_name}: Cannot modify LOCKED MANDATORY")
        return False
    
    # Verificar config mandatory
    if self._is_mandatory(worker_id, date):
        logging.info(f"🚫 BLOCKED {operation_name}: Cannot modify CONFIG MANDATORY")
        return False
    
    return True
```

### 2. Métodos Actualizados

Se ha aplicado la verificación centralizada en TODOS los métodos que modifican asignaciones:

#### ✅ `_try_fill_empty_shifts` (Pass 1 - Direct Fill)
```python
# ANTES de intentar asignar a un slot
is_protected, protected_worker = self._is_slot_protected_mandatory(date, post)
if is_protected:
    continue  # No intentar modificar este slot
```

#### ✅ `_try_fill_empty_shifts` (Pass 2 - Swaps)
```python
# ANTES de considerar un worker para swap
if not self._can_modify_assignment(worker_W_id, date_conflict, "swap_fill_empty"):
    continue
```

#### ✅ `_balance_workloads`
```python
# ANTES de reasignar turno
if not self._can_modify_assignment(over_worker_id, date_val, "balance_workloads"):
    continue
```

#### ✅ `_balance_weekday_distribution`
```python
# ANTES de mover turno a otro día de semana
if not self._can_modify_assignment(worker_id, date, "balance_weekday_distribution"):
    continue
```

#### ✅ `_balance_weekend_shifts` (mejorado)
```python
# ANTES de reasignar turno especial (weekend/holiday)
if not self._can_modify_assignment(over_worker_id, special_day_to_reassign, "balance_weekend_shifts"):
    continue
```

#### ✅ `_perform_shift_rebalancing`
```python
# ANTES de encontrar turnos movibles
if self._can_modify_assignment(over_worker_id, date, "rebalance_weekend"):
    # ... procesar turno
```

#### ✅ `_try_redistribute_excess_shifts`
```python
# ANTES de redistribuir exceso
if not self._can_modify_assignment(overloaded_worker_id, date, "redistribute_excess"):
    continue
```

#### ✅ `_find_swap_candidate`
```python
# ANTES de buscar candidato para swap
if not self._can_modify_assignment(worker_W_id, conflict_date, "swap_candidate_search"):
    return None
```

#### ✅ `_adjust_last_post_distribution_improved`
```python
# ANTES de intentar swap de último puesto
if not self._can_modify_assignment(worker_A_id, date_to_adjust, "adjust_last_post"):
    continue

# Y también para el partner:
if not self._can_modify_assignment(worker_B_id, date_to_adjust, "adjust_last_post_B"):
    continue
```

## 📊 Cobertura de Protección

### Métodos que YA tenían verificación (pero inconsistente):
- `_assign_mandatory_guards()` - asignación inicial con lock
- `_balance_workloads()` - verificaba `_is_mandatory`
- `_balance_weekend_shifts()` - verificaba ambos
- `_find_swap_candidate()` - verificaba `_is_mandatory`

### Métodos que NECESITABAN protección (ahora corregidos):
- ✅ `_try_fill_empty_shifts()` - Pass 1 y Pass 2
- ✅ `_balance_weekday_distribution()` - NO verificaba
- ✅ `_perform_shift_rebalancing()` - Verificaba solo `_is_mandatory`
- ✅ `_try_redistribute_excess_shifts()` - Verificaba de forma fragmentada
- ✅ `_adjust_last_post_distribution_improved()` - Solo verificaba `_is_mandatory`

## 🎯 Ventajas de la Solución

### 1. **Centralización**
- Un ÚNICO punto de verificación en lugar de código disperso
- Reduce errores por verificaciones olvidadas o inconsistentes
- Facilita mantenimiento y debugging

### 2. **Doble Verificación**
- Verifica tanto `_locked_mandatory` (asignaciones bloqueadas al inicio)
- Como `_is_mandatory` (configuración del trabajador)
- Garantiza protección incluso si falla el lock inicial

### 3. **Logging Mejorado**
- Cada bloqueo incluye el nombre de la operación
- Facilita identificar qué operación intenta modificar un mandatory
- Ayuda en debugging y auditoría

### 4. **Prevención Proactiva**
- Las operaciones verifican ANTES de intentar modificar
- Evita modificaciones parciales o inconsistencias
- Mantiene integridad del schedule en todo momento

## 🔍 Testing

Se ha creado `test_mandatory_protection.py` que verifica:

1. **Asignación Inicial Correcta**
   - Todos los mandatory_days se asignan en fase inicial
   - Se añaden a `_locked_mandatory`

2. **Protección Durante Optimización**
   - Los mandatory NO son modificados durante las iteraciones
   - Los trabajadores siguen teniendo sus mandatory_days al final

3. **Verificación de Método Centralizado**
   - `_can_modify_assignment()` retorna False para mandatory
   - `_can_modify_assignment()` retorna True para non-mandatory

## 📝 Uso Recomendado

### Para Desarrolladores:

**SIEMPRE** que vayas a modificar una asignación (mover, eliminar, swap), DEBES:

```python
# 1. Verificar si se puede modificar
if not self._can_modify_assignment(worker_id, date, "nombre_operacion"):
    continue  # o return False

# 2. Proceder con la modificación
# ... tu código aquí ...
```

### Operaciones que Requieren Verificación:
- ❌ Mover trabajador a otra fecha
- ❌ Cambiar trabajador de puesto en el mismo día (si es último puesto)
- ❌ Eliminar asignación
- ❌ Intercambiar (swap) dos trabajadores
- ❌ Reasignar turno a otro trabajador

### Operaciones que NO Requieren Verificación:
- ✅ Asignar trabajador a slot vacío (nuevo assignment)
- ✅ Verificar si trabajador puede ser asignado (sin modificar)
- ✅ Calcular métricas o estadísticas

## 🚀 Resultado Esperado

Con esta corrección, los turnos mandatory:
- ✅ Se asignan correctamente en la fase inicial
- ✅ Se marcan como protegidos en `_locked_mandatory`
- ✅ NO son modificados durante NINGUNA fase de optimización
- ✅ Permanecen intactos hasta la generación final del calendario
- ✅ Todos los trabajadores tienen sus mandatory_days asignados al 100%

## 📌 Nota Importante

Los turnos mandatory pueden cambiar de **puesto** en el mismo día (por ejemplo, de puesto 0 a puesto 1) si es necesario para resolver incompatibilidades, PERO:
- ✅ El trabajador SIEMPRE está asignado en la fecha mandatory
- ❌ El trabajador NUNCA es removido de la fecha mandatory
- ❌ El trabajador NUNCA es movido a otra fecha

Si se requiere protección absoluta del puesto también, se puede modificar `_can_modify_assignment` para bloquear incluso swaps intra-día.

---

**Fecha de implementación:** 14 de noviembre de 2025  
**Autor:** GitHub Copilot  
**Archivos modificados:**
- `schedule_builder.py` - Métodos centralizados y aplicación en todos los métodos de optimización
- `test_mandatory_protection.py` - Suite de tests para verificar protección
