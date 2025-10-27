# ⚠️ CORRECCIÓN CRÍTICA: Asignación de Mandatory Days

## Fecha: 24 de Octubre de 2025

---

## 🔴 PROBLEMA CRÍTICO DETECTADO Y CORREGIDO

### **Error en `_assign_mandatory_guards()`**

**Ubicación:** `schedule_builder.py` líneas ~1135-1150

### Descripción del Problema

El método `_assign_mandatory_guards()` estaba usando `_can_assign_worker()` para verificar si podía asignar un `mandatory_day`. Este método verifica **TODAS** las restricciones incluyendo:

- Gap entre turnos (días mínimos de descanso)
- Patrón 7/14 días
- Límites de fines de semana consecutivos
- Incompatibilidades entre trabajadores
- Disponibilidad del trabajador (work_periods, days_off)

### Consecuencia del Error

Si un `mandatory_day` violaba restricciones "soft" como:
- Gap mínimo entre turnos
- Patrón de 7 o 14 días
- Límites de fines de semana

**El turno NO se asignaba** y solo se mostraba un warning: 
```
Could not place mandatory shift for {worker_id} on {date}. All posts filled or incompatible.
```

Esto es **INCORRECTO** porque los `mandatory_days` son OBLIGATORIOS por definición y deben asignarse **SIEMPRE**, incluso si violan restricciones normales.

### Ejemplo Concreto del Error

```python
# Configuración del trabajador
Worker A: 
  - mandatory_days = "15-10-2025;17-10-2025"
  - gap_between_shifts = 3 días (mínimo)

# Comportamiento ANTES de la corrección
❌ Día 15-10-2025: Se asigna correctamente
❌ Día 17-10-2025: NO se asigna porque está a solo 2 días del 15-10
   Log: "Could not place mandatory shift - violates gap constraint"
   
# Comportamiento DESPUÉS de la corrección  
✅ Día 15-10-2025: Se asigna
✅ Día 17-10-2025: Se asigna (ignora gap porque es MANDATORY)
   Log: "Assigned worker A to 17-10-2025 post X (mandatory) and locked."
```

---

## ✅ SOLUCIÓN IMPLEMENTADA

### Cambio en `schedule_builder.py`

**ANTES:**
```python
if self.schedule[date][post] is None:
    # Check incompatibility
    others_on_date = [...]
    if not self._check_incompatibility_with_list(worker_id, others_on_date):
        continue
    
    # ❌ PROBLEMA: Verificaba TODAS las restricciones
    if not self._can_assign_worker(worker_id, date, post):
        logging.debug(f"Mandatory shift violates constraints")
        continue
    
    self.schedule[date][post] = worker_id
```

**DESPUÉS (CORREGIDO):**
```python
if self.schedule[date][post] is None:
    # CRITICAL: For MANDATORY assignments, only check HARD constraints
    # (incompatibility and unavailability), NOT soft constraints
    
    # ✅ Check incompatibility (HARD constraint)
    others_on_date = [...]
    if not self._check_incompatibility_with_list(worker_id, others_on_date):
        logging.debug(f"Mandatory shift incompatible. Trying next post.")
        continue
    
    # ✅ Check unavailability (HARD constraint)
    if self._is_worker_unavailable(worker_id, date):
        logging.warning(f"Mandatory shift conflicts with days_off/work_periods. Configuration error.")
        continue
    
    # ✅ NOTE: NO se verifican gap, 7/14 pattern, o weekend limits
    # porque mandatory_days ANULAN estas restricciones soft
    
    self.schedule[date][post] = worker_id
```

---

## 📋 Tipos de Restricciones

### Restricciones HARD (siempre se verifican)
Estas NO pueden violarse ni siquiera para mandatory_days:

1. **Incompatibilidad entre trabajadores**: Si dos trabajadores son incompatibles, no pueden trabajar el mismo día
2. **Disponibilidad del trabajador**: Si el trabajador tiene `days_off` o está fuera de su `work_periods`, no puede trabajar

