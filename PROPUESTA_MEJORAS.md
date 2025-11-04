# 🔧 Propuesta de Mejoras al Sistema de Generación de Horarios

## 📋 Problemas Identificados

### 1. **Reparto Inicial Demasiado Pobre**
El sistema realiza múltiples intentos (10-60) de reparto inicial, pero la calidad sigue siendo insuficiente.

**Causas raíz:**
- ❌ Scoring demasiado conservador que penaliza en lugar de incentivar
- ❌ Constraints 7/14 demasiado estrictos en fase inicial (solo se relajan en nivel 2)
- ❌ Lógica de "reserve capacity" que bloquea asignaciones prematuramente
- ❌ Gap constraints muy restrictivos para workers con déficit
- ❌ No hay suficiente "agresividad" para llenar el schedule en el primer intento

### 2. **Iteraciones Demasiado Agresivas**
El optimizador hace 50 iteraciones con redistribuciones masivas (155+ cambios por iteración).

**Causas raíz:**
- ❌ No hay early stopping inteligente (solo para = 0 violations)
- ❌ Redistribuciones muy agresivas (violations × 10-15)
- ❌ Multi-shift strategy intenta hasta 5 shifts por worker
- ❌ No evalúa si las iteraciones están mejorando realmente
- ❌ Sistema trabaja sobre un schedule inicial pobre

---

## 🎯 Estrategia de Solución

### **Principio fundamental:** 
**"Un buen reparto inicial requiere menos optimización agresiva"**

### **Enfoque en 2 fases:**

#### **Fase 1: MEJORAR EL REPARTO INICIAL** (Mayor impacto)
- ✅ Scoring más agresivo para llenar el schedule
- ✅ Relaxación progresiva de constraints dentro de cada intento
- ✅ Múltiples pasadas por intento con scoring diferente
- ✅ Priorizar llenar schedule antes que perfecta distribución

#### **Fase 2: OPTIMIZAR LAS ITERACIONES** (Menor impacto, pero necesario)
- ✅ Early stopping inteligente (mejora < threshold)
- ✅ Redistribuciones escaladas progresivamente
- ✅ Menos iteraciones pero más efectivas
- ✅ Mejor detección de estancamiento

---

## 🔨 Cambios Propuestos

### **A. MEJORAR REPARTO INICIAL**

#### **A1. Sistema de Múltiples Pasadas por Intento**

Cada intento hará **3-4 pasadas** con diferentes configuraciones:

```python
# Pasada 1: AGGRESSIVE FILL (relaxation=0-1)
# - Prioridad: Llenar schedule
# - Bonus muy alto para deficit
# - Penalties reducidas
# - Pattern 7/14 relajado

# Pasada 2: BALANCE FILL (relaxation=1)
# - Prioridad: Balancear carga
# - Ajustar desequilibrios
# - Pattern 7/14 moderado

# Pasada 3: FINE TUNING (relaxation=0)
# - Prioridad: Respetar targets
# - Pattern 7/14 estricto
# - Llenar huecos finales
```

**Configuración por pasada:**

| Pasada | Relaxation | Bonus Deficit | Penalty Excess | Pattern 7/14 | Gap Min |
|--------|------------|---------------|----------------|--------------|---------|
| 1      | 0-1        | 5000          | 1000           | Relajado     | normal  |
| 2      | 1          | 3000          | 2000           | Moderado     | normal  |
| 3      | 0          | 2000          | 5000           | Estricto     | normal  |

#### **A2. Modificar Scoring en `schedule_builder.py`**

**Cambios en `_calculate_target_shift_score()`:**

```python
# ACTUAL: Bonus 3000 por shift de déficit
# PROPUESTA: Bonus 5000 en primera pasada, luego 3000

if shift_difference > 0:
    # Bonus escalonado según pasada
    if self.current_fill_pass == 1:
        score += shift_difference * 5000  # MUY AGRESIVO
    else:
        score += shift_difference * 3000  # MODERADO
```

**Cambios en `_calculate_overall_target_score()`:**

```python
# ACTUAL: Bloquea si excede +10% en relaxation < 2
# PROPUESTA: Permitir hasta +15% en primera pasada

if self.current_fill_pass == 1:
    # Primera pasada: más permisivo
    max_allowed = int(overall_target_shifts * 1.15)  # +15%
else:
    # Pasadas posteriores: estricto
    max_allowed = int(overall_target_shifts * 1.10)  # +10%
```

**Cambios en `_check_gap_constraints()`:**

```python
# ACTUAL: Pattern 7/14 solo se relaja en relaxation=2 con deficit>=5
# PROPUESTA: Relajar en primera pasada con deficit>=2

if (days_between == 7 or days_between == 14):
    # Primera pasada: más permisivo
    if self.current_fill_pass == 1 and target_deficit >= 2:
        logging.debug("Pattern 7/14 relajado en pasada inicial")
        continue
    # Pasadas posteriores: estricto
    elif relaxation_level >= 2 and target_deficit >= 5:
        continue
    else:
        return False
```

