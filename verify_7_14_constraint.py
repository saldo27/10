#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de verificación: Constraint 7/14 días
Verifica que ningún trabajador tenga turnos en el mismo día de la semana
separados por exactamente 7 o 14 días
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict

def verify_7_14_constraint(schedule_file):
    print("=" * 80)
    print("VERIFICACIÓN DE CONSTRAINT 7/14 DÍAS")
    print("=" * 80)
    print()
    
    # Cargar schedule
    try:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
    except Exception as e:
        print(f"Error al cargar {schedule_file}: {e}")
        return False
    
    # Organizar asignaciones por trabajador
    worker_assignments = defaultdict(list)
    
    for date_str, shifts in schedule.items():
        if not isinstance(shifts, list):
            continue
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            continue
        
        for shift_idx, worker_id in enumerate(shifts):
            if worker_id and worker_id != 0:
                worker_assignments[worker_id].append(date)
    
    # Ordenar fechas para cada trabajador
    for worker_id in worker_assignments:
        worker_assignments[worker_id].sort()
    
    # Verificar patrón 7/14 para cada trabajador
    violations = []
    
    for worker_id, dates in sorted(worker_assignments.items()):
        if len(dates) < 2:
            continue
        
        for i, date1 in enumerate(dates):
            for date2 in dates[i+1:]:
                days_diff = abs((date2 - date1).days)
                
                # Verificar si es patrón 7 o 14 días con mismo día de la semana
                if (days_diff == 7 or days_diff == 14) and date1.weekday() == date2.weekday():
                    weekday_name = date1.strftime('%A')
                    violations.append({
                        'worker_id': worker_id,
                        'date1': date1,
                        'date2': date2,
                        'days_diff': days_diff,
                        'weekday': weekday_name
                    })
    
    # Reportar resultados
    if violations:
        print(f"❌ ENCONTRADAS {len(violations)} VIOLACIONES del patrón 7/14:\n")
        
        for v in violations:
            print(f"Worker {v['worker_id']:2d}: {v['weekday']} {v['date1'].strftime('%Y-%m-%d')} → "
                  f"{v['weekday']} {v['date2'].strftime('%Y-%m-%d')} ({v['days_diff']} días)")
        
        print()
        print("=" * 80)
        print("RESUMEN:")
        print(f"Total violaciones: {len(violations)}")
        print(f"Trabajadores afectados: {len(set(v['worker_id'] for v in violations))}")
        print("=" * 80)
        return False
    else:
        print("✅ NO SE ENCONTRARON VIOLACIONES del patrón 7/14")
        print()
        print(f"Verificados {len(worker_assignments)} trabajadores")
        total_shifts = sum(len(dates) for dates in worker_assignments.values())
        print(f"Total turnos verificados: {total_shifts}")
        print()
        print("=" * 80)
        print("✓ Constraint 7/14 RESPETADA CORRECTAMENTE")
        print("=" * 80)
        return True

if __name__ == "__main__":
    import sys
    import glob
    
    # Buscar el schedule más reciente si no se especifica uno
    if len(sys.argv) > 1:
        schedule_file = sys.argv[1]
    else:
        # Buscar en historical_data
        files = glob.glob("./historical_data/schedule_data_*.json")
        if files:
            schedule_file = max(files, key=lambda f: f.split('_')[-1])
            print(f"Usando schedule más reciente: {schedule_file}\n")
        else:
            print("ERROR: No se encontró ningún archivo de schedule")
            sys.exit(1)
    
    success = verify_7_14_constraint(schedule_file)
    sys.exit(0 if success else 1)
