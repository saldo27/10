#!/usr/bin/env python3
"""
Test con escenario real:
- 29 trabajadores
- 8 meses (01-11-2025 a 30-06-2026)
- 4 guardias por día
- 11 días festivos
- 5 trabajadores incompatibles entre sí
- Varios trabajadores con jornadas parciales
"""

import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_real_scenario.log')
    ]
)

def main():
    logging.info("="*80)
    logging.info("TEST ESCENARIO REAL - 4 MESES")
    logging.info("="*80)
    logging.info("")
    logging.info("Parámetros del test:")
    logging.info("  Fecha inicio: 01-11-2025")
    logging.info("  Fecha fin: 28-02-2026")
    logging.info("  Período: 4 meses (120 días)")
    logging.info("  Trabajadores: 29")
    logging.info("  Guardias/día: 4")
    logging.info("  Total guardias: 480")
    logging.info("  Días festivos: 6")
    logging.info("")
    logging.info("Distribución de trabajadores:")
    logging.info("  - 5 incompatibles (100% jornada, con restricciones)")
    logging.info("  - 2 trabajadores al 50%")
    logging.info("  - 1 trabajador al 60%")
    logging.info("  - 2 trabajadores al 66%")
    logging.info("  - 3 trabajadores al 80%")
    logging.info("  - 16 trabajadores al 100%")
    logging.info("")
    
    # Calcular capacidad teórica
    capacidad_trabajadores = {
        '50%': 2 * 24,   # 48
        '60%': 1 * 29,   # 29
        '66%': 2 * 32,   # 64
        '80%': 3 * 39,   # 117
        '100%': 21 * 49  # 1029 (16 normales + 5 incompatibles)
    }
    capacidad_total = sum(capacidad_trabajadores.values())
    
    logging.info(f"Capacidad teórica:")
    for porcentaje, capacidad in capacidad_trabajadores.items():
        logging.info(f"  {porcentaje}: {capacidad} turnos")
    logging.info(f"  TOTAL: {capacidad_total} turnos disponibles")
    logging.info(f"  Necesarios: 968 turnos")
    logging.info(f"  Ratio: {capacidad_total/968:.2f}x (cobertura teórica)")
    logging.info("")
    
    try:
        from scheduler import Scheduler
        import json
        
        logging.info("Iniciando generación de horario...")
        logging.info("-" * 80)
        
        start_time = datetime.now()
        
        # Cargar configuración desde archivo JSON
        with open('schedule_config_test_real.json', 'r') as f:
            config = json.load(f)
        
        # Convertir fechas de string a datetime
        config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d')
        config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d')
        
        # Convertir holidays a datetime
        config['holidays'] = [datetime.strptime(h, '%Y-%m-%d') for h in config['holidays']]
        
        # Crear scheduler con configuración de test
        scheduler = Scheduler(config)
        
        logging.info(f"✓ Scheduler creado correctamente")
        logging.info(f"  Trabajadores cargados: {len(scheduler.workers_data)}")
        logging.info(f"  Fecha inicio: {scheduler.start_date}")
        logging.info(f"  Fecha fin: {scheduler.end_date}")
        logging.info(f"  Días totales: {(scheduler.end_date - scheduler.start_date).days + 1}")
        logging.info("")
        
        # Generar horario con 5 intentos completos
        logging.info("Generando horario completo con 5 intentos...")
        logging.info("  - Cada intento respetará límite estricto de +10%")
        logging.info("  - Se compararán todos los intentos")
        logging.info("  - Se elegirá el mejor según cobertura y balance")
        logging.info("")
        success = scheduler.generate_schedule(max_improvement_loops=70)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logging.info("-" * 80)
        
        if success:
            logging.info("✅ HORARIO GENERADO EXITOSAMENTE")
            logging.info(f"⏱️  Tiempo de generación: {duration:.1f} segundos")
            
            # Estadísticas del horario
            total_days = len(scheduler.schedule)
            total_slots = total_days * scheduler.num_shifts
            filled_slots = sum(1 for day_shifts in scheduler.schedule.values() 
                             for worker in day_shifts if worker is not None)
            empty_slots = total_slots - filled_slots
            
            logging.info("")
            logging.info("📊 Estadísticas del horario:")
            logging.info(f"  Días programados: {total_days}")
            logging.info(f"  Total puestos: {total_slots}")
            logging.info(f"  Puestos cubiertos: {filled_slots}")
            logging.info(f"  Puestos vacíos: {empty_slots}")
            logging.info(f"  Cobertura: {filled_slots/total_slots*100:.1f}%")
            
            # Verificar balance de trabajadores
            logging.info("")
            logging.info("👥 Balance de trabajadores:")
            
            workers_with_shifts = {}
            for worker in scheduler.workers_data:
                worker_id = worker['id']
                assigned = sum(1 for day_shifts in scheduler.schedule.values()
                             for w in day_shifts if w == worker_id)
                target = worker.get('target_shifts', 0)
                workers_with_shifts[worker_id] = {
                    'assigned': assigned,
                    'target': target,
                    'percentage': worker.get('work_percentage', 100)
                }
            
            # Mostrar resumen por categoría
            categories = {
                'Parcial 50%': [w for w, d in workers_with_shifts.items() if d['percentage'] == 50],
                'Parcial 60%': [w for w, d in workers_with_shifts.items() if d['percentage'] == 60],
                'Parcial 66%': [w for w, d in workers_with_shifts.items() if d['percentage'] == 66],
                'Parcial 80%': [w for w, d in workers_with_shifts.items() if d['percentage'] == 80],
                'Completo 100%': [w for w, d in workers_with_shifts.items() if d['percentage'] == 100]
            }
            
            for category, workers in categories.items():
                if workers:
                    logging.info(f"  {category}:")
                    for worker_id in workers:
                        data = workers_with_shifts[worker_id]
                        deviation = data['assigned'] - data['target']
                        deviation_pct = (deviation / data['target'] * 100) if data['target'] > 0 else 0
                        status = "✓" if abs(deviation_pct) <= 8 else "⚠️" if abs(deviation_pct) <= 10 else "❌"
                        logging.info(f"    {status} Worker {worker_id}: {data['assigned']}/{data['target']} turnos ({deviation_pct:+.1f}%)")
            
            # Verificar violaciones de tolerancia
            logging.info("")
            logging.info("🎯 Verificación de tolerancia (±8% objetivo, ±10% límite):")
            
            violations = []
            for worker_id, data in workers_with_shifts.items():
                if data['target'] > 0:
                    deviation_pct = abs((data['assigned'] - data['target']) / data['target'] * 100)
                    if deviation_pct > 8:
                        violations.append({
                            'worker': worker_id,
                            'deviation': deviation_pct,
                            'assigned': data['assigned'],
                            'target': data['target']
                        })
            
            if violations:
                logging.warning(f"  ⚠️  {len(violations)} trabajadores fuera de tolerancia objetivo:")
                for v in sorted(violations, key=lambda x: x['deviation'], reverse=True):
                    level = "🚨" if v['deviation'] > 15 else "⚠️" if v['deviation'] > 10 else "📊"
                    logging.warning(f"    {level} Worker {v['worker']}: {v['assigned']}/{v['target']} ({v['deviation']:.1f}%)")
            else:
                logging.info(f"  ✅ Todos los trabajadores dentro de tolerancia")
            
            logging.info("")
            logging.info("="*80)
            logging.info("TEST COMPLETADO")
            logging.info("="*80)
            
            return True
            
        else:
            logging.error("❌ ERROR: No se pudo generar el horario")
            logging.error(f"⏱️  Tiempo hasta fallo: {duration:.1f} segundos")
            return False
            
    except Exception as e:
        logging.error(f"❌ ERROR CRÍTICO: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
