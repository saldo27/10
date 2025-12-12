#!/usr/bin/env python3
"""
Análisis de Deadlock - Identifica qué restricciones están bloqueando la asignación
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_deadlock():
    """Analiza el deadlock en el test_real_scenario"""
    
    print("=" * 80)
    print("ANÁLISIS DE DEADLOCK")
    print("=" * 80)
    print()
    
    # Cargar configuración
    with open('schedule_config_test_real.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Periodo de análisis
    start_date_str = config['start_date']
    end_date_str = config['end_date']
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    days = (end_date - start_date).days + 1
    
    workers = config.get('workers_data', [])
    schedule_days = config.get('schedule_days', [])
    
    print(f"Período: {start_date.strftime('%d-%m-%Y')} a {end_date.strftime('%d-%m-%Y')}")
    print(f"Total días: {days}")
    print()
    
    # Analizar capacidad por worker
    print("=" * 80)
    print("1. CAPACIDAD DE ASIGNACIÓN POR WORKER")
    print("=" * 80)
    print()
    
    workers_by_capacity = []
    
    for worker in workers:
        worker_id = worker['id']
        work_pct = worker.get('work_percentage', 100)
        base_target = days // 3  # ~40 días para 120 días
        adjusted_target = round(base_target * work_pct / 100)
        
        # Contar días obligatorios
        mandatory_count = 0
        for day_config in schedule_days:
            day_date = datetime.strptime(day_config['date'], '%Y-%m-%d')
            if start_date <= day_date <= end_date:
                if worker_id in day_config.get('mandatory', []):
                    mandatory_count += 1
        
        # Contar días excluidos
        excluded_count = 0
        for exclusion in worker.get('exclusions', []):
            excl_date = datetime.strptime(exclusion['date'], '%Y-%m-%d')
            if start_date <= excl_date <= end_date:
                excluded_count += 1
        
        # Calcular margen
        available_days = days - excluded_count
        margin = available_days - adjusted_target
        margin_pct = (margin / adjusted_target * 100) if adjusted_target > 0 else 0
        
        workers_by_capacity.append({
            'id': worker_id,
            'name': worker['name'],
            'work_pct': work_pct,
            'target': adjusted_target,
            'mandatory': mandatory_count,
            'excluded': excluded_count,
            'available': available_days,
            'margin': margin,
            'margin_pct': margin_pct,
            'ratio': available_days / adjusted_target if adjusted_target > 0 else 0
        })
    
    # Ordenar por menor margen
    workers_by_capacity.sort(key=lambda x: x['margin_pct'])
    
    print(f"{'Worker':<20} {'%Jor':<5} {'Target':<7} {'Mand':<5} {'Excl':<5} {'Disp':<6} {'Marg':<6} {'%Marg':<8} {'Ratio':<6}")
    print("-" * 80)
    
    critical_workers = []
    for w in workers_by_capacity:
        status = ""
        if w['margin_pct'] < 50:
            status = " ⚠️ CRÍTICO"
            critical_workers.append(w)
        elif w['margin_pct'] < 100:
            status = " ⚠️ AJUSTADO"
        
        print(f"{w['name']:<20} {w['work_pct']:<5} {w['target']:<7} {w['mandatory']:<5} "
              f"{w['excluded']:<5} {w['available']:<6} {w['margin']:<6} "
              f"{w['margin_pct']:<7.1f}% {w['ratio']:<6.2f}{status}")
    
    print()
    print(f"Workers críticos (margen < 50%): {len(critical_workers)}")
    print()
    
    # Analizar incompatibilidades
    print("=" * 80)
    print("2. ANÁLISIS DE INCOMPATIBILIDADES")
    print("=" * 80)
    print()
    
    incompatibility_counts = defaultdict(int)
    incompatibility_matrix = defaultdict(set)
    workers_dict = {w['id']: w for w in workers}
    
    for worker in workers:
        worker_id = worker['id']
        incompatibles = worker.get('incompatible_with', [])
        incompatibility_counts[worker_id] = len(incompatibles)
        for inc_id in incompatibles:
            incompatibility_matrix[worker_id].add(inc_id)
    
    # Encontrar grupos de incompatibilidad
    print("Workers con más incompatibilidades:")
    sorted_incompat = sorted(incompatibility_counts.items(), key=lambda x: x[1], reverse=True)
    
    for worker_id, count in sorted_incompat[:10]:
        if count > 0:
            worker_name = workers_dict[worker_id]['name']
            incompatibles = [workers_dict[inc_id]['name'] for inc_id in workers_dict[worker_id].get('incompatible_with', [])]
            print(f"  {worker_name}: {count} incompatibles")
            print(f"    → {', '.join(incompatibles[:5])}")
    
    print()
    
    # Analizar restricciones de días obligatorios
    print("=" * 80)
    print("3. ANÁLISIS DE DÍAS OBLIGATORIOS")
    print("=" * 80)
    print()
    
    mandatory_by_date = defaultdict(list)
    for day_config in schedule_days:
        day_date = datetime.strptime(day_config['date'], '%Y-%m-%d')
        if start_date <= day_date <= end_date:
            mandatory = day_config.get('mandatory', [])
            if mandatory:
                mandatory_by_date[day_config['date']] = mandatory
    
    print(f"Total días con asignaciones obligatorias: {len(mandatory_by_date)}")
    print()
    
    # Encontrar conflictos de incompatibilidad en días obligatorios
    conflicts = []
    for date, mandatory_ids in mandatory_by_date.items():
        for i, worker1_id in enumerate(mandatory_ids):
            for worker2_id in mandatory_ids[i+1:]:
                if worker2_id in incompatibility_matrix[worker1_id]:
                    conflicts.append({
                        'date': date,
                        'worker1': workers_dict[worker1_id]['name'],
                        'worker2': workers_dict[worker2_id]['name']
                    })
    
    if conflicts:
        print(f"⚠️ CONFLICTOS DETECTADOS: {len(conflicts)} días con workers incompatibles obligatorios")
        print()
        for conflict in conflicts[:10]:
            print(f"  {conflict['date']}: {conflict['worker1']} ⚔️ {conflict['worker2']}")
        if len(conflicts) > 10:
            print(f"  ... y {len(conflicts) - 10} conflictos más")
    else:
        print("✅ No hay conflictos de incompatibilidad en días obligatorios")
    
    print()
    
    # Analizar patrón 7/14
    print("=" * 80)
    print("4. ANÁLISIS DE RESTRICCIÓN 7/14")
    print("=" * 80)
    print()
    
    constraints = config.get('constraints', {})
    pattern_strict = constraints.get('pattern_7_14_strict', False)
    pattern_enabled = constraints.get('enforce_7_14_pattern', False)
    
    print(f"Patrón 7/14 habilitado: {pattern_enabled}")
    print(f"Patrón 7/14 estricto: {pattern_strict}")
    print()
    
    if pattern_enabled:
        print("⚠️ IMPACTO: Cada worker solo puede trabajar el mismo día de la semana")
        print("  - Limita a ~17 turnos por worker en 120 días")
        print(f"  - Workers con target > 17: ", end="")
        
        high_target_workers = [w for w in workers_by_capacity if w['target'] > 17]
        print(f"{len(high_target_workers)} workers")
        
        if high_target_workers:
            for w in high_target_workers[:5]:
                print(f"    • {w['name']}: target={w['target']}, límite 7/14≈17")
    
    print()
    
    # Analizar límites mensuales
    print("=" * 80)
    print("5. ANÁLISIS DE LÍMITES MENSUALES")
    print("=" * 80)
    print()
    
    monthly_max = constraints.get('max_shifts_per_month', 999)
    print(f"Límite mensual configurado: {monthly_max} turnos/mes")
    print()
    
    if monthly_max < 999:
        print(f"⚠️ IMPACTO: Máximo {monthly_max * 4} turnos en 4 meses")
        print(f"  - Workers que pueden exceder: ", end="")
        
        affected_workers = [w for w in workers_by_capacity if w['target'] > monthly_max * 4]
        print(f"{len(affected_workers)} workers")
        
        if affected_workers:
            for w in affected_workers[:5]:
                print(f"    • {w['name']}: target={w['target']}, límite mensual={monthly_max * 4}")
    
    print()
    
    # Calcular probabilidad de deadlock
    print("=" * 80)
    print("6. DIAGNÓSTICO DE DEADLOCK")
    print("=" * 80)
    print()
    
    deadlock_factors = []
    
    # Factor 1: Workers críticos
    if len(critical_workers) > 5:
        deadlock_factors.append(f"🔴 {len(critical_workers)} workers con margen < 50%")
    
    # Factor 2: Conflictos de incompatibilidad
    if conflicts:
        deadlock_factors.append(f"🔴 {len(conflicts)} conflictos de incompatibilidad en días obligatorios")
    
    # Factor 3: Patrón 7/14 con targets altos
    if pattern_enabled and len(high_target_workers) > 0:
        deadlock_factors.append(f"🔴 Patrón 7/14 limita {len(high_target_workers)} workers")
    
    # Factor 4: Límites mensuales restrictivos
    if monthly_max < 999 and len(affected_workers) > 0:
        deadlock_factors.append(f"🔴 Límite mensual afecta {len(affected_workers)} workers")
    
    if deadlock_factors:
        print("CAUSAS DETECTADAS DEL DEADLOCK:")
        print()
        for factor in deadlock_factors:
            print(f"  {factor}")
        print()
        print("CONCLUSIÓN: ❌ La configuración actual tiene alta probabilidad de deadlock")
        print()
        print("RECOMENDACIONES:")
        print("  1. Reducir días obligatorios conflictivos")
        print("  2. Revisar incompatibilidades (¿son todas necesarias?)")
        print("  3. Si patrón 7/14 es obligatorio, reducir targets de workers afectados")
        print("  4. Considerar aumentar límite mensual si es posible")
    else:
        print("✅ No se detectaron causas obvias de deadlock")
        print("   El sistema debería poder completar la asignación")
    
    print()

if __name__ == "__main__":
    analyze_deadlock()
