#!/usr/bin/env python3
"""
Analiza la distribución mensual de guardias por trabajador
"""

import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path

def load_config():
    """Carga la configuración del scheduler"""
    config_path = Path(__file__).parent / "schedule_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_date(date_str):
    """Parse fecha en formato DD-MM-YYYY o YYYY-MM-DD"""
    for fmt in ['%d-%m-%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"No se pudo parsear la fecha: {date_str}")

def get_work_periods(worker):
    """Obtiene los periodos de trabajo de un trabajador"""
    work_periods_str = worker.get('work_periods', '')
    if not work_periods_str:
        return []
    
    periods = []
    # Separar por punto y coma
    for period_str in work_periods_str.split(';'):
        period_str = period_str.strip()
        if not period_str:
            continue
        
        # Separar inicio y fin
        if ' - ' in period_str:
            parts = period_str.split(' - ')
            if len(parts) == 2:
                try:
                    start = parse_date(parts[0].strip())
                    end = parse_date(parts[1].strip())
                    periods.append((start, end))
                except ValueError as e:
                    print(f"Error parseando periodo '{period_str}': {e}")
    
    return periods

def is_date_in_work_periods(date, periods):
    """Verifica si una fecha está dentro de los periodos de trabajo"""
    if not periods:
        return True  # Sin periodos especificados = disponible siempre
    
    for start, end in periods:
        if start <= date <= end:
            return True
    return False

def get_unavailable_dates(worker):
    """Obtiene las fechas no disponibles de un trabajador"""
    unavailable_str = worker.get('unavailable_days', '')
    if not unavailable_str:
        return set()
    
    dates = set()
    for date_str in unavailable_str.replace(';', ',').split(','):
        date_str = date_str.strip()
        if date_str:
            try:
                dates.add(parse_date(date_str))
            except ValueError:
                pass
    
    return dates

def get_mandatory_dates(worker):
    """Obtiene las fechas mandatory de un trabajador"""
    mandatory_str = worker.get('mandatory_days', '')
    if not mandatory_str:
        return set()
    
    dates = set()
    for date_str in mandatory_str.replace(';', ',').split(','):
        date_str = date_str.strip()
        if date_str:
            try:
                dates.add(parse_date(date_str))
            except ValueError:
                pass
    
    return dates

def analyze_monthly_distribution():
    """Analiza la distribución mensual de guardias"""
    config = load_config()
    workers = config.get('workers_data', config.get('workers', []))
    
    # Parsear fechas del periodo
    start_date = parse_date(config.get('start_date', config.get('schedule_config', {}).get('start_date')))
    end_date = parse_date(config.get('end_date', config.get('schedule_config', {}).get('end_date')))
    
    print("=" * 100)
    print("ANÁLISIS DE DISTRIBUCIÓN MENSUAL DE GUARDIAS")
    print("=" * 100)
    print(f"Periodo: {start_date.strftime('%d-%m-%Y')} a {end_date.strftime('%d-%m-%Y')}")
    print()
    
    # Generar lista de meses en el periodo
    months = []
    current = start_date.replace(day=1)
    while current <= end_date:
        months.append((current.year, current.month))
        # Siguiente mes
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Eliminar duplicados y ordenar
    months = sorted(list(set(months)))
    
    # Header de la tabla
    month_names = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    print(f"{'Trabajador':<12} {'Target':<7} {'%':<5}", end='')
    for year, month in months:
        print(f" {month_names[month]}-{str(year)[2:]:<4}", end='')
    print(f" {'TOTAL':<6} {'Mandatory':<9} {'Estado'}")
    print("-" * 100)
    
    # Analizar cada trabajador
    total_by_month = defaultdict(int)
    
    for worker in sorted(workers, key=lambda w: w['id']):
        worker_id = worker['id']
        target = worker.get('target_shifts', 0)
        work_pct = worker.get('work_percentage', 100)
        
        # Obtener datos del trabajador
        work_periods = get_work_periods(worker)
        unavailable_dates = get_unavailable_dates(worker)
        mandatory_dates = get_mandatory_dates(worker)
        
        # Contar guardias por mes
        monthly_counts = defaultdict(int)
        
        # Contar mandatory por mes
        for date in mandatory_dates:
            if start_date <= date <= end_date:
                month_key = (date.year, date.month)
                monthly_counts[month_key] += 1
        
        # Mostrar fila del trabajador
        print(f"{worker_id:<12} {target:<7} {work_pct:<5}", end='')
        
        total_assigned = 0
        for year, month in months:
            month_key = (year, month)
            count = monthly_counts[month_key]
            total_assigned += count
            total_by_month[month_key] += count
            
            if count > 0:
                print(f" {count:<5}", end='')
            else:
                print(f" {'-':<5}", end='')
        
        # Total y mandatory
        mandatory_count = len(mandatory_dates)
        
        # Estado (comparar con target)
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
        
        print(f" {total_assigned:<6} {mandatory_count:<9} {estado}")
    
    # Línea de totales
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
    
    # Análisis por mes
    print("DESGLOSE MENSUAL DETALLADO")
    print("=" * 100)
    
    for year, month in months:
        month_key = (year, month)
        month_name = f"{month_names[month]} {year}"
        count = total_by_month[month_key]
        
        # Contar días laborables en el mes
        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]
        
        # Calcular días del mes dentro del periodo
        month_start = datetime(year, month, 1)
        month_end = datetime(year, month, days_in_month)
        
        actual_start = max(start_date, month_start)
        actual_end = min(end_date, month_end)
        
        if actual_start <= actual_end:
            days_in_period = (actual_end - actual_start).days + 1
            
            # Calcular guardias esperadas (4 guardias/día)
            shifts_per_day = config.get('num_shifts', config.get('schedule_config', {}).get('num_shifts', 4))
            expected_shifts = days_in_period * shifts_per_day
            
            print(f"{month_name:<12} | Días: {days_in_period:>2} | "
                  f"Guardias asignadas: {count:>3} | "
                  f"Esperadas: {expected_shifts:>3} | "
                  f"Cobertura: {count/expected_shifts*100:>5.1f}%" if expected_shifts > 0 else "N/A")
    
    print()
    print("=" * 100)
    
    # Resumen de workers con problemas
    print()
    print("WORKERS CON DESVIACIONES DEL TARGET")
    print("=" * 100)
    
    for worker in sorted(workers, key=lambda w: w['id']):
        worker_id = worker['id']
        target = worker.get('target_shifts', 0)
        mandatory_dates = get_mandatory_dates(worker)
        
        # Contar solo mandatory dentro del periodo
        mandatory_count = sum(1 for d in mandatory_dates if start_date <= d <= end_date)
        
        if target > 0:
            diff = mandatory_count - target
            if diff != 0:
                status = "EXCESO" if diff > 0 else "DÉFICIT"
                print(f"{worker_id:<12} | Target: {target:>3} | Asignado: {mandatory_count:>3} | "
                      f"Diferencia: {diff:>+4} | {status}")
    
    print()

if __name__ == "__main__":
    analyze_monthly_distribution()
