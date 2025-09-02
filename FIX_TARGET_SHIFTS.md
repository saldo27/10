# Corrección: Uso de target_shifts Reales para Cálculo de Desviaciones

## Problema Identificado ❌

El cálculo inicial de desviaciones en `adjustment_utils.py` estaba usando un cálculo genérico basado en porcentajes de trabajo, en lugar de utilizar los valores reales de `target_shifts` que ya calcula el sistema.

### Comportamiento Anterior (Incorrecto)
```python
# Calculaba objetivo proporcional genérico
total_percentage = sum(stats['percentage'] for stats in worker_stats.values())
target = round((stats['percentage'] / total_percentage) * total_assigned_shifts)
```

## Solución Implementada ✅

### Cambio Principal en `calculate_deviations()`
```python
# Ahora usa el target_shifts real del sistema
target_shifts = worker.get('target_shifts', 0)  # Valor real calculado por scheduler
worker_stats[worker_id] = {
    'target': target_shifts,  # Usar el valor real del sistema
    # ... resto de campos
}
```

### Cómo funciona target_shifts en el Sistema

El método `_calculate_target_shifts()` en `scheduler.py` calcula estos valores considerando:

1. **Slots disponibles por trabajador** según sus `work_periods` y `days_off`
2. **Porcentaje de jornada** (`work_percentage`) 
3. **Distribución proporcional** con redondeo largest-remainder
4. **Días obligatorios** restados del objetivo para evitar doble conteo

### Resultado de la Corrección

**Antes de la corrección:**
- Cálculo de objetivo incorrecto/simplificado
- Desviaciones no reflejaban la realidad del sistema

**Después de la corrección:**
- ✅ Usa valores reales de `target_shifts` ya calculados
- ✅ Considera períodos de trabajo específicos
- ✅ Respeta porcentajes de jornada individuales  
- ✅ Excluye días obligatorios del cálculo de objetivos
- ✅ Desviaciones precisas y coherentes con el sistema

## Prueba de Funcionamiento

```bash
cd /workspaces/5 && python test_adjustment.py
```

**Resultado de prueba:**
```
Trabajador 003: 6 asignados, 3 objetivo, desviación: +3
Trabajador 004: 3 asignados, 5 objetivo, desviación: -2
```

**Después del intercambio:**
```
Trabajador 003: 5 asignados, 3 objetivo, desviación: +2  # Mejoró
Trabajador 004: 4 asignados, 5 objetivo, desviación: -1  # Mejoró
```

## Archivos Modificados

### `/workspaces/5/adjustment_utils.py`
- ✅ Método `calculate_deviations()` corregido
- ✅ Ahora usa `worker.get('target_shifts', 0)` directamente
- ✅ Eliminado cálculo proporcional incorrecto

### `/workspaces/5/test_adjustment.py` 
- ✅ Actualizado con datos de `target_shifts` para pruebas
- ✅ Escenario de prueba que muestra intercambios exitosos

## Estado: ✅ CORREGIDO

La funcionalidad de ajuste ahora calcula desviaciones correctamente usando los valores reales de `target_shifts` del sistema, lo que garantiza coherencia y precisión en los ajustes propuestos.
