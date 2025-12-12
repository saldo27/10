#!/usr/bin/env python3
"""
Script de verificación avanzada para detectar modificaciones de mandatory shifts.
Analiza el log completo y detecta si algún mandatory fue modificado después de ser asignado.
"""

import sys
import re
from datetime import datetime
from collections import defaultdict

def parse_comprehensive_log(log_file_path):
    """
    Análisis exhaustivo del log para detectar violaciones de mandatory.
    """
    print("=" * 80)
    print("VERIFICACIÓN EXHAUSTIVA DE MANDATORY SHIFTS")
    print("=" * 80)
    print(f"\nAnalizando: {log_file_path}\n")
    
    # Tracking de mandatory assignments
    mandatory_assigned = {}  # {(worker, date): line_num}
    locked_mandatory = set()  # {(worker, date)}
    
    # Tracking de modificaciones
    all_assignments = defaultdict(list)  # {(worker, date): [line_nums]}
    blocked_attempts = []  # [(worker, date, operation, line_num)]
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Detectar asignaciones de mandatory y lock
                if '🔒 MANDATORY ASSIGNED AND LOCKED' in line:
                    match = re.search(r'🔒 MANDATORY ASSIGNED AND LOCKED: (\w+) → (\d{4}-\d{2}-\d{2})', line)
                    if match:
                        worker = match.group(1)
                        date = match.group(2)
                        mandatory_assigned[(worker, date)] = line_num
                        locked_mandatory.add((worker, date))
                
                # Detectar intentos bloqueados
                if '🔒 BLOCKED' in line:
                    match = re.search(r'🔒 BLOCKED.*?(\w+).*?(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        worker = match.group(1)
                        date = match.group(2)
                        operation = "unknown"
                        if 'Pass1' in line:
                            operation = "Pass1 Fill"
                        elif 'Initial Fill' in line:
                            operation = "Initial Fill"
                        elif 'balance' in line.lower():
                            operation = "Balance"
                        elif 'swap' in line.lower():
                            operation = "Swap"
                        elif 'transfer' in line.lower():
                            operation = "Transfer"
                        blocked_attempts.append((worker, date, operation, line_num))
                
                # Detectar CUALQUIER asignación a schedule (para detectar sobrescrituras)
                if 'Assigned worker' in line or 'assigned' in line.lower():
                    match = re.search(r'(\w+).*?(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        worker = match.group(1)
                        date = match.group(2)
                        all_assignments[(worker, date)].append(line_num)
                
                # Detectar operaciones de redistribución/rebalanceo que mencionan workers
                if any(keyword in line for keyword in ['Moved shift', 'Redistributed', 'Balanced', 'Swapped']):
                    # Intentar extraer workers y fechas
                    matches = re.findall(r'(\w+).*?(\d{4}-\d{2}-\d{2})', line)
                    for match in matches:
                        worker = match[0]
                        date = match[1]
                        all_assignments[(worker, date)].append(line_num)
    
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {log_file_path}")
        return
    except Exception as e:
        print(f"❌ Error al leer el archivo: {str(e)}")
        return
    
    # Análisis de mandatory asignados
    print("📋 MANDATORY SHIFTS DETECTADOS:")
    print("-" * 80)
    
    if mandatory_assigned:
        worker_mandatory = defaultdict(list)
        for (worker, date), line_num in mandatory_assigned.items():
            worker_mandatory[worker].append((date, line_num))
        
        for worker in sorted(worker_mandatory.keys()):
            dates = worker_mandatory[worker]
            print(f"\n  {worker}: {len(dates)} mandatory shifts")
            for date, line_num in sorted(dates):
                print(f"    🔒 {date} (línea {line_num})")
        
        print(f"\n  Total mandatory detectados: {len(mandatory_assigned)}")
    else:
        print("  ⚠️  No se detectaron mandatory shifts marcados con 🔒")
    
    # Análisis de intentos bloqueados
    print("\n" + "=" * 80)
    print("🛡️  INTENTOS DE MODIFICACIÓN BLOQUEADOS:")
    print("-" * 80)
    
    if blocked_attempts:
        operation_count = defaultdict(int)
        for worker, date, operation, line_num in blocked_attempts:
            operation_count[operation] += 1
        
        print(f"\n  Total de bloqueos exitosos: {len(blocked_attempts)}")
        print(f"\n  Por tipo de operación:")
        for operation in sorted(operation_count.keys()):
            count = operation_count[operation]
            print(f"    {operation}: {count} bloqueos")
        
        # Verificar que todos los mandatory fueron protegidos
        mandatory_protected = set()
        for worker, date, operation, line_num in blocked_attempts:
            if (worker, date) in locked_mandatory:
                mandatory_protected.add((worker, date))
        
        protection_rate = len(mandatory_protected) / len(locked_mandatory) * 100 if locked_mandatory else 0
        
        print(f"\n  Mandatory protegidos durante operaciones: {len(mandatory_protected)}/{len(locked_mandatory)} ({protection_rate:.1f}%)")
        
        # Mostrar primeros 5 bloqueos
        print(f"\n  Primeros 5 bloqueos detectados:")
        for worker, date, operation, line_num in blocked_attempts[:5]:
            mandatory_marker = "🔒" if (worker, date) in locked_mandatory else "  "
            print(f"    {mandatory_marker} {worker} en {date} - {operation} (línea {line_num})")
    else:
        print("  ℹ️  No se detectaron intentos de modificación bloqueados")
        print("  ⚠️  Esto podría indicar que NO se están bloqueando las modificaciones")
    
    # Verificación de violaciones: mandatory que aparecen múltiples veces
    print("\n" + "=" * 80)
    print("🔍 VERIFICACIÓN DE VIOLACIONES:")
    print("-" * 80)
    
    violations_found = []
    
    for (worker, date) in locked_mandatory:
        if (worker, date) in all_assignments:
            assignment_lines = all_assignments[(worker, date)]
            if len(assignment_lines) > 1:
                # Verificar si hay re-asignaciones después de la inicial
                initial_line = mandatory_assigned[(worker, date)]
                later_assignments = [l for l in assignment_lines if l > initial_line]
                
                if later_assignments:
                    violations_found.append((worker, date, initial_line, later_assignments))
    
    if violations_found:
        print(f"\n  ❌ {len(violations_found)} POSIBLES VIOLACIONES DETECTADAS:")
        for worker, date, initial_line, later_lines in violations_found:
            print(f"\n    ❌ {worker} en {date}:")
            print(f"       Asignación inicial (mandatory): línea {initial_line}")
            print(f"       Re-asignaciones sospechosas: líneas {later_lines}")
    else:
        print("  ✅ No se detectaron violaciones evidentes")
        print("  ✅ Ningún mandatory fue re-asignado después de su asignación inicial")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL:")
    print("=" * 80)
    print(f"  Mandatory detectados: {len(mandatory_assigned)}")
    print(f"  Locked set: {len(locked_mandatory)}")
    print(f"  Intentos bloqueados: {len(blocked_attempts)}")
    print(f"  Posibles violaciones: {len(violations_found)}")
    
    if len(violations_found) == 0 and len(blocked_attempts) > 0:
        print("\n  ✅ ESTADO: EXCELENTE - Todos los mandatory están protegidos")
        print("  ✅ El sistema está bloqueando correctamente las modificaciones")
    elif len(violations_found) == 0 and len(blocked_attempts) == 0:
        print("\n  ⚠️  ESTADO: INCIERTO - No hay violaciones pero tampoco bloqueos")
        print("  ⚠️  Posiblemente no hubo intentos de modificar mandatory")
    else:
        print("\n  ❌ ESTADO: CRÍTICO - Se detectaron violaciones")
        print("  ❌ Los mandatory NO están siendo protegidos correctamente")
    
    print("=" * 80)
    
    return len(violations_found) == 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        # Buscar el archivo de log más reciente
        import glob
        import os
        
        log_files = glob.glob("logs/*.log") + glob.glob("*.log")
        
        if log_files:
            log_file = max(log_files, key=os.path.getmtime)
            print(f"Usando log más reciente: {log_file}\n")
        else:
            print("❌ Error: No se encontró ningún archivo de log")
            print("\nUso: python verify_mandatory_protection.py [archivo_log]")
            sys.exit(1)
    
    success = parse_comprehensive_log(log_file)
    sys.exit(0 if success else 1)