#### **A3. Implementar Sistema de Pasadas**

**Nuevo método en `schedule_builder.py`:**

```python
def _fill_schedule_with_multiple_passes(self):
    """
    Llena el schedule en múltiples pasadas con diferentes prioridades.
    
    Pasada 1: AGGRESSIVE FILL - Llenar máximo posible
    Pasada 2: BALANCE FILL - Balancear distribución
    Pasada 3: FINE TUNING - Ajustes finales
    
    Returns:
        bool: True if schedule successfully filled
    """
    passes_config = [
        {
            'pass_num': 1,
            'name': 'AGGRESSIVE FILL',
            'relaxation_range': (0, 1),
            'target_fill_percentage': 95,  # Intentar llenar 95%
            'scoring_multiplier': 1.5      # Bonuses x1.5
        },
        {
            'pass_num': 2,
            'name': 'BALANCE FILL',
            'relaxation_range': (1, 1),
            'target_fill_percentage': 98,  # Llenar 98%
            'scoring_multiplier': 1.0      # Bonuses normales
        },
        {
            'pass_num': 3,
            'name': 'FINE TUNING',
            'relaxation_range': (0, 2),
            'target_fill_percentage': 100, # Llenar 100%
            'scoring_multiplier': 0.8      # Bonuses reducidos
        }
    ]
    
    for pass_config in passes_config:
        self.current_fill_pass = pass_config['pass_num']
        self.scoring_multiplier = pass_config['scoring_multiplier']
        
        logging.info(f"\n{'─' * 60}")
        logging.info(f"🎯 Pass {pass_config['pass_num']}: {pass_config['name']}")
        logging.info(f"{'─' * 60}")
        
        # Calcular huecos restantes
        empty_count = self._count_empty_shifts()
        total_shifts = self._count_total_shifts()
        fill_percentage = ((total_shifts - empty_count) / total_shifts * 100)
        
        logging.info(f"Current fill: {fill_percentage:.1f}%")
        logging.info(f"Target fill: {pass_config['target_fill_percentage']}%")
        
        # Intentar llenar con relaxation progresiva
        for relax_level in range(*pass_config['relaxation_range']):
            self._fill_empty_shifts_with_relaxation(relax_level)
            
        # Evaluar progreso
        new_empty_count = self._count_empty_shifts()
        filled_in_pass = empty_count - new_empty_count
        logging.info(f"✓ Filled {filled_in_pass} shifts in this pass")
        
        # Si ya llegamos al target, siguiente pasada
        new_fill_pct = ((total_shifts - new_empty_count) / total_shifts * 100)
        if new_fill_pct >= pass_config['target_fill_percentage']:
            logging.info(f"✅ Target achieved: {new_fill_pct:.1f}%")
        else:
            logging.warning(f"⚠️ Below target: {new_fill_pct:.1f}%")
    
    # Resetear estado
    self.current_fill_pass = 0
    self.scoring_multiplier = 1.0
    
    return True
```

---

### **B. OPTIMIZAR ITERACIONES**

#### **B1. Early Stopping Inteligente**

**Modificar `_should_stop_optimization()` en `iterative_optimizer.py`:**

```python
def _should_stop_optimization(self, iteration: int, current_violations: int) -> bool:
    """
    Stopping criteria inteligente basado en mejora real.
    
    CRITERIA:
    1. Perfect schedule (violations = 0)
    2. Stagnation > threshold con violations bajas (< 5)
    3. Mejora promedio < 0.3 violations/iteration en últimas 10 iterations
    4. Violations aumentan consistentemente (3+ iterations)
    """
    # 1. Perfect schedule
    if current_violations == 0:
        logging.info("✅ Perfect schedule - stopping")
        return True
    
    # 2. Low violations + stagnation
    if current_violations <= 5 and self.stagnation_counter >= 5:
        logging.info(f"✅ Acceptable violations ({current_violations}) + stagnation - stopping")
        return True
    
    # 3. Low improvement rate
    if len(self.optimization_history) >= 10:
        recent_10 = self.optimization_history[-10:]
        improvement = recent_10[0]['total_violations'] - recent_10[-1]['total_violations']
        avg_improvement = improvement / 10
        
        if avg_improvement < 0.3:  # Menos de 0.3 violations por iteration
            logging.info(f"⏹️ Low improvement rate ({avg_improvement:.2f}/iter) - stopping")
            return True
    
    # 4. Consistent worsening
    if len(self.optimization_history) >= 3:
        recent_3 = self.optimization_history[-3:]
        if all(recent_3[i]['total_violations'] >= recent_3[i-1]['total_violations'] 
               for i in range(1, 3)):
            logging.warning("⏹️ Violations increasing - stopping")
            return True
    
    return False
```

#### **B2. Redistribuciones Escalonadas**

