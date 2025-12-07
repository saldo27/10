#!/usr/bin/env python3
"""
Script para exportar la configuración actual de trabajadores.

Este script te ayuda a:
1. Crear un backup de tu configuración actual
2. Generar un archivo JSON con todos los datos de trabajadores
3. Usar ese archivo para pruebas sin perder datos

Uso:
    python export_current_config.py
    
Genera: schedule_config_backup.json
"""

import json
import os
from datetime import datetime

def export_config_from_main():
    """
    Intenta exportar la configuración desde main.py
    
    Si tienes datos guardados en la app, este script los exporta a JSON
    """
    
    # Buscar archivos de configuración existentes
    config_files = [
        'schedule_config.json',
        'workers_config.json',
        'config.json'
    ]
    
    found_config = None
    found_file = None
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    found_config = json.load(f)
                found_file = config_file
                print(f"✅ Encontrado: {config_file}")
                break
            except Exception as e:
                print(f"⚠️ Error leyendo {config_file}: {e}")
    
    if found_config:
        # Crear backup con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'schedule_config_backup_{timestamp}.json'
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(found_config, f, indent=2, ensure_ascii=False)
        
        print(f"\n📦 Backup creado: {backup_file}")
        print(f"   Fuente: {found_file}")
        
        # Mostrar resumen
        workers_data = found_config.get('workers_data', [])
        print(f"\n📊 RESUMEN DE CONFIGURACIÓN:")
        print(f"   - Total trabajadores: {len(workers_data)}")
        
        if workers_data:
            print(f"\n👥 TRABAJADORES:")
            for worker in workers_data:
                worker_id = worker.get('id', 'N/A')
                name = worker.get('name', 'Sin nombre')
                target = worker.get('target_shifts', 0)
                mandatory = worker.get('mandatory_days', '')
                mandatory_count = len(mandatory.split(',')) if mandatory else 0
                
                print(f"   [{worker_id}] {name}")
                print(f"       Target: {target} turnos")
                if mandatory_count > 0:
                    print(f"       🔒 Mandatory: {mandatory_count} fechas")
        
        return backup_file
    else:
        print("❌ No se encontró ningún archivo de configuración")
        print("\n💡 Archivos buscados:")
        for cf in config_files:
            print(f"   - {cf}")
        print("\n📝 Crea manualmente un archivo con este formato:")
        print("""
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "num_shifts": 2,
  "workers_data": [
    {
      "id": "1",
      "name": "Trabajador 1",
      "target_shifts": 10,
      "work_percentage": 100,
      "mandatory_days": "2025-01-05, 2025-01-15",
      "unavailable_days": "",
      "incompatible_with": [],
      "monthly_targets": {}
    }
  ],
  "max_shifts_per_worker": 20,
  "gap_between_shifts": 1,
  "max_consecutive_weekends": 2,
  "holidays": []
}
        """)
        return None

def create_sample_config():
    """Crea un archivo de configuración de ejemplo"""
    
    sample_config = {
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "num_shifts": 2,
        "workers_data": [
            {
                "id": "1",
                "name": "Trabajador 1",
                "target_shifts": 10,
                "work_percentage": 100,
                "mandatory_days": "2025-01-05, 2025-01-15, 2025-01-25",
                "unavailable_days": "",
                "incompatible_with": ["2"],
                "monthly_targets": {}
            },
            {
                "id": "2",
                "name": "Trabajador 2",
                "target_shifts": 10,
                "work_percentage": 100,
                "mandatory_days": "2025-01-10, 2025-01-20",
                "unavailable_days": "2025-01-01, 2025-01-02",
                "incompatible_with": ["1"],
                "monthly_targets": {}
            },
            {
                "id": "3",
                "name": "Trabajador 3",
                "target_shifts": 8,
                "work_percentage": 80,
                "mandatory_days": "",
                "unavailable_days": "",
                "incompatible_with": [],
                "monthly_targets": {}
            }
        ],
        "max_shifts_per_worker": 20,
        "gap_between_shifts": 1,
        "max_consecutive_weekends": 2,
        "holidays": []
    }
    
    sample_file = 'schedule_config_sample.json'
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    print(f"\n📝 Archivo de ejemplo creado: {sample_file}")
    print("   Personaliza este archivo con tus datos reales")
    
    return sample_file

if __name__ == '__main__':
    print("=" * 80)
    print("EXPORTADOR DE CONFIGURACIÓN")
    print("=" * 80)
    print()
    
    backup_file = export_config_from_main()
    
    if not backup_file:
        print("\n" + "=" * 80)
        print("CREANDO ARCHIVO DE EJEMPLO")
        print("=" * 80)
        sample_file = create_sample_config()
        print(f"\n💡 Edita {sample_file} y renómbralo a schedule_config.json")
    else:
        print(f"\n✅ Usa {backup_file} para tus pruebas")
        print("   O cópialo como schedule_config.json")
    
    print("\n🚀 Siguiente paso:")
    print("   python test_real_data.py")
