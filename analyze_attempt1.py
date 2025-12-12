#!/usr/bin/env python3
"""
Analiza el Complete Attempt 1 desde el log test_120days_v3.log
Extrae: turnos asignados, distribución mensual, fines de semana
"""

import re
import json
from datetime import datetime, timedelta
from collections import defaultdict

def parse_log():
    """Parsea el log y extrae información del Attempt 1"""
    
    # Buscar sección del Attempt 1
    print("📋 Parseando log test_120days_v3.log...")
    
    with open('test_120days_v3.log', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar métricas finales del Attempt 1
    metrics_match = re.search(r'📊 Complete Attempt 1 Final Metrics:.*?Coverage: ([\d.]+)%.*?Empty Shifts: (\d+).*?Overall Score: ([\d.]+).*?Workload Imbalance: ([\d.]+).*?Weekend Imbalance: ([\d.]+)', content, re.DOTALL)
    
    if metrics_match:
        coverage = float(metrics_match.group(1))
        empty_shifts = int(metrics_match.group(2))
        score = float(metrics_match.group(3))
        workload_imb = float(metrics_match.group(4))
        weekend_imb = float(metrics_match.group(5))
        
        print(f"\n✅ Métricas del Attempt 1:")
        print(f"  Coverage: {coverage}%")
        print(f"  Empty Shifts: {empty_shifts}")
        print(f"  Overall Score: {score}")
        print(f"  Workload Imbalance: {workload_imb}")
        print(f"  Weekend Imbalance: {weekend_imb}")
    else:
        print("❌ No se encontraron métricas del Attempt 1")
        return None
    
    # Extraer asignaciones de turnos del log
    # Buscar mensajes de asignación durante el Attempt 1
    print("\n📊 Buscando asignaciones de turnos...")
    
    # Patrón para encontrar asignaciones: "Assigned Worker X to YYYY-MM-DD shift Y"
    assignments_pattern = r'Assigned Worker (\d+) to (\d{4}-\d{2}-\d{2}) shift (\d+)'
    
    # Buscar el inicio del Attempt 1
    attempt1_start = content.find('🎯 COMPLETE ATTEMPT 1')
    if attempt1_start == -1:
        print("❌ No se encontró inicio del Attempt 1")
        return None
    
    # Buscar el final (inicio del Attempt 2 o métricas finales)
    attempt1_end = content.find('🎯 COMPLETE ATTEMPT 2', attempt1_start)
    if attempt1_end == -1:
        attempt1_end = content.find('📊 Complete Attempt 1 Final Metrics:', attempt1_start) + 5000
    
    attempt1_content = content[attempt1_start:attempt1_end]
    
    # Extraer todas las asignaciones
    assignments = re.findall(assignments_pattern, attempt1_content)
    
    print(f"  Encontradas {len(assignments)} asignaciones en el log")
    
    if len(assignments) == 0:
        print("⚠️  No se encontraron asignaciones explícitas en el log")
        print("  Intentando método alternativo...")
        return analyze_from_state(attempt1_content)
    
    # Organizar asignaciones
    worker_shifts = defaultdict(list)
    date_shifts = defaultdict(list)
    
    for worker_id, date_str, shift_id in assignments:
        worker_id = int(worker_id)
        date = datetime.strptime(date_str, '%Y-%m-%d')
        shift_id = int(shift_id)
        
        worker_shifts[worker_id].append({
            'date': date,
            'shift_id': shift_id,
            'date_str': date_str
        })
        date_shifts[date_str].append((worker_id, shift_id))
    
    return {
        'metrics': {
            'coverage': coverage,
            'empty_shifts': empty_shifts,
            'score': score,
            'workload_imbalance': workload_imb,
            'weekend_imbalance': weekend_imb
        },
        'worker_shifts': dict(worker_shifts),
        'date_shifts': dict(date_shifts),
        'total_assignments': len(assignments)
    }

def analyze_from_state(attempt1_content):
    """Intenta extraer estado final desde mensajes de DEBUG"""
    
    # Buscar mensajes de "current: X, target: Y"
    current_pattern = r'Worker (\d+):.*?current[:\s]+(\d+).*?target[:\s]+(\d+)'
    matches = re.findall(current_pattern, attempt1_content, re.IGNORECASE)
    
    if not matches:
        print("❌ No se pudo extraer información de estado")
        return None
    
    print(f"  Encontrados {len(matches)} estados de trabajadores")
    
    worker_data = {}
    for worker_id, current, target in matches:
        worker_id = int(worker_id)
        if worker_id not in worker_data:
            worker_data[worker_id] = {
                'assigned': int(current),
                'target': int(target)
            }
    
    return {
        'worker_data': worker_data,
        'total_workers': len(worker_data)
    }

def load_config():
    """Carga configuración para obtener targets"""
    with open('schedule_config_test_real.json', 'r') as f:
        config = json.load(f)
    return config

def analyze_distribution(data):
    """Analiza distribución de turnos"""
    
    if not data:
        return
    
    print("\n" + "="*80)
    print("📊 ANÁLISIS DE DISTRIBUCIÓN DE TURNOS - ATTEMPT 1")
    print("="*80)
    
    # Cargar config para targets
    config = load_config()
    workers_config = config['workers_data']
    
    # Crear diccionario de targets y work_percentage
    targets = {}
    work_percentages = {}
    for w in workers_config:
        targets[int(w['id'])] = w.get('target_shifts', 0)
        work_percentages[int(w['id'])] = w.get('work_percentage', 100)
    
    if 'worker_data' in data:
        # Análisis desde estado
        worker_data = data['worker_data']
        
        print(f"\n👥 Distribución Global de Turnos:")
        print(f"   Total trabajadores analizados: {len(worker_data)}")
        print()
        
        # Agrupar por porcentaje de jornada
        workers_by_percentage = defaultdict(list)
        for w in workers_config:
            pct = w.get('work_percentage', 100)
            workers_by_percentage[pct].append(int(w['id']))
        
        violations_8 = []
        violations_10 = []
        violations_extreme = []
        
        for percentage in sorted(workers_by_percentage.keys()):
            worker_ids = workers_by_percentage[percentage]
            print(f"\n  📌 Trabajadores al {percentage}%:")
            print(f"     {'ID':<6} {'Asignados':<12} {'Target':<10} {'Desv.':<10} {'%':<10} {'Estado'}")
            print(f"     {'-'*6} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*20}")
            
            for worker_id in sorted(worker_ids):
                if worker_id in worker_data:
                    assigned = worker_data[worker_id]['assigned']
                    target = worker_data[worker_id]['target']
                    deviation = assigned - target
                    dev_pct = (deviation / target * 100) if target > 0 else 0
                    
                    if abs(dev_pct) <= 8:
                        status = "✅ Objetivo"
                        icon = "✅"
                    elif abs(dev_pct) <= 10:
                        status = "⚠️  Emergencia"
                        icon = "⚠️"
                        violations_8.append((worker_id, dev_pct, assigned, target))
                    elif abs(dev_pct) <= 15:
                        status = "🚨 Crítico"
                        icon = "🚨"
                        violations_10.append((worker_id, dev_pct, assigned, target))
                    else:
                        status = "❌ Extremo"
                        icon = "❌"
                        violations_extreme.append((worker_id, dev_pct, assigned, target))
                    
                    print(f"     {worker_id:<6} {assigned:<12} {target:<10} {deviation:+4d}      {dev_pct:+6.1f}%   {status}")
        
        # Resumen de violaciones
        print(f"\n" + "="*80)
        print(f"🎯 RESUMEN DE CUMPLIMIENTO DE TOLERANCIA:")
        print(f"="*80)
        
        total_workers = len(worker_data)
        within_8 = total_workers - len(violations_8) - len(violations_10) - len(violations_extreme)
        
        print(f"\n  ✅ Dentro de tolerancia objetivo (±8%):  {within_8}/{total_workers} trabajadores ({within_8/total_workers*100:.1f}%)")
        
        if violations_8:
            print(f"\n  ⚠️  Tolerancia emergencia (8-10%):       {len(violations_8)} trabajadores")
            for worker_id, dev_pct, assigned, target in violations_8:
                print(f"      Worker {worker_id}: {assigned}/{target} ({dev_pct:+.1f}%)")
        
        if violations_10:
            print(f"\n  🚨 Tolerancia crítica (10-15%):         {len(violations_10)} trabajadores")
            for worker_id, dev_pct, assigned, target in violations_10:
                print(f"      Worker {worker_id}: {assigned}/{target} ({dev_pct:+.1f}%)")
        
        if violations_extreme:
            print(f"\n  ❌ Violación extrema (>15%):            {len(violations_extreme)} trabajadores")
            for worker_id, dev_pct, assigned, target in violations_extreme:
                print(f"      Worker {worker_id}: {assigned}/{target} ({dev_pct:+.1f}%)")
        
        if not violations_10 and not violations_extreme:
            print(f"\n  🏆 TODOS LOS TRABAJADORES DENTRO DEL LÍMITE DE ±10%")
        
        return worker_data
    
    elif 'worker_shifts' in data:
        # Análisis desde asignaciones completas
        worker_shifts = data['worker_shifts']
        print(f"\n👥 Distribución Global desde {data['total_assignments']} asignaciones:")
        
        for worker_id in sorted(worker_shifts.keys()):
            shifts = worker_shifts[worker_id]
            assigned = len(shifts)
            target = targets.get(worker_id, 0)
            deviation = assigned - target
            dev_pct = (deviation / target * 100) if target > 0 else 0
            
            print(f"  Worker {worker_id}: {assigned} turnos (target: {target}, {dev_pct:+.1f}%)")

def analyze_monthly(data):
    """Analiza distribución mensual"""
    
    if not data or 'worker_shifts' not in data:
        print("\n⚠️  No hay datos suficientes para análisis mensual")
        return
    
    print("\n" + "="*80)
    print("📅 ANÁLISIS DE DISTRIBUCIÓN MENSUAL")
    print("="*80)
    
    worker_shifts = data['worker_shifts']
    
    # Organizar por mes
    monthly_data = defaultdict(lambda: defaultdict(int))
    
    for worker_id, shifts in worker_shifts.items():
        for shift in shifts:
            date = shift['date']
            month_key = date.strftime('%Y-%m')
            monthly_data[month_key][worker_id] += 1
    
    # Mostrar por mes
    for month in sorted(monthly_data.keys()):
        print(f"\n📆 {month}:")
        workers_month = monthly_data[month]
        for worker_id in sorted(workers_month.keys()):
            count = workers_month[worker_id]
            print(f"    Worker {worker_id}: {count} turnos")

def analyze_weekends(data):
    """Analiza distribución de fines de semana"""
    
    if not data or 'worker_shifts' not in data:
        print("\n⚠️  No hay datos suficientes para análisis de fines de semana")
        return
    
    print("\n" + "="*80)
    print("🏖️  ANÁLISIS DE TURNOS EN FIN DE SEMANA")
    print("="*80)
    
    worker_shifts = data['worker_shifts']
    weekend_counts = defaultdict(int)
    
    for worker_id, shifts in worker_shifts.items():
        weekend_shifts = [s for s in shifts if s['date'].weekday() in [5, 6]]  # Sábado=5, Domingo=6
        weekend_counts[worker_id] = len(weekend_shifts)
    
    total_weekend = sum(weekend_counts.values())
    
    print(f"\n  Total turnos de fin de semana asignados: {total_weekend}")
    print(f"\n  Distribución por trabajador:")
    
    for worker_id in sorted(weekend_counts.keys()):
        count = weekend_counts[worker_id]
        total = len(worker_shifts[worker_id])
        pct = (count / total * 100) if total > 0 else 0
        print(f"    Worker {worker_id}: {count} turnos fin de semana ({pct:.1f}% de sus {total} turnos)")

def main():
    print("="*80)
    print("ANÁLISIS DE COMPLETE ATTEMPT 1")
    print("="*80)
    
    # Parsear log
    data = parse_log()
    
    if not data:
        print("\n❌ No se pudo extraer información del log")
        return
    
    # Análisis de distribución
    analyze_distribution(data)
    
    # Análisis mensual
    analyze_monthly(data)
    
    # Análisis de fines de semana
    analyze_weekends(data)
    
    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80)

if __name__ == '__main__':
    main()
