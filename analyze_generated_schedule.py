#!/usr/bin/env python3
"""
Analiza el calendario generado leyendo directamente del scheduler
"""

import json
import sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Add the workspace to path
sys.path.insert(0, str(Path(__file__).parent))

from scheduler import Scheduler

def parse_date(date_str):
    """Parse fecha en formato DD-MM-YYYY o YYYY-MM-DD"""
    for fmt in ['%d-%m-%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"No se pudo parsear la fecha: {date_str}")

def analyze_generated_schedule():
    """Analiza el calendario generado desde el scheduler"""
    
    # Cargar configuración
    config_path = Path(__file__).parent / "schedule_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Crear scheduler y generar calendario
    print("Cargando calendario generado...")
    print()
    
    scheduler = Scheduler(config)
    
    # Verificar si hay un calendario generado
    if not scheduler.schedule or len(scheduler.schedule) == 0:
        print("❌ No hay calendario generado")
        print("Ejecuta primero: python test_scheduler_only.py")
        return
    
    workers = config.get('workers_data', config.get('workers', []))
    start_date = parse_date(config.get('start_date', config.get('schedule_config', {}).get('start_date')))
    end_date = parse_date(config.get('end_date', config.get('schedule_config', {}).get('end_date')))
    
    print("=" * 100)
    print("ANÁLISIS DE DISTRIBUCIÓN MENSUAL - CALENDARIO GENERADO")
    print("=" * 100)
    print(f"Periodo: {start_date.strftime('%d-%m-%Y')} a {end_date.strftime('%d-%m-%Y')}")
    print()
    
    # Generar lista de meses
    months = []
    current = start_date.replace(day=1)
    while current <= end_date:
        months.append((current.year, current.month))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    months = sorted(list(set(months)))
    
    # Nombres de meses
    month_names = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    # Contar asignaciones por trabajador y mes desde scheduler.worker_assignments
    worker_monthly_counts = defaultdict(lambda: defaultdict(int))
    
    for worker_id, dates in scheduler.worker_assignments.items():
        for date in dates:
            if start_date <= date <= end_date:
                month_key = (date.year, date.month)
                worker_monthly_counts[worker_id][month_key] += 1
    
    # Header
    print(f"{'Trabajador':<12} {'Target':<7} {'%':<5}", end='')
    for year, month in months:
        print(f" {month_names[month]}-{str(year)[2:]:<4}", end='')
    print(f" {'TOTAL':<6} {'Estado'}")
    print("-" * 100)
    
    # Crear un mapa de workers por ID
    workers_by_id = {w['id']: w for w in workers}
    
    # Analizar cada trabajador
    total_by_month = defaultdict(int)
    
    for worker_id in sorted(worker_monthly_counts.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        worker = workers_by_id.get(worker_id)
        if not worker:
            continue
            
        target = worker.get('target_shifts', 0)
        work_pct = worker.get('work_percentage', 100)
        
        # Mostrar fila
        print(f"{worker_id:<12} {target:<7} {work_pct:<5}", end='')
        
        total_assigned = 0
        for year, month in months:
            month_key = (year, month)
            count = worker_monthly_counts[worker_id].get(month_key, 0)
            total_assigned += count
            total_by_month[month_key] += count
            
            if count > 0:
                print(f" {count:<5}", end='')
            else:
                print(f" {'-':<5}", end='')
        
        # Estado
        if target > 0:
            diff = total_assigned - target
            if diff == 0:
                estado = "✓ OK"
            elif diff > 0:
                estado = f"↑ +{diff}"
            else:
                estado = f"↓ {diff}"
        else:
            estado = "-"
        
        print(f" {total_assigned:<6} {estado}")
    
    # Totales
    print("-" * 100)
    print(f"{'TOTAL':<12} {'':<7} {'':<5}", end='')
    grand_total = 0
    for year, month in months:
        month_key = (year, month)
        count = total_by_month[month_key]
        grand_total += count
        print(f" {count:<5}", end='')
    print(f" {grand_total:<6}")
    
    print()
    print("=" * 100)
    print()
    
    # Desglose mensual
    print("DESGLOSE MENSUAL DETALLADO")
    print("=" * 100)
    
    for year, month in months:
        month_key = (year, month)
        month_name = f"{month_names[month]} {year}"
        count = total_by_month[month_key]
        
        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]
        
        month_start = datetime(year, month, 1)
        month_end = datetime(year, month, days_in_month)
        
        actual_start = max(start_date, month_start)
        actual_end = min(end_date, month_end)
        
        if actual_start <= actual_end:
            days_in_period = (actual_end - actual_start).days + 1
            shifts_per_day = config.get('num_shifts', config.get('schedule_config', {}).get('num_shifts', 4))
            expected_shifts = days_in_period * shifts_per_day
            coverage = (count/expected_shifts*100) if expected_shifts > 0 else 0
            
            print(f"{month_name:<12} | Días: {days_in_period:>2} | "
                  f"Guardias asignadas: {count:>3} | "
                  f"Esperadas: {expected_shifts:>3} | "
                  f"Cobertura: {coverage:>5.1f}%")
    
    print()
    print("=" * 100)
    print()
    
    # Resumen de desviaciones
    print("RESUMEN DE DESVIACIONES")
    print("=" * 100)
    
    workers_ok = []
    workers_excess = []
    workers_deficit = []
    
    for worker_id in sorted(worker_monthly_counts.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        worker = workers_by_id.get(worker_id)
        if not worker:
            continue
            
        target = worker.get('target_shifts', 0)
        if target == 0:
            continue
            
        total_assigned = sum(worker_monthly_counts[worker_id].values())
        diff = total_assigned - target
        
        if diff == 0:
            workers_ok.append((worker_id, total_assigned, target))
        elif diff > 0:
            workers_excess.append((worker_id, total_assigned, target, diff))
        else:
            workers_deficit.append((worker_id, total_assigned, target, diff))
    
    print(f"✓ Workers en target: {len(workers_ok)}")
    print(f"↑ Workers con exceso: {len(workers_excess)}")
    print(f"↓ Workers con déficit: {len(workers_deficit)}")
    print()
    
    if workers_deficit:
        print("WORKERS CON DÉFICIT:")
        for worker_id, assigned, target, diff in sorted(workers_deficit, key=lambda x: x[3]):
            print(f"  {worker_id:<12} | Asignado: {assigned:>3} | Target: {target:>3} | Déficit: {diff:>+4}")
        print()
    
    if workers_excess:
        print("WORKERS CON EXCESO:")
        for worker_id, assigned, target, diff in sorted(workers_excess, key=lambda x: x[3], reverse=True):
            print(f"  {worker_id:<12} | Asignado: {assigned:>3} | Target: {target:>3} | Exceso: {diff:>+4}")
    
    print()

if __name__ == "__main__":
    analyze_generated_schedule()
