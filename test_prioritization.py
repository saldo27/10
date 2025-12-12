#!/usr/bin/env python3
"""
Test para verificar que workers con déficit reciben prioridad correcta
"""

import logging
from datetime import datetime
from scheduler import Scheduler

# Configurar logging para ver solo INFO y WARNING
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

# Suprimir DEBUG de módulos internos
logging.getLogger('scheduler').setLevel(logging.WARNING)
logging.getLogger('schedule_builder').setLevel(logging.WARNING)
logging.getLogger('scheduler_core').setLevel(logging.WARNING)

print("=" * 80)
print("TEST: Verificación de Priorización por Déficit")
print("=" * 80)
print()

# Configuración simple con 5 workers 100%
config = {
    'start_date': datetime(2025, 11, 1),
    'end_date': datetime(2025, 11, 30),  # Solo 1 mes para test rápido
    'num_shifts': 4,
    'workers_data': [
        {'id': '1', 'name': 'Worker1', 'work_percentage': 100, 'incompatible_with': []},
        {'id': '2', 'name': 'Worker2', 'work_percentage': 100, 'incompatible_with': []},
        {'id': '3', 'name': 'Worker3', 'work_percentage': 100, 'incompatible_with': []},
        {'id': '4', 'name': 'Worker4', 'work_percentage': 100, 'incompatible_with': []},
        {'id': '5', 'name': 'Worker5', 'work_percentage': 100, 'incompatible_with': []},
    ],
    'max_shifts_per_worker': 999,
    'gap_between_shifts': 1,
    'max_consecutive_weekends': 2,
    'holidays': [],
    'schedule_days': [],
    'constraints': {
        'enforce_7_14_pattern': False,
        'max_shifts_per_month': 999
    }
}

scheduler = Scheduler(config)

print("Generando horario...")
result = scheduler.generate_schedule()

if result['success']:
    print("\n✅ Horario generado exitosamente")
    print()
    
    # Analizar distribución
    print("DISTRIBUCIÓN DE TURNOS:")
    print("-" * 40)
    
    worker_counts = {}
    for worker_id in ['1', '2', '3', '4', '5']:
        count = len(scheduler.worker_assignments.get(worker_id, set()))
        worker_counts[worker_id] = count
        target = scheduler.target_shifts.get(worker_id, 0)
        deviation = ((count - target) / target * 100) if target > 0 else 0
        print(f"Worker {worker_id}: {count:2d} turnos (target: {target}, desv: {deviation:+.1f}%)")
    
    print()
    
    # Verificar que no hay grandes desviaciones
    counts = list(worker_counts.values())
    max_count = max(counts)
    min_count = min(counts)
    diff = max_count - min_count
    
    print(f"Diferencia máxima: {diff} turnos")
    print()
    
    if diff <= 2:
        print("✅ CORRECTO: Distribución equilibrada (diff ≤ 2)")
    elif diff <= 4:
        print("⚠️  ACEPTABLE: Distribución razonable (diff ≤ 4)")
    else:
        print(f"❌ ERROR: Distribución muy desigual (diff = {diff})")
        print("   El sistema NO está priorizando workers con déficit")
    
else:
    print("\n❌ Error generando horario")
    if result.get('errors'):
        for error in result['errors']:
            print(f"  - {error}")

print()
