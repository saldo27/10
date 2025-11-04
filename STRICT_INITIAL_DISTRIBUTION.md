# Sistema de Reparto Inicial ESTRICTO + Iteración Relajada

## 🎯 Objetivo

**Fase Inicial:** Reparto estricto respetando todas las restricciones sin excepciones
**Fase Iteración:** Relajación controlada para optimizar y completar el horario

---

## 📜 Restricciones en Fase Inicial (ESTRICTAS)

### 1. **Objetivo de Turnos**
- Tolerancia: **+10%** sobre target (ajustado por % jornada)
- Formula: `max_allowed = target_shifts × work_percentage/100 × 1.10`
- **BLOQUEO ABSOLUTO** si se excede

### 2. **Turnos Mandatory**
- Se cuentan dentro del objetivo
- **NUNCA** se pueden cambiar, mover o eliminar
- Protegidos con `_locked_mandatory`

### 3. **Incompatibilidades**
- **BLOQUEO ABSOLUTO** si trabajadores incompatibles en mismo turno/día
- Cache de incompatibilidades para velocidad

### 4. **Distancia Mínima entre Guardias**
- Mínimo: `gap_between_shifts` días
- **NO se permite -1** en fase inicial
- Solo en iteración con extrema necesidad

### 5. **Patrón 7/14 Días**
- **PROHIBIDO** asignar mismo día de semana con distancia 7 o 14 días
- Aplica a lunes-jueves (weekend tiene reglas especiales)
- **SIN EXCEPCIONES** en fase inicial

### 6. **Equilibrio Mensual**
- Tolerancia: **±1 turno** por mes como máximo extremo
- Calcula distribución esperada: `target/12 × días_en_mes`
- Bloquea si desbalance > 1

### 7. **Equilibrio Fines de Semana**
- Tolerancia: **±1 fin de semana** como máximo extremo
- Distribución equitativa entre trabajadores
- Bloquea si desbalance > 1

### 8. **Equilibrio Last Posts**
- Distribución equitativa del último puesto
- Evita que siempre le toque al mismo trabajador
- Preferencia: quien menos last posts tenga

### 9. **Turnos Fuera (Days Off)**
- **IMPOSIBLE** asignar en días marcados como "fuera"
- Validación en `days_off` del worker
- Bloqueo total sin excepciones

---

## 🔧 Implementación

### **A. Validador Estricto de Constraints**

```python
class StrictConstraintValidator:
    """
    Validador ESTRICTO para fase inicial.
    NO permite excepciones.
    """
    
    def validate_assignment_strict(
        self, 
        worker_id: str,
        date: datetime,
        post: int,
        schedule: Dict,
        worker_data: Dict
    ) -> Tuple[bool, str]:
        """
        Valida si asignación cumple TODAS las restricciones estrictas.
        
        Returns:
            (valid, reason): True si válido, False + razón si no
        """
        # 1. Days off
        if self._is_day_off(worker_id, date):
            return False, "Worker has day off"
        
        # 2. Incompatibilidades
        if self._has_incompatibility(worker_id, date, post, schedule):
            return False, "Incompatibility conflict"
        
        # 3. Objetivo +10%
        if self._exceeds_target_limit(worker_id, worker_data):
            return False, "Exceeds +10% target limit"
        
        # 4. Gap mínimo
        if not self._respects_min_gap(worker_id, date):
            return False, "Violates minimum gap"
        
        # 5. Patrón 7/14
        if self._violates_7_14_pattern(worker_id, date):
            return False, "Violates 7/14 day pattern"
        
        # 6. Equilibrio mensual
        if self._exceeds_monthly_balance(worker_id, date, worker_data):
            return False, "Exceeds monthly balance ±1"
        
        # 7. Equilibrio weekend
        if self._exceeds_weekend_balance(worker_id, date):
            return False, "Exceeds weekend balance ±1"
        
        # 8. Last post balance
        if post == self.num_shifts and self._exceeds_last_post_balance(worker_id):
            return False, "Exceeds last post balance"
        
        return True, "Valid"
```

### **B. Sistema de Scoring Estricto**

```python
def _calculate_strict_score(
    self, 
    worker: Dict,
    date: datetime,
    post: int
) -> float:
    """
    Calcula score para fase inicial ESTRICTA.
    
    Prioridades:
    1. Mandatory shifts (máxima prioridad)
    2. Workers con mayor déficit
    3. Balancear fines de semana
    4. Balancear mensual
    5. Balancear last posts
    """
    score = 0
    worker_id = worker['id']
    
    # PRIORIDAD 1: Mandatory
    if self._is_mandatory(worker_id, date):
        return 1000000  # Máxima prioridad
    
    # PRIORIDAD 2: Déficit de turnos
    current = len(self.worker_assignments[worker_id])
    target = worker.get('target_shifts', 0)
    deficit = target - current
    
    if deficit > 0:
        score += deficit * 5000  # Bonus masivo por déficit
    else:
        score -= abs(deficit) * 2000  # Penalización por exceso
    
    # PRIORIDAD 3: Balance weekend
    if date.weekday() >= 4:  # Es fin de semana
        weekend_count = self._count_weekends(worker_id)
        expected_weekends = self._calculate_expected_weekends(worker)
        weekend_deficit = expected_weekends - weekend_count
        score += weekend_deficit * 2000
    
    # PRIORIDAD 4: Balance mensual
    month_count = self._count_month_assignments(worker_id, date)
    expected_month = self._calculate_expected_monthly(worker, date)
    month_deficit = expected_month - month_count
    score += month_deficit * 1000
    
    # PRIORIDAD 5: Last post balance
    if post == self.num_shifts:
        last_post_count = self._count_last_posts(worker_id)
        expected_last = self._calculate_expected_last_posts(worker)
        last_deficit = expected_last - last_post_count
        score += last_deficit * 1500
    
    return score
```

