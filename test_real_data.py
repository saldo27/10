#!/usr/bin/env python3
"""
Script de prueba para validar protección de mandatory shifts con datos reales.

Este script:
1. Carga tu configuración real de trabajadores (schedule_config.json)
2. Ejecuta el scheduler con las correcciones aplicadas
3. Genera logs con marcadores 🔒 para verificación
4. Ejecuta el script de verificación automáticamente

Uso:
    python test_real_data.py
    
Requisitos:
    - Archivo schedule_config.json con tus trabajadores reales
    - O modifica la sección WORKER_DATA para incluir tus datos
"""

import logging
import json
import os
from datetime import datetime, timedelta
from scheduler import Scheduler

# Configurar logging para ver los emojis 🔒
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_real_data.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_config_from_file(filepath='schedule_config.json'):
    """Carga configuración desde archivo JSON si existe"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logging.info(f"✅ Configuración cargada desde {filepath}")
        return config
    else:
        logging.warning(f"⚠️ No se encontró {filepath}")
        return None

def create_test_config():
    """
    Crea configuración de prueba.
    
    PERSONALIZA ESTA FUNCIÓN con tus datos reales:
    - Copia y pega los datos de tus trabajadores
    - Ajusta fechas de mandatory_days
    - Modifica targets según tu caso
    """
    
    # Periodo de prueba (ajusta según necesites)
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 1, 31)
    
    # EJEMPLO: Configuración básica
    # REEMPLAZA esto con tus trabajadores reales
    workers_data = [
        {
            'id': '1',
            'name': 'Trabajador 1',
            'target_shifts': 10,
            'work_percentage': 100,
            'mandatory_days': '2025-01-05, 2025-01-15',  # FECHAS MANDATORY
            'unavailable_days': '',
            'incompatible_with': [],
            'monthly_targets': {}
        },
        {
            'id': '2',
            'name': 'Trabajador 2',
            'target_shifts': 10,
            'work_percentage': 100,
            'mandatory_days': '2025-01-10, 2025-01-20',  # FECHAS MANDATORY
            'unavailable_days': '',
            'incompatible_with': [],
            'monthly_targets': {}
        },
        {
            'id': '3',
            'name': 'Trabajador 3',
            'target_shifts': 10,
            'work_percentage': 100,
            'mandatory_days': '',
            'unavailable_days': '',
            'incompatible_with': [],
            'monthly_targets': {}
        }
    ]
    
    config = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'num_shifts': 2,
        'workers_data': workers_data,
        'max_shifts_per_worker': 15,
        'gap_between_shifts': 1,
        'max_consecutive_weekends': 2,
        'holidays': []
    }
    
    return config

def run_test_with_real_data():
    """Ejecuta test con datos reales"""
    
    print("=" * 80)
    print("TEST DE PROTECCIÓN DE MANDATORY SHIFTS CON DATOS REALES")
    print("=" * 80)
    
    # 1. Intentar cargar configuración desde archivo
    config = load_config_from_file('schedule_config.json')
    
    # 2. Si no existe, usar configuración de prueba
    if config is None:
        print("\n⚠️  No se encontró schedule_config.json")
        print("📝 Usando configuración de prueba por defecto")
        print("💡 TIP: Copia tu archivo schedule_config.json aquí o modifica create_test_config()")
        print()
        config = create_test_config()
    
    # 3. Mostrar resumen de configuración
    workers_data = config.get('workers_data', [])
    print(f"\n📊 CONFIGURACIÓN:")
    print(f"  - Periodo: {config['start_date']} a {config['end_date']}")
    print(f"  - Trabajadores: {len(workers_data)}")
    print(f"  - Turnos por día: {config.get('num_shifts', 2)}")
    
    # Contar mandatory shifts
    mandatory_count = 0
    for worker in workers_data:
        mandatory_str = worker.get('mandatory_days', '')
        if mandatory_str:
            # Contar comas + 1 para aproximar número de fechas
            mandatory_count += len(mandatory_str.split(','))
            print(f"  - {worker['id']} ({worker['name']}): {len(mandatory_str.split(','))} mandatory shifts")
    
    print(f"\n🔒 Total mandatory shifts esperados: {mandatory_count}")
    
    # 4. Crear scheduler y generar horario
    print("\n🚀 Generando schedule...")
    try:
        scheduler = Scheduler(
            start_date=datetime.strptime(config['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(config['end_date'], '%Y-%m-%d'),
            num_shifts=config.get('num_shifts', 2),
            workers_data=workers_data,
            max_shifts_per_worker=config.get('max_shifts_per_worker', 20),
            gap_between_shifts=config.get('gap_between_shifts', 1),
            max_consecutive_weekends=config.get('max_consecutive_weekends', 2),
            holidays=config.get('holidays', [])
        )
        
        schedule = scheduler.generate_schedule()
        
        print(f"\n✅ Schedule generado exitosamente")
        print(f"   - Días procesados: {len(schedule)}")
        print(f"   - Turnos asignados: {sum(sum(1 for w in workers if w is not None) for workers in schedule.values())}")
        
    except Exception as e:
        print(f"\n❌ ERROR al generar schedule: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Ejecutar verificación automática
    print("\n" + "=" * 80)
    print("EJECUTANDO VERIFICACIÓN DE PROTECCIÓN")
    print("=" * 80)
    
    import subprocess
    result = subprocess.run(
        ['python', '/workspaces/10/verify_mandatory_protection.py'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

if __name__ == '__main__':
    success = run_test_with_real_data()
    
    if success:
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        print("\n💡 Revisa logs/test_real_data.log para ver los detalles")
        print("🔍 Busca los emojis 🔒 para confirmar protección de mandatory")
    else:
        print("\n" + "=" * 80)
        print("⚠️ TEST COMPLETADO CON ADVERTENCIAS")
        print("=" * 80)
        print("\n📋 Siguiente paso: Revisa el log para entender el estado")
