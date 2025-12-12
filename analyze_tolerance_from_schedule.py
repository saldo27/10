#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analiza un archivo schedule JSON para verificar límites de tolerancia ±12%
"""

import json
import sys
from datetime import datetime
from collections import defaultdict

def analyze_schedule_tolerance(schedule_file):
    print("=" * 80)
    print("ANÁLISIS DE TOLERANCIAS EN SCHEDULE")
    print("=" * 80)
    
    # Cargar el schedule
    with open(schedule_file, 'r', encoding='utf-8') as f:
        schedule = json.load(f)
    
    # Cargar la configuración
    with open('schedule_config_test_real.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Contar turnos por trabajador
    shifts_by_worker = defaultdict(int)
    
    for date_str, day_schedule in schedule.items():
        # Saltar claves de metadatos
        if not isinstance(day_schedule, list):
            continue
        for worker_id in day_schedule:
            if worker_id is not None and worker_id != 0:
                shifts_by_worker[worker_id] += 1
    
    # Obtener datos de trabajadores
    workers_data = config['workers']
    
    # Calcular días totales
    start_date = datetime.strptime(config['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(config['end_date'], '%Y-%m-%d')
    total_days = (end_date - start_date).days + 1
    num_shifts = config['num_shifts']
    
    print(f"Período: {config['start_date']} a {config['end_date']}")
    print(f"Total días: {total_days}")
    print(f"Turnos/día: {num_shifts}")
    print(f"Total posiciones: {total_days * num_shifts}")
    print()
    
    # Analizar cada trabajador
    violations = []
    within_obj = []
    outside_obj_within_limit = []
    
    tolerance_obj = 0.10  # ±10% objetivo
    tolerance_limit = 0.12  # ±12% límite absoluto
    
    for worker_id, worker_data in sorted(workers_data.items(), key=lambda x: int(x[0])):
        worker_id = int(worker_id)
        shifts_assigned = shifts_by_worker.get(worker_id, 0)
        work_pct = worker_data.get('work_percentage', 100)
        
        # Calcular target
        base_target = (total_days * work_pct) / 100.0
        target = round(base_target)
        
        # Calcular tolerancias ajustadas para part-time
        if work_pct < 100:
            adj_tol_obj = max(0.05, tolerance_obj * (work_pct / 100.0))
            adj_tol_limit = max(0.05, tolerance_limit * (work_pct / 100.0))
        else:
            adj_tol_obj = tolerance_obj
            adj_tol_limit = tolerance_limit
        
        # Rangos
        min_obj = round(target * (1 - adj_tol_obj))
        max_obj = round(target * (1 + adj_tol_obj))
        min_limit = round(target * (1 - adj_tol_limit))
        max_limit = round(target * (1 + adj_tol_limit))
        
        # Calcular desviación
        if target > 0:
            deviation = ((shifts_assigned - target) / target) * 100
        else:
            deviation = 0
        
        # Clasificar
        status = ""
        if min_limit <= shifts_assigned <= max_limit:
            if min_obj <= shifts_assigned <= max_obj:
                status = "✅ DENTRO"
                within_obj.append((worker_id, worker_data, shifts_assigned, target, deviation))
            else:
                status = "⚠️ FUERA OBJ"
                outside_obj_within_limit.append((worker_id, worker_data, shifts_assigned, target, deviation))
        else:
            status = "❌ VIOLACIÓN"
            violations.append((worker_id, worker_data, shifts_assigned, target, deviation))
        
        # Imprimir detalle
        print(f"{status} Worker {worker_id:2d} ({work_pct:3.0f}%): {shifts_assigned:2d} turnos (target: {target:2d}, "
              f"rango obj: {min_obj}-{max_obj}, LÍMITE: {min_limit}-{max_limit}, desv: {deviation:+.1f}%)")
    
    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"✅ Dentro de ±10% objetivo: {len(within_obj)} trabajadores")
    print(f"⚠️ Fuera de ±10% pero dentro de ±12% límite: {len(outside_obj_within_limit)} trabajadores")
    print(f"❌ VIOLACIONES de ±12% LÍMITE ABSOLUTO: {len(violations)} trabajadores")
    print()
    
    if violations:
        print("DETALLE DE VIOLACIONES:")
        for worker_id, worker_data, shifts, target, deviation in violations:
            work_pct = worker_data.get('work_percentage', 100)
            print(f"  - Worker {worker_id} ({work_pct}%): {shifts} turnos (target: {target}, desviación: {deviation:+.1f}%)")
        print()
        return False
    else:
        print("🎉 ¡ÉXITO! TODOS los trabajadores están dentro del límite absoluto de ±12%")
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        schedule_file = sys.argv[1]
    else:
        # Buscar el schedule más reciente
        import glob
        import os
        schedule_files = glob.glob("schedule_complete_*.json")
        if not schedule_files:
            print("ERROR: No se encontró ningún archivo schedule_complete_*.json")
            sys.exit(1)
        schedule_file = max(schedule_files, key=os.path.getmtime)
        print(f"Usando schedule más reciente: {schedule_file}\n")
    
    success = analyze_schedule_tolerance(schedule_file)
    sys.exit(0 if success else 1)