### Restricciones SOFT (se ignoran para mandatory_days)
Estas SE IGNORAN para mandatory_days:

1. **Gap mínimo entre turnos**: Los mandatory_days pueden estar muy cerca entre sí
2. **Patrón 7/14 días**: Los mandatory_days pueden estar a 7 o 14 días exactos
3. **Límites de fines de semana consecutivos**: Los mandatory_days no cuentan para este límite
4. **Target shifts**: Los mandatory_days se asignan independientemente del objetivo de turnos

---

## 🔍 Casos Especiales y Manejo de Errores

### Caso 1: Mandatory con incompatibilidad
```python
# Si Worker A y Worker B son incompatibles y ambos tienen mandatory el mismo día
Worker A: mandatory_days = "15-10-2025"
Worker B: mandatory_days = "15-10-2025"
Workers A y B son incompatibles

Resultado:
- El primero en procesarse se asigna al primer post disponible
- El segundo intenta asignarse pero detecta incompatibilidad
- Se intenta en otro post del mismo día
- Si no hay posts disponibles: WARNING "Could not place mandatory shift - incompatible"
- Esto es un ERROR DE CONFIGURACIÓN que el usuario debe corregir
```

### Caso 2: Mandatory con days_off
```python
# Si un trabajador tiene mandatory en un día que está en days_off
Worker A: 
  - mandatory_days = "15-10-2025"
  - days_off = "10-10-2025 - 20-10-2025"

Resultado:
- Se detecta que está unavailable (days_off)
- Se muestra WARNING "Configuration error - conflicts with days_off"
- NO se asigna el turno
- Esto es un ERROR DE CONFIGURACIÓN que el usuario debe corregir
```

### Caso 3: Mandatory que viola gap (CORRECTO)
```python
Worker A:
  - mandatory_days = "15-10-2025;17-10-2025"
  - gap_between_shifts = 3

Resultado:
✅ Ambos días se asignan correctamente
✅ El gap se ignora porque son MANDATORY
✅ El sistema puede mostrar un aviso informativo pero NO bloquea la asignación
```

---

## 📊 Resumen de Cambios

| Aspecto | Antes | Después |
|---------|-------|---------|
| Verificación de gap | ❌ Bloqueaba mandatory | ✅ Se ignora para mandatory |
| Verificación de patrón 7/14 | ❌ Bloqueaba mandatory | ✅ Se ignora para mandatory |
| Verificación de incompatibilidad | ✅ Correcto | ✅ Correcto |
| Verificación de disponibilidad | ✅ Correcto | ✅ Correcto |
| Asignación garantizada | ❌ NO garantizada | ✅ Garantizada (con restricciones HARD) |

---

## ⚠️ IMPORTANTE: Errores de Configuración

El sistema ahora distingue entre:

1. **Restricciones que pueden violarse para mandatory**: Gap, patrones, límites
2. **Restricciones que NO pueden violarse**: Incompatibilidad, disponibilidad

Si un mandatory_day viola una restricción HARD:
- Se registra como **ERROR de configuración**
- El usuario debe revisar y corregir los datos del trabajador
- El sistema NO asigna el turno automáticamente

---

## 🧪 Testing Recomendado

1. ✅ Crear mandatory_days consecutivos (viola gap)
2. ✅ Crear mandatory_days a 7 días exactos (viola patrón)
3. ✅ Crear mandatory_days para trabajadores incompatibles (error de config)
4. ✅ Crear mandatory_days en days_off (error de config)
5. ✅ Verificar que todos los mandatory_days se asignan cuando es posible
6. ✅ Verificar logs para errores de configuración

---

**Autor:** GitHub Copilot  
**Fecha:** 24 de Octubre de 2025  
**Versión:** 1.0  
**Estado:** ✅ CRÍTICO - CORREGIDO
