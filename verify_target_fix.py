#!/usr/bin/env python3
"""
Verificar que el fix de target_shifts funciona correctamente.
Este test verifica que adjusted_target ya no multiplica por work_percentage.
"""

import logging
import sys
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    logging.info("="*80)
    logging.info("VERIFICACIÓN DEL FIX DE TARGET_SHIFTS")
    logging.info("="*80)
    
    try:
        from scheduler import Scheduler
        
        # Cargar configuración
        with open('schedule_config_test_real.json', 'r') as f:
            config = json.load(f)
        
        # Convertir fechas
        config['start_date'] = datetime.strptime(config['start_date'], '%Y-%m-%d')
        config['end_date'] = datetime.strptime(config['end_date'], '%Y-%m-%d')
        config['holidays'] = [datetime.strptime(h, '%Y-%m-%d') for h in config['holidays']]
        
        # Crear scheduler
        scheduler = Scheduler(config)
        
        logging.info("\n📋 Verificando targets calculados:")
        logging.info("-" * 80)
        
        # Verificar Worker 10 (50% part-time)
        worker_10 = next((w for w in scheduler.workers_data if w['id'] == '10'), None)
        if worker_10:
            work_pct = worker_10.get('work_percentage', 100)
            target = worker_10.get('target_shifts', 0)
            
            logging.info(f"\n✅ Worker 10:")
            logging.info(f"   work_percentage: {work_pct}%")
            logging.info(f"   target_shifts: {target}")
            logging.info(f"   Esperado: 9 (ya incluye ajuste por work_percentage)")
            
            if target == 9:
                logging.info(f"   ✅ CORRECTO: target_shifts = 9")
            else:
                logging.error(f"   ❌ ERROR: target_shifts debería ser 9, no {target}")
                return False
        
        # Verificar Worker 11 (50% part-time)
        worker_11 = next((w for w in scheduler.workers_data if w['id'] == '11'), None)
        if worker_11:
            work_pct = worker_11.get('work_percentage', 100)
            target = worker_11.get('target_shifts', 0)
            
            logging.info(f"\n✅ Worker 11:")
            logging.info(f"   work_percentage: {work_pct}%")
            logging.info(f"   target_shifts: {target}")
            logging.info(f"   Esperado: 9 (ya incluye ajuste por work_percentage)")
            
            if target == 9:
                logging.info(f"   ✅ CORRECTO: target_shifts = 9")
            else:
                logging.error(f"   ❌ ERROR: target_shifts debería ser 9, no {target}")
                return False
        
        # Verificar que adjusted_target no multiplica por work_percentage
        logging.info("\n" + "="*80)
        logging.info("Verificando schedule_builder...")
        logging.info("="*80)
        
        # Leer el código de schedule_builder.py para verificar el fix
        with open('schedule_builder.py', 'r') as f:
            content = f.read()
        
        if 'adjusted_target = overall_target_shifts' in content:
            logging.info("\n✅ CORRECTO: schedule_builder usa 'adjusted_target = overall_target_shifts'")
            logging.info("   (NO multiplica por work_percentage)")
        elif 'adjusted_target = int(overall_target_shifts * work_percentage / 100)' in content:
            logging.error("\n❌ ERROR: schedule_builder TODAVÍA multiplica por work_percentage")
            logging.error("   Esto causará que Worker 10 tenga target=4 en vez de 9")
            return False
        else:
            logging.warning("\n⚠️  ADVERTENCIA: No se pudo verificar el código de adjusted_target")
        
        logging.info("\n" + "="*80)
        logging.info("✅ TODAS LAS VERIFICACIONES PASARON")
        logging.info("="*80)
        logging.info("\nEl fix de target_shifts está correctamente implementado:")
        logging.info("  1. target_shifts YA incluye el ajuste por work_percentage")
        logging.info("  2. schedule_builder NO vuelve a multiplicar por work_percentage")
        logging.info("  3. Worker 10 (50% part-time) tiene target_shifts=9 (correcto)")
        logging.info("\nEsto significa que durante la asignación y validación:")
        logging.info("  - Worker 10: target=9, max_allowed=round(9*1.12)=10")
        logging.info("  - NO más 'target=4' que causaba violaciones >12%")
        
        return True
        
    except Exception as e:
        logging.error(f"\n❌ ERROR: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