**Modificar `_apply_forced_redistribution()` en `iterative_optimizer.py`:**

```python
def _calculate_redistribution_limit(self, violations: int, iteration: int):
    """
    Calcula límite de redistribuciones de forma escalada.
    
    ESTRATEGIA:
    - Iterations 1-10: Moderado (violations × 3-5)
    - Iterations 11-25: Agresivo (violations × 6-8)
    - Iterations 26-50: Muy agresivo (violations × 10-15)
    """
    if iteration <= 10:
        # Fase inicial: exploración moderada
        base = violations * 3
        max_limit = violations * 5
    elif iteration <= 25:
        # Fase media: incrementar agresividad
        base = violations * 6
        max_limit = violations * 8
    else:
        # Fase final: máxima agresividad
        base = violations * 10
        max_limit = violations * 15
    
    # Ajustar según gravedad
    if violations > 20:
        return max_limit
    else:
        return base
```

#### **B3. Reducir Número Máximo de Iteraciones**

```python
# ACTUAL: max_iterations = 50
# PROPUESTA: max_iterations = 30

# Con mejor reparto inicial, 30 iteraciones deberían ser suficientes
# Si el reparto inicial es bueno (< 15 violations), incluso menos
```

---

## 📊 Impacto Esperado

### **Mejoras en Reparto Inicial:**

| Métrica | Actual | Objetivo | Mejora |
|---------|--------|----------|--------|
| Shifts vacíos después de fase inicial | 5-15% | < 2% | 70%+ |
| Violaciones después de fase inicial | 30-35 | 10-15 | 55%+ |
| Workers con déficit > 10 shifts | 8-12 | 0-3 | 75%+ |
| Tiempo fase inicial | 5-8 min | 8-12 min | +50% tiempo OK |

### **Mejoras en Optimización:**

| Métrica | Actual | Objetivo | Mejora |
|---------|--------|----------|--------|
| Iteraciones necesarias | 50 | 15-25 | 50%+ |
| Redistributions por iteration | 140-180 | 50-100 | 40%+ |
| Tiempo optimización | 90 seg | 40-60 seg | 35%+ |
| Violaciones finales | 28-31 | 0-5 | 85%+ |

### **Beneficios Generales:**

✅ **Mejor calidad:** Reparto inicial más equilibrado y completo
✅ **Menos trabajo para optimizador:** Schedule inicial cercano al óptimo
✅ **Convergencia más rápida:** Menos iteraciones necesarias
✅ **Mejor estabilidad:** Menos cambios masivos en optimization
✅ **Tiempo similar o mejor:** Más tiempo inicial, menos tiempo optimization

---

## 🚀 Plan de Implementación

### **Prioridad 1: Mejorar Reparto Inicial (CRÍTICO)**

1. ✅ Implementar `current_fill_pass` tracking en `schedule_builder.py`
2. ✅ Modificar scoring para usar `current_fill_pass`
3. ✅ Crear `_fill_schedule_with_multiple_passes()`
4. ✅ Integrar en `_try_multiple_initial_distributions()`
5. ✅ Probar con dataset actual

### **Prioridad 2: Optimizar Iteraciones (IMPORTANTE)**

1. ✅ Implementar early stopping inteligente
2. ✅ Implementar redistribuciones escalonadas
3. ✅ Reducir max_iterations de 50 a 30
4. ✅ Probar con schedule mejorado de Prioridad 1

### **Prioridad 3: Fine Tuning (OPCIONAL)**

1. ✅ Ajustar thresholds basado en resultados
2. ✅ Optimizar número de intentos iniciales
3. ✅ Revisar scoring multipliers

---

## ❓ Decisiones Pendientes

1. **¿Cuántas pasadas por intento inicial?**
   - Opción A: 3 pasadas (rápido, menos exhaustivo)
   - Opción B: 4 pasadas (más lento, más exhaustivo)
   - **Recomendación:** Empezar con 3, evaluar resultados

2. **¿Bonuses en primera pasada?**
   - Opción A: 5000 (muy agresivo)
   - Opción B: 4000 (moderadamente agresivo)
   - **Recomendación:** 5000, el objetivo es llenar

3. **¿Max iterations para optimización?**
   - Opción A: 20 (conservador)
   - Opción B: 30 (balanceado)
   - **Recomendación:** 30, permite convergencia completa

4. **¿Mantener múltiples intentos iniciales?**
   - Opción A: Mantener 10-60 intentos
   - Opción B: Reducir a 5-30 intentos (con pasadas múltiples)
   - **Recomendación:** Reducir a 5-20, cada intento es más efectivo

---

## 📝 Notas Finales

- **Testing crítico:** Cada cambio debe probarse con dataset completo
- **Rollback plan:** Mantener versión actual como backup
- **Logging exhaustivo:** Para diagnosticar problemas
- **Métricas claras:** Definir KPIs de éxito antes de implementar

**¿Proceder con implementación?**