### **C. Relajación en Fase de Iteración**

```python
class RelaxedOptimizer:
    """
    Optimizador con relajación progresiva para fase iterativa.
    """
    
    RELAXATION_LEVELS = {
        'LEVEL_0': {
            'name': 'STRICT',
            'target_tolerance': 1.10,      # +10%
            'gap_reduction': 0,             # Sin reducción
            'pattern_7_14': 'strict',       # Estricto
            'monthly_tolerance': 1,         # ±1
            'weekend_tolerance': 1          # ±1
        },
        'LEVEL_1': {
            'name': 'MODERATE',
            'target_tolerance': 1.12,      # +12%
            'gap_reduction': 0,             # Sin reducción aún
            'pattern_7_14': 'moderate',     # Permite con déficit >3
            'monthly_tolerance': 2,         # ±2
            'weekend_tolerance': 1          # ±1 (mantener)
        },
        'LEVEL_2': {
            'name': 'RELAXED',
            'target_tolerance': 1.15,      # +15%
            'gap_reduction': 0,             # Sin reducción
            'pattern_7_14': 'relaxed',      # Permite con déficit >2
            'monthly_tolerance': 2,         # ±2
            'weekend_tolerance': 2          # ±2
        },
        'LEVEL_3': {
            'name': 'EXTREME',
            'target_tolerance': 1.18,      # +18%
            'gap_reduction': 1,             # gap-1 SOLO en extremo
            'pattern_7_14': 'very_relaxed', # Permite con déficit >1
            'monthly_tolerance': 3,         # ±3
            'weekend_tolerance': 2          # ±2 (mantener)
        }
    }
    
    def select_relaxation_level(self, iteration: int, violations: int) -> str:
        """
        Selecciona nivel de relajación según progreso.
        
        Criterios:
        - Iterations 1-10 con violations >20: LEVEL_1
        - Iterations 11-20 con violations >15: LEVEL_2  
        - Iterations 21+ con violations >10: LEVEL_3
        - Violations <5: LEVEL_0 (mantener estricto)
        """
        if violations < 5:
            return 'LEVEL_0'
        elif iteration <= 10 and violations > 20:
            return 'LEVEL_1'
        elif iteration <= 20 and violations > 15:
            return 'LEVEL_2'
        elif violations > 10:
            return 'LEVEL_3'
        else:
            return 'LEVEL_1'
```

---

## 🔄 Flujo de Trabajo

### **Fase 1: Reparto Inicial (ESTRICTO)**

```
Para cada intento (10-60 intentos):
    1. Restaurar mandatory shifts
    2. Aplicar validador ESTRICTO
    3. Usar scoring estricto
    4. NO permitir excepciones
    5. Evaluar calidad
    6. Guardar mejor intento

Seleccionar mejor intento →
```

### **Fase 2: Optimización Iterativa (RELAJADA)**

```
Para cada iteración (1-30):
    1. Evaluar violations
    2. Seleccionar nivel relajación
    3. Aplicar constraints relajados
    4. Permitir excepciones controladas
    5. Verificar mejora
    6. Si mejora: aplicar
    7. Si no mejora: aumentar relajación
```

---

## 📊 Comparación Fase Inicial vs Iteración

| Restricción | Fase Inicial | Fase Iteración (Nivel 3) |
|-------------|--------------|--------------------------|
| Target limit | +10% ESTRICTO | +18% relajado |
| Gap mínimo | NO reducción | gap-1 permitido |
| Patrón 7/14 | PROHIBIDO | Permite con déficit >1 |
| Balance mensual | ±1 ESTRICTO | ±3 relajado |
| Balance weekend | ±1 ESTRICTO | ±2 relajado |
| Incompatibilidades | NUNCA | NUNCA (siempre estricto) |
| Days off | NUNCA | NUNCA (siempre estricto) |
| Mandatory | NUNCA cambiar | NUNCA cambiar |

**Restricciones SIEMPRE estrictas (nunca se relajan):**
- ✅ Mandatory shifts
- ✅ Incompatibilidades
- ✅ Days off

---

## 🎯 Objetivos de Calidad

### **Al finalizar Fase Inicial:**
- ✅ 90-95% de shifts asignados
- ✅ 0 violaciones de mandatory
- ✅ 0 violaciones de incompatibilidades
- ✅ 0 violaciones de days off
- ✅ Violaciones de balance: 15-25

### **Al finalizar Fase Iteración:**
- ✅ 98-100% de shifts asignados
- ✅ 0 violaciones críticas (mandatory, incomp, days off)
- ✅ Violaciones de balance: 0-5
- ✅ Distribución equilibrada

---

## 🚀 Próximos Pasos

1. ✅ Implementar `StrictConstraintValidator`
2. ✅ Modificar `_calculate_worker_score` para fase inicial
3. ✅ Crear `RelaxedOptimizer` con niveles
4. ✅ Integrar en `scheduler_core.py`
5. ✅ Integrar en `iterative_optimizer.py`
6. ✅ Testing exhaustivo
