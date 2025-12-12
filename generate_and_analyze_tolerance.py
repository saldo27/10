#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generación rápida de schedule para test de tolerancias
CON LOGGING COMPLETAMENTE SILENCIADO
"""

import sys
import json
import logging
from datetime import datetime
from scheduler import Scheduler
from scheduler_core import SchedulerCore

# SILENCIAR TODO EL LOGGING
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in logging.Logger.manager.loggerDict:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

def main():
    print("Generando schedule con tolerancias ±10%/±12%...")
    print()
    
    # Cargar configuración
    with open('schedule_config_test_real.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Convertir fechas
    config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d')
    config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d')
    
    if 'holidays' in config and config['holidays']:
        config['holidays'] = [datetime.strptime(h, '%Y-%m-%d') if isinstance(h, str) else h 
                              for h in config['holidays']]
    
    # Crear scheduler
    scheduler = Scheduler(config)
    scheduler_core = SchedulerCore(scheduler)
    
    # Ejecutar generación
    print(f"Ejecutando generación...")
    print(f"- 29 trabajadores")
    print(f"- {(scheduler.end_date - scheduler.start_date).days + 1} días")
    print(f"- {scheduler.num_shifts} turnos/día")
    print(f"- max_improvement_loops: 30")
    print()
    
    start_time = datetime.now()
    success = scheduler_core.orchestrate_schedule_generation(
        max_improvement_loops=30,  # Reducido para rapidez
        max_complete_attempts=1
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"\nCompletado en {duration:.1f}s")
    
    if success:
        # Guardar schedule - convertir dates a strings
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'schedule_test_tolerance_{timestamp}.json'
        
        # Convertir claves datetime a strings
        schedule_serializable = {}
        for date_key, shifts in scheduler.schedule.items():
            if isinstance(date_key, datetime):
                date_str = date_key.strftime('%Y-%m-%d')
            else:
                date_str = str(date_key)
            schedule_serializable[date_str] = shifts
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schedule_serializable, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n✅ Schedule guardado: {output_file}")
        return output_file
    else:
        print("\n❌ Error: No se pudo generar el schedule")
        return None

if __name__ == "__main__":
    output_file = main()
    if output_file:
        print(f"\nEjecutando análisis de tolerancias...\n")
        import subprocess
        subprocess.run([sys.executable, 'analyze_tolerance_from_schedule.py', output_file])
