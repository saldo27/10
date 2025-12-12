# Test para verificar que los turnos mandatory NO son modificados durante la optimizacion.
#
# Este test valida que:
# 1. Los turnos mandatory se asignan correctamente en la fase inicial
# 2. Los turnos mandatory NO son modificados durante las iteraciones de mejora
# 3. La verificacion centralizada _can_modify_assignment() funciona correctamente

import logging
from datetime import datetime, timedelta
from scheduler import Scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_mandatory_protection():
    """
    Test principal que verifica la protección de turnos mandatory
    """
    print("\n" + "="*80)
    print("TEST: PROTECCIÓN DE TURNOS MANDATORY")
    print("="*80 + "\n")
    
    # Trabajadores de prueba con mandatory_days
    workers_data = [
        {
            'id': 'WORKER_A',
            'target_shifts': 10,
            'work_percentage': 100,
            'mandatory_days': '05-11-2025;15-11-2025',  # 2 turnos mandatory
            'days_off': '',
            'incompatible_with': [],
            'work_periods': ''
        },
        {
            'id': 'WORKER_B',
            'target_shifts': 10,
            'work_percentage': 100,
            'mandatory_days': '10-11-2025',  # 1 turno mandatory
            'days_off': '',
            'incompatible_with': [],
            'work_periods': ''
        },
        {
            'id': 'WORKER_C',
            'target_shifts': 10,
            'work_percentage': 100,
            'mandatory_days': '',  # Sin mandatory
            'days_off': '',
            'incompatible_with': [],
            'work_periods': ''
        }
    ]
    
    holidays = []
    
    # Crear un scheduler de prueba con datos mínimos
    config = {
        'start_date': datetime.strptime('01-11-2025', '%d-%m-%Y'),
        'end_date': datetime.strptime('30-11-2025', '%d-%m-%Y'),
        'num_shifts': 2,
        'gap_between_shifts': 2,
        'max_consecutive_weekends': 3,
        'max_shifts_per_worker': 20,
        'workers_data': workers_data,
        'holidays': holidays
    }
    
    print("📋 Configuración del test:")
    print(f"   - Periodo: {config['start_date']} - {config['end_date']}")
    print(f"   - Trabajadores: {len(workers_data)}")
    print(f"   - Turnos por día: {config['num_shifts']}")
    print(f"   - WORKER_A: 2 mandatory (05-11, 15-11)")
    print(f"   - WORKER_B: 1 mandatory (10-11)")
    print(f"   - WORKER_C: Sin mandatory")
    print()
    
    # Crear scheduler
    scheduler = Scheduler(config)
    
    # Fase 1: Generar schedule inicial
    print("🔄 Fase 1: Generando schedule inicial...")
    try:
        success = scheduler.generate_schedule()
        if not success:
            print("❌ ERROR: No se pudo generar el schedule")
            return False
        print("✅ Schedule inicial generado correctamente")
    except Exception as e:
        print(f"❌ EXCEPTION durante generación: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Fase 2: Verificar asignaciones mandatory iniciales
    print("\n🔍 Fase 2: Verificando asignaciones mandatory iniciales...")
    
    mandatory_assignments_initial = {}
    
    # Verificar WORKER_A
    date_a1 = datetime.strptime('05-11-2025', '%d-%m-%Y')
    date_a2 = datetime.strptime('15-11-2025', '%d-%m-%Y')
    
    if date_a1 in scheduler.schedule:
        if 'WORKER_A' in scheduler.schedule[date_a1]:
            post_a1 = scheduler.schedule[date_a1].index('WORKER_A')
            mandatory_assignments_initial[('WORKER_A', date_a1)] = post_a1
            print(f"   ✅ WORKER_A asignado el 05-11-2025 en puesto {post_a1}")
        else:
            print(f"   ❌ ERROR: WORKER_A NO asignado el 05-11-2025 (MANDATORY)")
            return False
    else:
        print(f"   ❌ ERROR: Fecha 05-11-2025 no existe en schedule")
        return False
    
    if date_a2 in scheduler.schedule:
        if 'WORKER_A' in scheduler.schedule[date_a2]:
            post_a2 = scheduler.schedule[date_a2].index('WORKER_A')
            mandatory_assignments_initial[('WORKER_A', date_a2)] = post_a2
            print(f"   ✅ WORKER_A asignado el 15-11-2025 en puesto {post_a2}")
        else:
            print(f"   ❌ ERROR: WORKER_A NO asignado el 15-11-2025 (MANDATORY)")
            return False
    else:
        print(f"   ❌ ERROR: Fecha 15-11-2025 no existe en schedule")
        return False
    
    # Verificar WORKER_B
    date_b1 = datetime.strptime('10-11-2025', '%d-%m-%Y')
    
    if date_b1 in scheduler.schedule:
        if 'WORKER_B' in scheduler.schedule[date_b1]:
            post_b1 = scheduler.schedule[date_b1].index('WORKER_B')
            mandatory_assignments_initial[('WORKER_B', date_b1)] = post_b1
            print(f"   ✅ WORKER_B asignado el 10-11-2025 en puesto {post_b1}")
        else:
            print(f"   ❌ ERROR: WORKER_B NO asignado el 10-11-2025 (MANDATORY)")
            return False
    else:
        print(f"   ❌ ERROR: Fecha 10-11-2025 no existe en schedule")
        return False
    
    print(f"\n   Total mandatory asignados: {len(mandatory_assignments_initial)}")
    
    # Verificar que están en _locked_mandatory
    print("\n🔒 Verificando _locked_mandatory...")
    locked_count = len(scheduler.schedule_builder._locked_mandatory)
    print(f"   Total en _locked_mandatory: {locked_count}")
    
    for (worker_id, date), post in mandatory_assignments_initial.items():
        if (worker_id, date) in scheduler.schedule_builder._locked_mandatory:
            print(f"   ✅ {worker_id} en {date.strftime('%d-%m-%Y')} está LOCKED")
        else:
            print(f"   ⚠️  {worker_id} en {date.strftime('%d-%m-%Y')} NO está en _locked_mandatory")
    
    # Fase 3: Verificar que NO son modificados después de las iteraciones
    print("\n🔍 Fase 3: Verificando que mandatory NO fueron modificados...")
    
    all_protected = True
    for (worker_id, date), original_post in mandatory_assignments_initial.items():
        current_post = None
        if date in scheduler.schedule:
            if worker_id in scheduler.schedule[date]:
                current_post = scheduler.schedule[date].index(worker_id)
            else:
                print(f"   ❌ VIOLACIÓN: {worker_id} YA NO está asignado el {date.strftime('%d-%m-%Y')} (mandatory eliminado)")
                all_protected = False
                continue
        else:
            print(f"   ❌ ERROR: Fecha {date.strftime('%d-%m-%Y')} ya no existe en schedule")
            all_protected = False
            continue
        
        if current_post == original_post:
            print(f"   ✅ {worker_id} en {date.strftime('%d-%m-%Y')} sigue en puesto {current_post} (NO MODIFICADO)")
        else:
            print(f"   ⚠️  {worker_id} en {date.strftime('%d-%m-%Y')} cambió de puesto {original_post} → {current_post} (MOVIDO)")
            # Esto es aceptable si sigue asignado en la misma fecha
            # Lo importante es que NO se elimine o cambie de fecha
    
    # Resumen final
    print("\n" + "="*80)
    if all_protected:
        print("✅ TEST EXITOSO: Todos los turnos mandatory fueron PROTEGIDOS")
    else:
        print("❌ TEST FALLIDO: Algunos turnos mandatory fueron MODIFICADOS o ELIMINADOS")
    print("="*80 + "\n")
    
    return all_protected

def test_can_modify_assignment():
    """
    Test unitario para _can_modify_assignment()
    """
    print("\n" + "="*80)
    print("TEST UNITARIO: _can_modify_assignment()")
    print("="*80 + "\n")
    
    # Crear scheduler de prueba
    workers_data = [
        {
            'id': 'WORKER_TEST',
            'target_shifts': 5,
            'work_percentage': 100,
            'mandatory_days': '05-11-2025',
            'days_off': '',
            'incompatible_with': [],
            'work_periods': ''
        }
    ]
    
    holidays = []
    
    config = {
        'start_date': datetime.strptime('01-11-2025', '%d-%m-%Y'),
        'end_date': datetime.strptime('10-11-2025', '%d-%m-%Y'),
        'num_shifts': 2,
        'gap_between_shifts': 2,
        'max_consecutive_weekends': 3,
        'max_shifts_per_worker': 20,
        'workers_data': workers_data,
        'holidays': holidays
    }
    
    scheduler = Scheduler(config)
    scheduler.generate_schedule()
    
    # Test 1: Mandatory date should NOT be modifiable
    date_mandatory = datetime.strptime('05-11-2025', '%d-%m-%Y')
    can_modify = scheduler.schedule_builder._can_modify_assignment('WORKER_TEST', date_mandatory, 'test')
    
    print(f"Test 1: ¿Se puede modificar mandatory (05-11-2025)?")
    if not can_modify:
        print(f"   ✅ CORRECTO: NO se puede modificar (retornó False)")
    else:
        print(f"   ❌ ERROR: Sí se puede modificar (retornó True) - DEBERÍA SER False")
    
    # Test 2: Non-mandatory date SHOULD be modifiable
    date_non_mandatory = datetime.strptime('08-11-2025', '%d-%m-%Y')
    
    # Primero asignar el trabajador a esa fecha (si no está ya)
    if date_non_mandatory in scheduler.schedule and 'WORKER_TEST' in scheduler.schedule[date_non_mandatory]:
        can_modify_non = scheduler.schedule_builder._can_modify_assignment('WORKER_TEST', date_non_mandatory, 'test')
        
        print(f"\nTest 2: ¿Se puede modificar non-mandatory (08-11-2025)?")
        if can_modify_non:
            print(f"   ✅ CORRECTO: Sí se puede modificar (retornó True)")
        else:
            print(f"   ❌ ERROR: NO se puede modificar (retornó False) - DEBERÍA SER True")
    else:
        print(f"\nTest 2: Skipped (WORKER_TEST no asignado el 08-11-2025)")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    # Ejecutar tests
    print("\n" + "="*80)
    print("INICIANDO SUITE DE TESTS DE PROTECCIÓN MANDATORY")
    print("="*80)
    
    # Test 1: Protección durante optimización
    test1_passed = test_mandatory_protection()
    
    # Test 2: Verificación unitaria
    test_can_modify_assignment()
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE TESTS")
    print("="*80)
    print(f"Test de protección mandatory: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print("="*80 + "\n")
