#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de Límites de Tolerancia ±12%
Este test verifica que NINGÚN trabajador supere el límite absoluto de ±12%
"""

import sys
import json
import logging
from datetime import datetime
from scheduler import Scheduler
from scheduler_core import SchedulerCore

# Configurar logging - Solo WARNING para evitar DEBUG masivo
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Logger específico para este test en INFO
test_logger = logging.getLogger('tolerance_test')
test_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(message)s'))
test_logger.addHandler(handler)

def main():
    print("="*80)
    print("TEST: VERIFICACIÓN DE LÍMITES DE TOLERANCIA ±12%")
    print("="*80)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Cargar configuración
    config_path = 'schedule_config_test_real.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Convertir fechas de string a datetime
    config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d')
    config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d')
    
    # Convertir holidays si existen
    if 'holidays' in config and config['holidays']:
        config['holidays'] = [datetime.strptime(h, '%Y-%m-%d') if isinstance(h, str) else h 
                              for h in config['holidays']]
    
    # Crear scheduler con configuración real
    scheduler = Scheduler(config)
    
    print(f"Configuración cargada: {config_path}")
    print(f"  - Trabajadores: {len(scheduler.workers_data)}")
    print(f"  - Periodo: {scheduler.start_date.strftime('%Y-%m-%d')} a {scheduler.end_date.strftime('%Y-%m-%d')}")
    print(f"  - Días: {(scheduler.end_date - scheduler.start_date).days + 1}")
    print(f"  - Turnos/día: {scheduler.num_shifts}")
    print()
    
    # Crear core con 1 intento completo
    scheduler_core = SchedulerCore(scheduler)
    
    print("Iniciando generación con:")
    print("  - max_complete_attempts = 1")
    print("  - max_improvement_loops = 70")
    print("  - Tolerancia Fase 1: ±10% (objetivo)")
    print("  - Tolerancia Fase 2: ±12% (LÍMITE ABSOLUTO)")
    print()
    
    # Ejecutar generación
    start_time = datetime.now()
    success = scheduler_core.orchestrate_schedule_generation(
        max_improvement_loops=50,  # Reducido de 70 a 50 para acelerar
        max_complete_attempts=1
    )
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print()
    print("="*80)
    print("RESULTADOS DEL TEST")
    print("="*80)
    print(f"Duración: {duration:.1f} segundos ({duration/60:.1f} minutos)")
    print(f"Estado: {'✅ ÉXITO' if success else '❌ FALLO'}")
    print()
    
    # Analizar resultados
    if scheduler.schedule:
        # Contar cobertura
        total_shifts = 0
        filled_shifts = 0
        for date, posts in scheduler.schedule.items():
            for post_val in posts:
                total_shifts += 1
                if post_val is not None:
                    filled_shifts += 1
        
        coverage_pct = (filled_shifts / total_shifts * 100) if total_shifts > 0 else 0
        print(f"Cobertura: {filled_shifts}/{total_shifts} ({coverage_pct:.1f}%)")
        print()
        
        # Analizar desviaciones por trabajador
        print("ANÁLISIS DE DESVIACIONES:")
        print("-" * 80)
        
        violations = []
        within_objective = []
        within_limit = []
        
        # Crear diccionario de workers por ID
        workers_dict = {w['id']: w for w in scheduler.workers_data}
        
        for worker_id, worker_data in sorted(workers_dict.items()):
            # Contar turnos asignados
            shifts_assigned = sum(
                1 for date, posts in scheduler.schedule.items()
                for post_val in posts
                if post_val == worker_id
            )
            
            # Obtener objetivo
            target = scheduler.builder._calculate_target_shifts(worker_id)
            work_pct = worker_data.get('work_percentage', 100)
            
            # Calcular desviación
            if target > 0:
                deviation_pct = ((shifts_assigned - target) / target) * 100
            else:
                deviation_pct = 0
            
            # Calcular tolerancias ajustadas
            tolerance_phase1 = 0.10  # ±10% objetivo
            tolerance_phase2 = 0.12  # ±12% límite
            
            if work_pct < 100:
                adjusted_tol_p1 = max(0.05, tolerance_phase1 * (work_pct / 100.0))
                adjusted_tol_p2 = max(0.05, tolerance_phase2 * (work_pct / 100.0))
            else:
                adjusted_tol_p1 = tolerance_phase1
                adjusted_tol_p2 = tolerance_phase2
            
            # Calcular rangos
            min_phase1 = round(target * (1 - adjusted_tol_p1))
            max_phase1 = round(target * (1 + adjusted_tol_p1))
            min_phase2 = round(target * (1 - adjusted_tol_p2))
            max_phase2 = round(target * (1 + adjusted_tol_p2))
            
            # Clasificar
            status = ""
            if shifts_assigned < min_phase2 or shifts_assigned > max_phase2:
                status = "❌ VIOLACIÓN"
                violations.append((worker_id, work_pct, target, shifts_assigned, deviation_pct, max_phase2))
            elif shifts_assigned < min_phase1 or shifts_assigned > max_phase1:
                status = "⚠️  FUERA OBJ"
                within_limit.append((worker_id, work_pct, target, shifts_assigned, deviation_pct))
            else:
                status = "✅ DENTRO"
                within_objective.append((worker_id, work_pct, target, shifts_assigned, deviation_pct))
            
            print(f"W{worker_id:2d} ({work_pct:3d}%): {shifts_assigned:2d}/{target:2d} "
                  f"({deviation_pct:+6.1f}%) "
                  f"[Obj:{min_phase1}-{max_phase1}, Lím:{min_phase2}-{max_phase2}] "
                  f"{status}")
        
        print()
        print("="*80)
        print("RESUMEN:")
        print(f"  ✅ Dentro objetivo (±10%): {len(within_objective)}")
        print(f"  ⚠️  Fuera objetivo, dentro límite: {len(within_limit)}")
        print(f"  ❌ VIOLACIONES (>±12%): {len(violations)}")
        print("="*80)
        
        if violations:
            print()
            print("⚠️  TRABAJADORES QUE EXCEDEN ±12% (VIOLACIONES):")
            for worker_id, work_pct, target, assigned, deviation, max_allowed in violations:
                excess = assigned - max_allowed
                print(f"  • Worker {worker_id} ({work_pct}%): {assigned}/{target} "
                      f"({deviation:+.1f}%) - Máximo permitido: {max_allowed}, "
                      f"Exceso: +{excess}")
            print()
            print("❌ TEST FALLIDO: Hay trabajadores fuera del límite ±12%")
            return False
        else:
            print()
            print("✅ TEST EXITOSO: Todos los trabajadores dentro del límite ±12%")
            return True
    else:
        print("❌ No se generó ningún horario")
        return False

if __name__ == "__main__":
    start = datetime.now()
    result = main()
    end = datetime.now()
    
    print()
    print("="*80)
    print(f"Finalizado: {end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duración total: {(end - start).total_seconds():.1f}s")
    print("="*80)
    
    sys.exit(0 if result else 1)
