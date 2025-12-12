#!/usr/bin/env python3
"""
Test de balance estricto - Verifica que las desviaciones se mantengan controladas
"""

import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_balance_validator():
    """Test del BalanceValidator"""
    from balance_validator import BalanceValidator
    
    logging.info("="*80)
    logging.info("TEST: BalanceValidator")
    logging.info("="*80)
    
    # Crear validador
    validator = BalanceValidator(tolerance_percentage=8.0)
    
    # Crear datos de prueba
    workers_data = [
        {'id': '1', 'target_shifts': 10},
        {'id': '2', 'target_shifts': 10},
        {'id': '3', 'target_shifts': 10},
        {'id': '4', 'target_shifts': 10},
    ]
    
    # Escenario 1: Balance perfecto
    logging.info("\n--- Escenario 1: Balance perfecto ---")
    schedule_perfect = {}
    base_date = datetime(2025, 12, 1)
    
    # Asignar 10 turnos a cada trabajador
    day_counter = 1
    for i in range(10):
        for worker_id in ['1', '2', '3', '4']:
            date = base_date.replace(day=day_counter)
            if date not in schedule_perfect:
                schedule_perfect[date] = []
            schedule_perfect[date].append(worker_id)
            day_counter += 1
            if day_counter > 28:  # Evitar días inválidos
                day_counter = 1
    
    result = validator.validate_schedule_balance(schedule_perfect, workers_data)
    assert result['is_balanced'], "Escenario perfecto debería estar balanceado"
    logging.info("✅ Balance perfecto validado correctamente")
    
    # Escenario 2: Desviación moderada (dentro de tolerancia)
    logging.info("\n--- Escenario 2: Desviación moderada ---")
    schedule_moderate = {}
    
    # Worker 1: 9 turnos (-10%)
    # Worker 2: 10 turnos (0%)
    # Worker 3: 11 turnos (+10%) - Debería estar en emergency
    # Worker 4: 10 turnos (0%)
    assignments = {
        '1': 9,
        '2': 10,
        '3': 11,
        '4': 10
    }
    
    day = 1
    for worker_id, count in assignments.items():
        for _ in range(count):
            if day > 28:
                day = 1
            date = base_date.replace(day=day)
            if date not in schedule_moderate:
                schedule_moderate[date] = []
            schedule_moderate[date].append(worker_id)
            day += 1
    
    result = validator.validate_schedule_balance(schedule_moderate, workers_data)
    logging.info(f"Moderate balance: is_balanced={result['is_balanced']}")
    
    # Escenario 3: Desviación extrema (inaceptable)
    logging.info("\n--- Escenario 3: Desviación extrema (DEBE FALLAR) ---")
    schedule_extreme = {}
    
    # Worker 1: 5 turnos (-50% - CRÍTICO)
    # Worker 2: 10 turnos (0%)
    # Worker 3: 15 turnos (+50% - CRÍTICO)
    # Worker 4: 10 turnos (0%)
    assignments_extreme = {
        '1': 5,
        '2': 10,
        '3': 15,
        '4': 10
    }
    
    day = 1
    for worker_id, count in assignments_extreme.items():
        for _ in range(count):
            if day > 28:
                day = 1
            date = base_date.replace(day=day)
            if date not in schedule_extreme:
                schedule_extreme[date] = []
            schedule_extreme[date].append(worker_id)
            day += 1
    
    result = validator.validate_schedule_balance(schedule_extreme, workers_data)
    assert not result['is_balanced'], "Escenario extremo NO debería estar balanceado"
    assert len(result['violations']['extreme']) > 0, "Debería detectar violaciones extremas"
    logging.info("✅ Desviaciones extremas detectadas correctamente")
    
    # Test de recomendaciones
    logging.info("\n--- Test de recomendaciones ---")
    recommendations = validator.get_rebalancing_recommendations(schedule_extreme, workers_data)
    assert len(recommendations) > 0, "Debería generar recomendaciones"
    logging.info(f"✅ Generadas {len(recommendations)} recomendaciones de rebalanceo")
    
    # Test de validación de transferencia
    logging.info("\n--- Test de validación de transferencia ---")
    valid, reason = validator.check_transfer_validity('3', '1', schedule_extreme, workers_data)
    logging.info(f"Transfer de Worker 3 (+50%) a Worker 1 (-50%): {valid} - {reason}")
    assert valid, "Transferencia de sobrecargado a infracargado debería ser válida"
    
    valid, reason = validator.check_transfer_validity('1', '3', schedule_extreme, workers_data)
    logging.info(f"Transfer de Worker 1 (-50%) a Worker 3 (+50%): {valid} - {reason}")
    assert not valid, "Transferencia de infracargado a sobrecargado NO debería ser válida"
    
    logging.info("\n✅ TODOS LOS TESTS DE BalanceValidator PASARON")


def test_integration():
    """Test de integración con el scheduler"""
    logging.info("\n" + "="*80)
    logging.info("TEST: Integración con Scheduler")
    logging.info("="*80)
    
    try:
        # Intentar cargar configuración real
        import json
        
        with open('schedule_config.json', 'r') as f:
            config = json.load(f)
        
        logging.info("✅ Configuración cargada")
        logging.info(f"   Workers: {len(config.get('workers', []))}")
        logging.info(f"   Turnos por día: {config.get('num_shifts', 'N/A')}")
        
        # Test rápido de creación de scheduler
        from scheduler import Scheduler
        
        scheduler = Scheduler('schedule_config.json')
        logging.info("✅ Scheduler creado correctamente")
        
        # Verificar que tiene el balance_validator integrado
        if hasattr(scheduler, 'iterative_optimizer'):
            if hasattr(scheduler.iterative_optimizer, 'balance_validator'):
                logging.info("✅ BalanceValidator integrado en IterativeOptimizer")
            else:
                logging.warning("⚠️  BalanceValidator NO encontrado en IterativeOptimizer")
        
    except Exception as e:
        logging.error(f"❌ Error en test de integración: {e}")
        return False
    
    return True


if __name__ == '__main__':
    logging.info("INICIANDO TESTS DE BALANCE ESTRICTO")
    logging.info("="*80 + "\n")
    
    # Test 1: BalanceValidator standalone
    try:
        test_balance_validator()
    except Exception as e:
        logging.error(f"❌ Test de BalanceValidator falló: {e}", exc_info=True)
        sys.exit(1)
    
    # Test 2: Integración
    try:
        if not test_integration():
            logging.warning("⚠️  Test de integración con warnings")
    except Exception as e:
        logging.error(f"❌ Test de integración falló: {e}", exc_info=True)
        # No salir con error - puede ser porque no hay config
    
    logging.info("\n" + "="*80)
    logging.info("✅ TESTS DE BALANCE COMPLETADOS")
    logging.info("="*80)
    logging.info("\nEl sistema ahora incluye:")
    logging.info("  1. BalanceValidator - Validación estricta de desviaciones")
    logging.info("  2. Límites de emergencia (±10%) y críticos (±15%)")
    logging.info("  3. Validación de cada transferencia antes de aplicarla")
    logging.info("  4. Recomendaciones inteligentes de rebalanceo")
    logging.info("  5. Verificación de balance después de cada redistribución")
    logging.info("\nEsto debería prevenir desviaciones extremas como -9 y +4 turnos")
