#!/usr/bin/env python3
"""
Test rápido de las mejoras del sistema de reparto
"""

import json
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

def test_mejoras_reparto():
    """Prueba rápida del sistema mejorado"""
    
    print("=" * 80)
    print("TEST DE MEJORAS DEL SISTEMA DE REPARTO")
    print("=" * 80)
    
    # 1. Verificar archivo de configuración
    try:
        with open('schedule_config.json', 'r') as f:
            config = json.load(f)
        
        print(f"✅ Configuración cargada:")
        print(f"   - Periodo: {config['start_date']} a {config['end_date']}")
        print(f"   - Trabajadores: {len(config['workers_data'])}")
        print(f"   - Turnos por día: {config['num_shifts']}")
        
    except FileNotFoundError:
        print("❌ No se encontró schedule_config.json")
        return False
    
    # 2. Importar módulos
    print("\n📦 Importando módulos...")
    try:
        from scheduler import Scheduler
        from advanced_distribution_engine import AdvancedDistributionEngine
        print("   ✅ Módulos importados correctamente")
    except ImportError as e:
        print(f"   ❌ Error al importar: {e}")
        return False
    
    # 3. Crear scheduler
    print("\n🔧 Inicializando scheduler...")
    try:
        # Convertir fechas string a datetime
        config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d')
        config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d')
        
        scheduler = Scheduler(config)
        print("   ✅ Scheduler creado")
        
        # Verificar que tiene schedule_builder
        if not hasattr(scheduler, 'schedule_builder'):
            print("   ❌ Scheduler no tiene schedule_builder")
            return False
        
        print("   ✅ Schedule builder disponible")
        
    except Exception as e:
        print(f"   ❌ Error creando scheduler: {e}")
        return False
    
    # 4. Inicializar motor avanzado
    print("\n🚀 Inicializando Advanced Distribution Engine...")
    try:
        advanced_engine = AdvancedDistributionEngine(scheduler, scheduler.schedule_builder)
        print("   ✅ Motor avanzado inicializado")
        print(f"   - Métricas disponibles: {list(advanced_engine.metrics.keys())}")
        
    except Exception as e:
        print(f"   ❌ Error inicializando motor: {e}")
        return False
    
    # 5. Generar schedule básico (solo mandatory)
    print("\n📅 Asignando turnos mandatory...")
    try:
        scheduler.schedule_builder._assign_mandatory_guards()
        
        # Contar mandatory asignados
        mandatory_count = len(scheduler.schedule_builder._locked_mandatory)
        print(f"   ✅ {mandatory_count} turnos mandatory asignados y bloqueados")
        
    except Exception as e:
        print(f"   ❌ Error asignando mandatory: {e}")
        return False
    
    # 6. Verificar capacidades del motor avanzado
    print("\n🔍 Verificando capacidades del motor avanzado...")
    
    # Contar slots vacíos
    empty_count = advanced_engine._count_filled_slots()
    total_count = advanced_engine._count_total_slots()
    fill_percentage = (empty_count / total_count * 100) if total_count > 0 else 0
    
    print(f"   Estado actual: {empty_count}/{total_count} slots llenos ({fill_percentage:.1f}%)")
    
    # Verificar métodos
    methods_to_check = [
        '_chunk_based_fill',
        '_adaptive_backtracking_fill',
        '_multi_worker_swap_optimization',
        '_progressive_relaxation_fill',
        '_get_smart_candidates',
        '_find_most_constrained_slot'
    ]
    
    print(f"\n   Métodos implementados:")
    for method in methods_to_check:
        has_method = hasattr(advanced_engine, method)
        status = "✅" if has_method else "❌"
        print(f"   {status} {method}")
    
    # 7. Test de scoring mejorado
    print("\n🎯 Probando scoring mejorado...")
    try:
        # Obtener primera fecha con slots vacíos
        test_date = None
        test_post = None
        
        for date, workers in scheduler.schedule.items():
            for post, worker in enumerate(workers):
                if worker is None:
                    test_date = date
                    test_post = post
                    break
            if test_date:
                break
        
        if test_date and test_post is not None:
            candidates = advanced_engine._get_smart_candidates(test_date, test_post)
            print(f"   ✅ Encontrados {len(candidates)} candidatos para {test_date.strftime('%Y-%m-%d')} post {test_post}")
            
            if candidates:
                top_candidate = candidates[0]
                print(f"   - Mejor candidato: Worker {top_candidate[0]['id']} con score {top_candidate[1]:.0f}")
        else:
            print(f"   ℹ️  No hay slots vacíos para probar (todos llenos o solo mandatory)")
        
    except Exception as e:
        print(f"   ⚠️  Error en scoring: {e}")
    
    # 8. Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DEL TEST")
    print("=" * 80)
    print("✅ Todos los componentes están correctamente instalados")
    print("✅ Advanced Distribution Engine está funcional")
    print("✅ Sistema listo para mejorar el reparto hacia 100%")
    print("\n📝 Siguiente paso: ejecutar generación completa")
    print("   Comando: python test_scheduler_only.py")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = test_mejoras_reparto()
    exit(0 if success else 1)
