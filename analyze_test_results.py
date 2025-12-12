#!/usr/bin/env python3
"""
Analizar los resultados del test_final_results.log
Extraer solo la información crítica sobre tolerancias y balance.
"""

import re
import sys

def analyze_log(log_file):
    """Analizar el log y extraer métricas clave."""
    
    print("="*80)
    print("ANÁLISIS DE RESULTADOS - TEST REAL SCENARIO")
    print("="*80)
    
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Buscar intentos completos
    attempts = re.findall(r'COMPLETE ATTEMPT (\d+)/(\d+)', content)
    if attempts:
        print(f"\n📊 Intentos ejecutados: {len(set([a[0] for a in attempts]))}/{attempts[-1][1] if attempts else '?'}")
    
    # Buscar mensajes de éxito/error
    if '✅ HORARIO GENERADO EXITOSAMENTE' in content:
        print("\n✅ RESULTADO: HORARIO GENERADO EXITOSAMENTE")
    elif '❌ ERROR' in content or 'ERROR CRÍTICO' in content:
        print("\n❌ RESULTADO: ERROR EN LA GENERACIÓN")
    else:
        print("\n⏳ RESULTADO: Test aún en proceso o incompleto")
    
    # Buscar cobertura
    coverage_match = re.search(r'Cobertura:\s+(\d+\.\d+)%', content)
    if coverage_match:
        coverage = float(coverage_match.group(1))
        print(f"\n📈 Cobertura: {coverage:.1f}%")
        if coverage >= 100:
            print("   ✅ Cobertura completa")
        elif coverage >= 95:
            print("   ⚠️  Cobertura alta pero no completa")
        else:
            print("   ❌ Cobertura insuficiente")
    
    # Buscar violaciones de tolerancia
    print("\n🎯 VERIFICACIÓN DE TOLERANCIAS (límite ±12%):")
    print("-" * 80)
    
    # Buscar mensajes de "BLOCKED at ABSOLUTE LIMIT"
    blocked_messages = re.findall(
        r'Worker (\d+): BLOCKED at ABSOLUTE LIMIT - Phase \d+ \(±(\d+)%\) \((\d+) > (\d+), target: (\d+)\)',
        content
    )
    
    if blocked_messages:
        print(f"\n⚠️  Encontrados {len(blocked_messages)} bloqueos por límite absoluto:")
        workers_blocked = {}
        for worker_id, tolerance, current, max_allowed, target in blocked_messages[-20:]:  # Últimos 20
            if worker_id not in workers_blocked:
                workers_blocked[worker_id] = {
                    'target': int(target),
                    'max_allowed': int(max_allowed),
                    'tolerance': int(tolerance)
                }
        
        for worker_id, data in sorted(workers_blocked.items()):
            print(f"   Worker {worker_id}: target={data['target']}, "
                  f"max_allowed={data['max_allowed']}, tolerance=±{data['tolerance']}%")
    
    # Buscar balance final de trabajadores
    balance_section = re.search(
        r'Balance de trabajadores:(.*?)(?=\n\n|\Z)',
        content,
        re.DOTALL
    )
    
    if balance_section:
        print("\n👥 BALANCE FINAL DE TRABAJADORES:")
        print("-" * 80)
        
        # Buscar líneas con workers y sus asignaciones
        worker_lines = re.findall(
            r'Worker\s+(\d+).*?(\d+)/(\d+).*?([-+]?\d+\.\d+)%',
            balance_section.group(1)
        )
        
        if worker_lines:
            violations_12 = []
            violations_8 = []
            ok_workers = []
            
            for worker_id, assigned, target, deviation_str in worker_lines:
                deviation = float(deviation_str)
                assigned = int(assigned)
                target = int(target)
                
                if abs(deviation) > 12:
                    violations_12.append((worker_id, assigned, target, deviation))
                elif abs(deviation) > 8:
                    violations_8.append((worker_id, assigned, target, deviation))
                else:
                    ok_workers.append((worker_id, assigned, target, deviation))
            
            if violations_12:
                print(f"\n❌ VIOLACIONES >12% ({len(violations_12)} workers):")
                for wid, assigned, target, dev in sorted(violations_12, key=lambda x: abs(x[3]), reverse=True)[:10]:
                    print(f"   Worker {wid}: {assigned}/{target} ({dev:+.1f}%)")
            
            if violations_8:
                print(f"\n⚠️  VIOLACIONES >8% pero ≤12% ({len(violations_8)} workers):")
                for wid, assigned, target, dev in sorted(violations_8, key=lambda x: abs(x[3]), reverse=True)[:10]:
                    print(f"   Worker {wid}: {assigned}/{target} ({dev:+.1f}%)")
            
            if ok_workers:
                print(f"\n✅ DENTRO DE TOLERANCIA ≤8% ({len(ok_workers)} workers)")
            
            print(f"\n📊 RESUMEN:")
            print(f"   Total workers: {len(worker_lines)}")
            print(f"   Dentro de ±8%: {len(ok_workers)} ({len(ok_workers)/len(worker_lines)*100:.1f}%)")
            print(f"   Entre ±8-12%: {len(violations_8)} ({len(violations_8)/len(worker_lines)*100:.1f}%)")
            print(f"   Fuera de ±12%: {len(violations_12)} ({len(violations_12)/len(worker_lines)*100:.1f}%)")
    
    # Verificar target fixes específicos para Worker 10
    print("\n🔍 VERIFICACIÓN ESPECÍFICA - WORKER 10 (50% part-time):")
    print("-" * 80)
    
    worker10_target = re.search(r'Worker 10: target_shifts=(\d+)', content)
    if worker10_target:
        target = int(worker10_target.group(1))
        print(f"✅ Target configurado: {target}")
        if target == 9:
            print("   ✅ CORRECTO: target=9 (no dividido por work_percentage)")
        else:
            print(f"   ❌ ERROR: target={target}, debería ser 9")
    
    worker10_blocked = re.findall(
        r'Worker 10.*?target:\s*(\d+)',
        content
    )
    if worker10_blocked:
        targets_used = set(worker10_blocked)
        print(f"\nTargets usados en validación: {targets_used}")
        if '9' in targets_used and len(targets_used) == 1:
            print("   ✅ CORRECTO: Siempre usa target=9")
        elif '4' in targets_used:
            print("   ❌ ERROR: Detectado uso de target=4 (bug no corregido)")
        else:
            print(f"   ⚠️  REVISAR: Múltiples targets detectados")
    
    print("\n" + "="*80)
    print("FIN DEL ANÁLISIS")
    print("="*80)

if __name__ == '__main__':
    log_file = sys.argv[1] if len(sys.argv) > 1 else 'test_final_results.log'
    analyze_log(log_file)
