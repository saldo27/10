#!/usr/bin/env python3
"""
Script para rastrear cambios en turnos mandatory durante la generación del schedule
"""

import json
import logging
from datetime import datetime
from scheduler import Scheduler
from utilities import DateTimeUtils

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mandatory_trace.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_config(filename='schedule_config.json'):
    """Carga configuración desde JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def extract_mandatory_shifts(config):
    """Extrae todos los mandatory shifts de la configuración"""
    date_utils = DateTimeUtils()
    mandatory_shifts = {}  # {(worker_id, date): True}
    
    for worker in config.get('workers_data', []):
        worker_id = worker['id']
        mandatory_str = worker.get('mandatory_days', '')
        if mandatory_str:
            # Separar por ; y , luego parsear cada fecha individualmente
            dates_str = mandatory_str.replace(';', ',')
            date_strings = [d.strip() for d in dates_str.split(',') if d.strip()]
            
            for date_str in date_strings:
                try:
                    # Intentar formato DD-MM-YYYY primero
                    try:
                        date = datetime.strptime(date_str, '%d-%m-%Y')
                    except ValueError:
                        # Intentar formato YYYY-MM-DD
                        date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    mandatory_shifts[(worker_id, date)] = {
                        'worker_id': worker_id,
                        'worker_name': worker.get('name', 'Unknown'),
                        'date': date,
                        'original': True
                    }
                except ValueError as e:
                    logging.warning(f"Could not parse mandatory date '{date_str}' for worker {worker_id}: {e}")
    
    return mandatory_shifts

def trace_mandatory_changes():
    """Rastrea cambios en mandatory shifts durante generación"""
    print("=" * 80)
    print("RASTREADOR DE CAMBIOS EN MANDATORY SHIFTS")
    print("=" * 80)
    
    # Cargar configuración
    config = load_config()
    if not config:
        print("❌ No se pudo cargar configuración")
        return
    
    # Extraer mandatory shifts esperados
    print("\n📋 EXTRAYENDO MANDATORY SHIFTS DE CONFIGURACIÓN...")
    expected_mandatory = extract_mandatory_shifts(config)
    print(f"   Total mandatory esperados: {len(expected_mandatory)}")
    
    for (worker_id, date), info in sorted(expected_mandatory.items(), key=lambda x: (x[1]['date'], x[0])):
        print(f"   - {worker_id} ({info['worker_name']}): {date.strftime('%d-%m-%Y')}")
    
    # Convertir fechas
    start_date_str = config['start_date']
    end_date_str = config['end_date']
    
    try:
        start_date = datetime.strptime(start_date_str, '%d-%m-%Y')
        end_date = datetime.strptime(end_date_str, '%d-%m-%Y')
        date_format = '%d-%m-%Y'
    except ValueError:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        date_format = '%Y-%m-%d'
    
    holidays = []
    for h in config.get('holidays', []):
        if isinstance(h, str):
            try:
                holidays.append(datetime.strptime(h, date_format))
            except ValueError:
                other_format = '%Y-%m-%d' if date_format == '%d-%m-%Y' else '%d-%m-%Y'
                holidays.append(datetime.strptime(h, other_format))
        else:
            holidays.append(h)
    
    scheduler_config = config.copy()
    scheduler_config['start_date'] = start_date
    scheduler_config['end_date'] = end_date
    scheduler_config['holidays'] = holidays
    
    # Crear scheduler
    print("\n🚀 CREANDO SCHEDULER...")
    scheduler = Scheduler(scheduler_config)
    
    # El schedule_builder no existe hasta que se llama generate_schedule
    # porque se crea dentro de scheduler_core
    print("   (schedule_builder se creará durante generate_schedule)")
    
    # Generar schedule
    print("\n⏳ GENERANDO SCHEDULE (esto puede tardar)...")
    result = scheduler.generate_schedule()
    
    if not result:
        print("❌ No se generó schedule")
        return
    
    schedule = scheduler.schedule
    
    print(f"\n✅ SCHEDULE GENERADO")
    print(f"   Días generados: {len(schedule)}")
    
    # Ahora acceder al schedule_builder
    # El scheduler_core crea su propio scheduler interno con schedule_builder
    # Necesitamos acceder a través de la estructura correcta
    schedule_builder = None
    locked_set = set()
    
    # Intentar diferentes rutas de acceso
    if hasattr(scheduler, 'schedule_builder'):
        schedule_builder = scheduler.schedule_builder
        print("   ✓ Accedido via scheduler.schedule_builder")
    
    if schedule_builder and hasattr(schedule_builder, '_locked_mandatory'):
        locked_set = schedule_builder._locked_mandatory
        print(f"\n🔒 _locked_mandatory final: {len(locked_set)}")
    else:
        # Acceso alternativo: buscar en todas las asignaciones si tienen marcador de mandatory
        print("\n⚠️  No se pudo acceder a _locked_mandatory directamente")
        print("   Analizando asignaciones del schedule para inferir mandatory...")
        
        # Inferir locked_set desde las asignaciones que coinciden con expected_mandatory
        for (worker_id, date), info in expected_mandatory.items():
            if date in schedule and worker_id in schedule[date]:
                locked_set.add((worker_id, date))
    
    # Verificar cada mandatory shift
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE MANDATORY SHIFTS")
    print("=" * 80)
    
    protected_count = 0
    modified_count = 0
    missing_count = 0
    problem_shifts = []  # Lista de shifts con problemas
    
    for (worker_id, expected_date), info in sorted(expected_mandatory.items(), key=lambda x: (x[1]['date'], x[0])):
        worker_name = info['worker_name']
        date_str = expected_date.strftime('%d-%m-%Y')
        
        # Verificar si está en _locked_mandatory
        is_locked = (worker_id, expected_date) in locked_set
        
        # Verificar si está asignado en el schedule final
        is_assigned = expected_date in schedule and worker_id in schedule[expected_date]
        
        # Determinar estado
        if is_locked and is_assigned:
            status = "✅ PROTEGIDO"
            protected_count += 1
        elif is_locked and not is_assigned:
            status = "⚠️  LOCKED pero NO ASIGNADO"
            missing_count += 1
            problem_shifts.append({
                'worker_id': worker_id,
                'worker_name': worker_name,
                'date': expected_date,
                'date_str': date_str,
                'problem': 'LOCKED pero no asignado'
            })
        elif not is_locked and is_assigned:
            status = "⚠️  ASIGNADO pero NO LOCKED"
            modified_count += 1
            problem_shifts.append({
                'worker_id': worker_id,
                'worker_name': worker_name,
                'date': expected_date,
                'date_str': date_str,
                'problem': 'Asignado pero NO protegido'
            })
        else:
            status = "❌ NO LOCKED y NO ASIGNADO"
            missing_count += 1
            problem_shifts.append({
                'worker_id': worker_id,
                'worker_name': worker_name,
                'date': expected_date,
                'date_str': date_str,
                'problem': 'NO LOCKED y NO asignado'
            })
        
        print(f"{status}: {worker_id:3} ({worker_name:12}) - {date_str}")
        logging.info(f"{status}: {worker_id:3} ({worker_name:12}) - {date_str}")
        
        # Si está asignado, mostrar en qué turno
        if is_assigned:
            post_index = schedule[expected_date].index(worker_id)
            print(f"         → Asignado en Post {post_index}")
            logging.info(f"         → Asignado en Post {post_index}")
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Total mandatory esperados:  {len(expected_mandatory)}")
    print(f"✅ Protegidos correctamente: {protected_count}")
    print(f"⚠️  Modificados/Sin lock:     {modified_count}")
    print(f"❌ Faltantes:                {missing_count}")
    
    logging.info("\n" + "=" * 80)
    logging.info("RESUMEN")
    logging.info("=" * 80)
    logging.info(f"Total mandatory esperados:  {len(expected_mandatory)}")
    logging.info(f"✅ Protegidos correctamente: {protected_count}")
    logging.info(f"⚠️  Modificados/Sin lock:     {modified_count}")
    logging.info(f"❌ Faltantes:                {missing_count}")
    
    if protected_count == len(expected_mandatory):
        print("\n🎉 ¡TODOS LOS MANDATORY SHIFTS ESTÁN PROTEGIDOS!")
        logging.info("\n🎉 ¡TODOS LOS MANDATORY SHIFTS ESTÁN PROTEGIDOS!")
    else:
        print(f"\n⚠️  HAY {len(expected_mandatory) - protected_count} MANDATORY SHIFTS CON PROBLEMAS")
        logging.warning(f"\n⚠️  HAY {len(expected_mandatory) - protected_count} MANDATORY SHIFTS CON PROBLEMAS")
        
        # Mostrar detalles de los problemas
        if problem_shifts:
            print("\n" + "=" * 80)
            print("DETALLES DE MANDATORY SHIFTS CON PROBLEMAS:")
            print("=" * 80)
            logging.info("\n" + "=" * 80)
            logging.info("DETALLES DE MANDATORY SHIFTS CON PROBLEMAS:")
            logging.info("=" * 80)
            
            for shift in problem_shifts:
                msg = f"❌ {shift['worker_id']} ({shift['worker_name']}): {shift['date_str']} - {shift['problem']}"
                print(msg)
                logging.error(msg)
                
                # Mostrar quién está asignado en ese día/turno si no es el worker esperado
                if shift['date'] in schedule:
                    assigned_workers = schedule[shift['date']]
                    print(f"   Asignados ese día: {assigned_workers}")
                    logging.info(f"   Asignados ese día: {assigned_workers}")
    
    print("\n💾 Log detallado guardado en: mandatory_trace.log")
    logging.info("\n💾 Fin del análisis")

if __name__ == "__main__":
    trace_mandatory_changes()
