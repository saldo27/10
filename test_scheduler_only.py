#!/usr/bin/env python3
"""
Script para probar SOLO el scheduler con datos reales.
NO ejecuta la interfaz Kivy, solo la lógica de scheduling.

Uso:
    python test_scheduler_only.py [archivo_config.json]

Ejemplo:
    python test_scheduler_only.py schedule_config.json
"""

import sys
import json
import logging
from datetime import datetime
from scheduler import Scheduler

# Configurar logging con emoji support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_scheduler_only.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_config(config_file):
    """Carga configuración desde archivo JSON"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {config_file}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error: Archivo JSON inválido: {e}")
        return None

def run_scheduler_test(config_file='schedule_config.json'):
    """Ejecuta el scheduler con configuración real"""
    
    print("=" * 80)
    print("TEST DEL SCHEDULER (Solo lógica, sin UI)")
    print("=" * 80)
    
    # Cargar configuración
    config = load_config(config_file)
    if not config:
        print("\n💡 Crea un archivo de configuración primero:")
        print("   python export_current_config.py")
        return False
    
    # Extraer parámetros
    workers_data = config.get('workers_data', [])
    
    if not workers_data:
        print("❌ Error: No hay trabajadores en la configuración")
        return False
    
    # Mostrar resumen
    print(f"\n📊 CONFIGURACIÓN CARGADA:")
    print(f"   - Archivo: {config_file}")
    print(f"   - Periodo: {config['start_date']} a {config['end_date']}")
    print(f"   - Trabajadores: {len(workers_data)}")
    print(f"   - Turnos/día: {config.get('num_shifts', 2)}")
    
    # Contar mandatory shifts
    mandatory_total = 0
    print(f"\n👥 TRABAJADORES CON MANDATORY SHIFTS:")
    for worker in workers_data:
        mandatory_str = worker.get('mandatory_days', '')
        if mandatory_str:
            # Separar por comas Y punto y coma
            dates = mandatory_str.replace(';', ',').split(',')
            count = len([d.strip() for d in dates if d.strip()])
            if count > 0:
                mandatory_total += count
                print(f"   [{worker['id']}] {worker.get('name', 'Sin nombre')}: {count} mandatory")
    
    print(f"\n🔒 Total mandatory shifts: {mandatory_total}")
    
    # Crear scheduler
    print(f"\n🚀 INICIANDO SCHEDULER...")
    print(f"   Este proceso puede tardar varios minutos...")
    
    try:
        # Convertir fechas a datetime para el scheduler
        scheduler_config = config.copy()
        
        # Detectar formato de fecha (intentar ambos formatos)
        start_date_str = config['start_date']
        end_date_str = config['end_date']
        
        try:
            # Intentar formato DD-MM-YYYY primero
            scheduler_config['start_date'] = datetime.strptime(start_date_str, '%d-%m-%Y')
            scheduler_config['end_date'] = datetime.strptime(end_date_str, '%d-%m-%Y')
            date_format = '%d-%m-%Y'
        except ValueError:
            # Si falla, usar formato YYYY-MM-DD
            scheduler_config['start_date'] = datetime.strptime(start_date_str, '%Y-%m-%d')
            scheduler_config['end_date'] = datetime.strptime(end_date_str, '%Y-%m-%d')
            date_format = '%Y-%m-%d'
        
        # Convertir holidays usando el formato detectado
        holidays = []
        for h in config.get('holidays', []):
            if isinstance(h, str):
                try:
                    holidays.append(datetime.strptime(h, date_format))
                except ValueError:
                    # Intentar el otro formato si falla
                    other_format = '%Y-%m-%d' if date_format == '%d-%m-%Y' else '%d-%m-%Y'
                    holidays.append(datetime.strptime(h, other_format))
            else:
                holidays.append(h)
        scheduler_config['holidays'] = holidays
        
        # Crear scheduler con el diccionario de configuración
        scheduler = Scheduler(scheduler_config)
        
        # Generar schedule
        print(f"\n⏳ Generando schedule...")
        success = scheduler.generate_schedule()
        
        if not success:
            print(f"\n❌ La generación del schedule no fue exitosa")
            return False
        
        # Obtener el schedule generado
        schedule = scheduler.schedule
        
        # Mostrar resultados
        print(f"\n✅ SCHEDULE GENERADO EXITOSAMENTE")
        print(f"=" * 80)
        print(f"📋 RESUMEN:")
        print(f"   - Días procesados: {len(schedule)}")
        
        total_shifts = sum(sum(1 for w in workers if w is not None) 
                          for workers in schedule.values())
        print(f"   - Turnos asignados: {total_shifts}")
        
        empty_shifts = sum(sum(1 for w in workers if w is None) 
                          for workers in schedule.values())
        print(f"   - Turnos vacíos: {empty_shifts}")
        
        # Resumen por trabajador
        print(f"\n👥 ASIGNACIONES POR TRABAJADOR:")
        for worker in workers_data:
            worker_id = worker['id']
            assigned = len(scheduler.worker_assignments.get(worker_id, set()))
            target = worker.get('target_shifts', 0)
            mandatory_str = worker.get('mandatory_days', '')
            mandatory_count = len([d.strip() for d in mandatory_str.split(',') if d.strip()]) if mandatory_str else 0
            
            status = "✅" if assigned >= target * 0.9 else "⚠️"
            print(f"   {status} [{worker_id}] {worker.get('name', 'N/A')}: {assigned}/{target} turnos", end="")
            if mandatory_count > 0:
                print(f" (🔒 {mandatory_count} mandatory)", end="")
            print()
        
        # Exportar calendario completo a JSON
        print(f"\n💾 Exportando calendario a JSON...")
        json_file = scheduler.export_schedule_json()
        print(f"   ✅ Calendario guardado en: {json_file}")
        
        print(f"\n📝 Log guardado en: logs/test_scheduler_only.log")
        print(f"   Busca los emojis 🔒 para ver protecciones de mandatory")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR al generar schedule:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # Permitir pasar archivo de configuración como argumento
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'schedule_config.json'
    
    success = run_scheduler_test(config_file)
    
    if success:
        print(f"\n" + "=" * 80)
        print(f"✅ TEST COMPLETADO")
        print(f"=" * 80)
        print(f"\n🔍 Siguiente paso - Verificar protección:")
        print(f"   python verify_mandatory_protection.py")
    else:
        print(f"\n" + "=" * 80)
        print(f"❌ TEST FALLÓ")
        print(f"=" * 80)
    
    sys.exit(0 if success else 1)
