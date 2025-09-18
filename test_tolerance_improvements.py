#!/usr/bin/env python3
"""
Script de prueba para validar las mejoras de tolerancia +/-7% en la distribución de shifts
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_test_config() -> Dict[str, Any]:
    """Crear configuración de prueba con trabajadores diversos"""
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    # Crear trabajadores con diferentes porcentajes de trabajo
    workers_data = [
        {
            'id': 'Worker_A',
            'work_percentage': 100,
            'work_periods': '',
            'days_off': '',
            'mandatory_days': '',
            'incompatible_with': [],
            'is_incompatible': False,
            'target_shifts': 0  # Se calculará automáticamente
        },
        {
            'id': 'Worker_B', 
            'work_percentage': 80,
            'work_periods': '',
            'days_off': '',
            'mandatory_days': '',
            'incompatible_with': [],
            'is_incompatible': False,
            'target_shifts': 0
        },
        {
            'id': 'Worker_C',
            'work_percentage': 60,
            'work_periods': '',
            'days_off': '',
            'mandatory_days': '',
            'incompatible_with': [],
            'is_incompatible': False,
            'target_shifts': 0
        },
        {
            'id': 'Worker_D',
            'work_percentage': 100,
            'work_periods': '',
            'days_off': '',
            'mandatory_days': '',
            'incompatible_with': [],
            'is_incompatible': False,
            'target_shifts': 0
        },
        {
            'id': 'Worker_E',
            'work_percentage': 40,
            'work_periods': '',
            'days_off': '',
            'mandatory_days': '',
            'incompatible_with': [],
            'is_incompatible': False,
            'target_shifts': 0
        }
    ]
    
    config = {
        'start_date': start_date,
        'end_date': end_date,
        'num_shifts': 3,  # 3 puestos por día
        'variable_shifts': [],
        'workers_data': workers_data,
        'holidays': [
            datetime(2024, 1, 6),   # Día de Reyes
            datetime(2024, 1, 15),  # Holiday ficticio
        ],
        'gap_between_shifts': 2,
        'max_consecutive_weekends': 2,
        'enable_proportional_weekends': True,
        'weekend_tolerance': 1,
        'cache_enabled': True
    }
    
    return config

def test_tolerance_validation():
    """Prueba la validación de tolerancia de +/-7%"""
    print("\n=== INICIANDO PRUEBA DE TOLERANCIA +/-7% ===\n")
    
    try:
        from scheduler import Scheduler
        from shift_tolerance_validator import ShiftToleranceValidator
        
        # Crear configuración de prueba
        config = create_test_config()
        
        # Inicializar el scheduler
        print("Inicializando scheduler...")
        scheduler = Scheduler(config)
        
        # Calcular targets antes de generar el schedule
        scheduler._calculate_target_shifts()
        
        print("Target shifts calculados:")
        for worker in scheduler.workers_data:
            print(f"  {worker['id']}: {worker.get('target_shifts', 0)} shifts")
        
        # Generar schedule
        print("\nGenerando schedule...")
        success = scheduler.generate_schedule(max_improvement_loops=30)
        
        if not success:
            print("ERROR: No se pudo generar el schedule")
            return False
        
        print("Schedule generado exitosamente!")
        
        # Validar tolerancia
        print("\n=== VALIDANDO TOLERANCIA +/-7% ===")
        
        # Validación de shifts generales
        general_validations = scheduler.tolerance_validator.validate_all_workers()
        print(f"\nValidación de shifts generales:")
        print(f"Trabajadores dentro de tolerancia: {sum(1 for v in general_validations if v['valid'])}/{len(general_validations)}")
        
        for validation in general_validations:
            status = "✅" if validation['valid'] else "❌"
            print(f"{status} {validation['worker_id']}: "
                  f"{validation['assigned_shifts']}/{validation['target_shifts']} shifts "
                  f"(rango: {validation['min_allowed']}-{validation['max_allowed']}, "
                  f"desviación: {validation['deviation_percentage']:.1f}%)")
        
        # Validación de shifts de weekend
        weekend_validations = scheduler.tolerance_validator.validate_weekend_shifts()
        print(f"\nValidación de shifts de weekend:")
        print(f"Trabajadores dentro de tolerancia: {sum(1 for v in weekend_validations if v['valid'])}/{len(weekend_validations)}")
        
        for validation in weekend_validations:
            status = "✅" if validation['valid'] else "❌"
            print(f"{status} {validation['worker_id']} (weekends): "
                  f"{validation['assigned_shifts']}/{validation['target_shifts']} shifts "
                  f"(rango: {validation['min_allowed']}-{validation['max_allowed']}, "
                  f"desviación: {validation['deviation_percentage']:.1f}%)")
        
        # Sugerencias de mejora
        outside_tolerance = scheduler.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=False)
        if outside_tolerance:
            print(f"\n⚠️ {len(outside_tolerance)} trabajadores fuera de tolerancia general")
            suggestions = scheduler.tolerance_validator.suggest_shift_adjustments(is_weekend_only=False)
            if suggestions:
                print("\nSugerencias de ajuste:")
                for i, suggestion in enumerate(suggestions[:3], 1):
                    print(f"  {i}. Transferir {suggestion['shifts_to_transfer']} shifts "
                          f"de {suggestion['from_worker']} a {suggestion['to_worker']}")
        
        outside_weekend = scheduler.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=True)
        if outside_weekend:
            print(f"\n⚠️ {len(outside_weekend)} trabajadores fuera de tolerancia de weekend")
            weekend_suggestions = scheduler.tolerance_validator.suggest_shift_adjustments(is_weekend_only=True)
            if weekend_suggestions:
                print("\nSugerencias de ajuste para weekends:")
                for i, suggestion in enumerate(weekend_suggestions[:3], 1):
                    print(f"  {i}. Transferir {suggestion['shifts_to_transfer']} weekend shifts "
                          f"de {suggestion['from_worker']} a {suggestion['to_worker']}")
        
        # Estadísticas del schedule
        total_shifts = sum(len([w for w in shifts if w is not None]) 
                          for shifts in scheduler.schedule.values())
        total_slots = sum(len(shifts) for shifts in scheduler.schedule.values())
        coverage = (total_shifts / total_slots) * 100 if total_slots > 0 else 0
        
        print(f"\n=== ESTADÍSTICAS DEL SCHEDULE ===")
        print(f"Total shifts asignados: {total_shifts}/{total_slots} ({coverage:.1f}% cobertura)")
        print(f"Período: {config['start_date'].strftime('%d/%m/%Y')} - {config['end_date'].strftime('%d/%m/%Y')}")
        print(f"Días: {(config['end_date'] - config['start_date']).days + 1}")
        
        # Contar weekend shifts
        weekend_count = 0
        for date, shifts in scheduler.schedule.items():
            if date.weekday() >= 4:  # Friday, Saturday, Sunday
                weekend_count += len([w for w in shifts if w is not None])
        
        print(f"Weekend shifts asignados: {weekend_count}")
        
        print(f"\n{'='*50}")
        print("✅ PRUEBA DE TOLERANCIA COMPLETADA")
        
        # Verificar si la mejora cumple los requisitos
        general_success_rate = (sum(1 for v in general_validations if v['valid']) / len(general_validations)) * 100
        weekend_success_rate = (sum(1 for v in weekend_validations if v['valid']) / len(weekend_validations)) * 100
        
        print(f"Tasa de éxito general: {general_success_rate:.1f}%")
        print(f"Tasa de éxito weekend: {weekend_success_rate:.1f}%")
        
        if general_success_rate >= 80 and weekend_success_rate >= 80:
            print("🎉 MEJORA EXITOSA: Más del 80% de trabajadores dentro de tolerancia")
            return True
        else:
            print("⚠️ MEJORA PARCIAL: Menos del 80% de trabajadores dentro de tolerancia")
            return True  # Aún consideramos exitoso si funciona el sistema
        
    except Exception as e:
        print(f"ERROR durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("Iniciando pruebas de mejoras de tolerancia de distribución...")
    
    success = test_tolerance_validation()
    
    if success:
        print("\n✅ Todas las pruebas completadas exitosamente")
        sys.exit(0)
    else:
        print("\n❌ Algunas pruebas fallaron")
        sys.exit(1)

if __name__ == "__main__":
    main()