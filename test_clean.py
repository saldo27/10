#!/usr/bin/env python3
"""
Test limpio con logging reducido para análisis de resultados.
"""

import logging
import sys
import json
from datetime import datetime

# Configure logging to WARNING level to reduce output
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_clean.log')
    ]
)

# Create a separate INFO logger for our test output
test_logger = logging.getLogger('test')
test_logger.setLevel(logging.INFO)
test_handler = logging.StreamHandler(sys.stdout)
test_handler.setFormatter(logging.Formatter('%(message)s'))
test_logger.addHandler(test_handler)

def main():
    test_logger.info("="*80)
    test_logger.info("TEST LIMPIO - VERIFICACIÓN DE FIXES")
    test_logger.info("="*80)
    test_logger.info("")
    test_logger.info("Configuración:")
    test_logger.info("  • 29 trabajadores (5 incompatibles, 2@50%, 1@60%, 2@66%, 3@80%, 21@100%)")
    test_logger.info("  • Período: 120 días (01-11-2025 a 28-02-2026)")
    test_logger.info("  • 4 turnos/día = 480 posiciones totales")
    test_logger.info("  • Tolerancia: Fase 1 ±8%, Fase 2 ±12% (ABSOLUTO)")
    test_logger.info("")
    
    try:
        from scheduler import Scheduler
        
        start_time = datetime.now()
        
        # Load configuration
        with open('schedule_config_test_real.json', 'r') as f:
            config = json.load(f)
        
        # Convert dates
        config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d')
        config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d')
        config['holidays'] = [datetime.strptime(h, '%Y-%m-%d') for h in config['holidays']]
        
        test_logger.info("🚀 Creando scheduler...")
        scheduler = Scheduler(config)
        
        test_logger.info(f"✅ Scheduler creado: {len(scheduler.workers_data)} trabajadores")
        test_logger.info("")
        
        # Verify Worker 10 target
        worker_10 = next((w for w in scheduler.workers_data if w['id'] == '10'), None)
        if worker_10:
            test_logger.info("🔍 Verificación pre-test:")
            test_logger.info(f"   Worker 10 (50% part-time): target_shifts = {worker_10.get('target_shifts', 0)}")
            if worker_10.get('target_shifts') == 9:
                test_logger.info("   ✅ Target CORRECTO (9, no dividido por work_percentage)")
            else:
                test_logger.info(f"   ❌ Target INCORRECTO (debería ser 9, no {worker_10.get('target_shifts')})")
        test_logger.info("")
        
        # Generate schedule
        test_logger.info("🔄 Generando horario (esto puede tomar varios minutos)...")
        test_logger.info("   Ejecutando 5 intentos completos con optimización...")
        test_logger.info("")
        
        success = scheduler.generate_schedule(max_improvement_loops=70)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        test_logger.info("")
        test_logger.info("="*80)
        
        if success:
            test_logger.info("✅ HORARIO GENERADO EXITOSAMENTE")
            test_logger.info(f"⏱️  Tiempo total: {duration:.1f} segundos ({duration/60:.1f} minutos)")
            test_logger.info("")
            
            # Calculate statistics
            total_days = len(scheduler.schedule)
            total_slots = total_days * scheduler.num_shifts
            filled_slots = sum(1 for day_shifts in scheduler.schedule.values() 
                             for worker in day_shifts if worker is not None)
            empty_slots = total_slots - filled_slots
            coverage = (filled_slots / total_slots * 100) if total_slots > 0 else 0
            
            test_logger.info("📊 ESTADÍSTICAS GENERALES:")
            test_logger.info(f"   Días programados: {total_days}")
            test_logger.info(f"   Puestos totales: {total_slots}")
            test_logger.info(f"   Puestos cubiertos: {filled_slots}")
            test_logger.info(f"   Puestos vacíos: {empty_slots}")
            test_logger.info(f"   Cobertura: {coverage:.1f}%")
            test_logger.info("")
            
            # Analyze worker distribution
            test_logger.info("👥 ANÁLISIS DE DISTRIBUCIÓN POR TRABAJADOR:")
            test_logger.info("="*80)
            
            workers_analysis = []
            for worker in scheduler.workers_data:
                worker_id = worker['id']
                assigned = sum(1 for day_shifts in scheduler.schedule.values()
                             for w in day_shifts if w == worker_id)
                target = worker.get('target_shifts', 0)
                work_pct = worker.get('work_percentage', 100)
                
                if target > 0:
                    deviation = ((assigned - target) / target * 100)
                    workers_analysis.append({
                        'id': worker_id,
                        'assigned': assigned,
                        'target': target,
                        'work_pct': work_pct,
                        'deviation': deviation
                    })
            
            # Sort by absolute deviation (worst first)
            workers_analysis.sort(key=lambda x: abs(x['deviation']), reverse=True)
            
            # Categorize workers
            violations_12 = [w for w in workers_analysis if abs(w['deviation']) > 12]
            violations_8 = [w for w in workers_analysis if 8 < abs(w['deviation']) <= 12]
            ok_workers = [w for w in workers_analysis if abs(w['deviation']) <= 8]
            
            # Show violations > 12%
            if violations_12:
                test_logger.info(f"\n❌ VIOLACIONES >12% ({len(violations_12)} trabajadores):")
                test_logger.info("-" * 80)
                for w in violations_12[:15]:  # Show top 15
                    status = "🔴" if abs(w['deviation']) > 15 else "⚠️"
                    test_logger.info(f"   {status} Worker {w['id']:>2} ({w['work_pct']:>3}%): "
                                   f"{w['assigned']:>2}/{w['target']:>2} turnos "
                                   f"({w['deviation']:+6.1f}%)")
            
            # Show violations 8-12%
            if violations_8:
                test_logger.info(f"\n⚠️  VIOLACIONES 8-12% ({len(violations_8)} trabajadores):")
                test_logger.info("-" * 80)
                for w in violations_8[:15]:
                    test_logger.info(f"   ⚠️  Worker {w['id']:>2} ({w['work_pct']:>3}%): "
                                   f"{w['assigned']:>2}/{w['target']:>2} turnos "
                                   f"({w['deviation']:+6.1f}%)")
            
            # Summary
            test_logger.info(f"\n✅ DENTRO DE TOLERANCIA ±8% ({len(ok_workers)} trabajadores)")
            
            # Overall summary
            test_logger.info("")
            test_logger.info("="*80)
            test_logger.info("📊 RESUMEN FINAL:")
            test_logger.info("="*80)
            test_logger.info(f"   Total trabajadores: {len(workers_analysis)}")
            test_logger.info(f"   ✅ Dentro de ±8%: {len(ok_workers)} ({len(ok_workers)/len(workers_analysis)*100:.1f}%)")
            test_logger.info(f"   ⚠️  Entre ±8-12%: {len(violations_8)} ({len(violations_8)/len(workers_analysis)*100:.1f}%)")
            test_logger.info(f"   ❌ Fuera de ±12%: {len(violations_12)} ({len(violations_12)/len(workers_analysis)*100:.1f}%)")
            test_logger.info(f"   📈 Cobertura: {coverage:.1f}%")
            test_logger.info("")
            
            # Check Worker 10 specifically
            worker_10_analysis = next((w for w in workers_analysis if w['id'] == '10'), None)
            if worker_10_analysis:
                test_logger.info("🔍 VERIFICACIÓN ESPECÍFICA - WORKER 10:")
                test_logger.info("-" * 80)
                test_logger.info(f"   Jornada: {worker_10_analysis['work_pct']}% part-time")
                test_logger.info(f"   Target configurado: {worker_10_analysis['target']} turnos")
                test_logger.info(f"   Turnos asignados: {worker_10_analysis['assigned']}")
                test_logger.info(f"   Desviación: {worker_10_analysis['deviation']:+.1f}%")
                
                if abs(worker_10_analysis['deviation']) <= 12:
                    test_logger.info(f"   ✅ DENTRO DEL LÍMITE ±12%")
                else:
                    test_logger.info(f"   ❌ FUERA DEL LÍMITE ±12%")
            
            # Final verdict
            test_logger.info("")
            test_logger.info("="*80)
            if len(violations_12) == 0 and coverage >= 95:
                test_logger.info("🎉 TEST EXITOSO: Sin violaciones >12% y cobertura ≥95%")
            elif len(violations_12) == 0:
                test_logger.info("⚠️  TEST PARCIAL: Sin violaciones >12% pero cobertura <95%")
            else:
                test_logger.info("❌ TEST FALLIDO: Existen violaciones >12% del límite absoluto")
            test_logger.info("="*80)
            
            return True
            
        else:
            test_logger.info("❌ ERROR: No se pudo generar el horario")
            test_logger.info(f"⏱️  Tiempo hasta fallo: {duration:.1f} segundos")
            return False
            
    except Exception as e:
        test_logger.error(f"❌ ERROR CRÍTICO: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
