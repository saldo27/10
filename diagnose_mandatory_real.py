#!/usr/bin/env python3
"""
Script de diagnóstico para casos reales.
Monitorea el estado de los mandatory shifts durante la ejecución.
"""

import sys
import re
from datetime import datetime
from collections import defaultdict

def parse_log_file(log_file_path):
    """
    Analiza el archivo de log y extrae información sobre mandatory shifts.
    """
    print("=" * 80)
    print("DIAGNÓSTICO DE MANDATORY SHIFTS - CASO REAL")
    print("=" * 80)
    print(f"\nAnalizando: {log_file_path}\n")
    
    mandatory_assigned = []
    mandatory_locked = []
    mandatory_protected = []
    mandatory_violations = []
    
    locked_count = 0
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Detectar asignaciones de mandatory
                if '🔒 MANDATORY ASSIGNED AND LOCKED' in line:
                    match = re.search(r'🔒 MANDATORY ASSIGNED AND LOCKED: (\w+) → (\d{4}-\d{2}-\d{2})', line)
                    if match:
                        worker = match.group(1)
                        date = match.group(2)
                        mandatory_assigned.append((worker, date, line_num))
                
                # Detectar locked mandatory en summary
                if 'Total locked mandatory:' in line:
                    match = re.search(r'Total locked mandatory: (\d+)', line)
                    if match:
                        locked_count = int(match.group(1))
                
                # Detectar protecciones durante initial fill
                if 'is LOCKED MANDATORY for' in line:
                    match = re.search(r'(\d{4}-\d{2}-\d{2}).*post (\d+).*LOCKED MANDATORY for (\w+)', line)
                    if match:
                        date = match.group(1)
                        post = match.group(2)
                        worker = match.group(3)
                        mandatory_protected.append((worker, date, post, line_num))
                
                # Detectar violaciones críticas
                if 'CRITICAL: Mandatory' in line and 'NOT in locked set' in line:
                    match = re.search(r'Mandatory (\w+) on (\d{4}-\d{2}-\d{2})', line)
                    if match:
                        worker = match.group(1)
                        date = match.group(2)
                        mandatory_violations.append((worker, date, line_num))
    
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {log_file_path}")
        return
    except Exception as e:
        print(f"❌ Error al leer el archivo: {str(e)}")
        return
    
    # Resumen de mandatory asignados
    print("📋 MANDATORY SHIFTS ASIGNADOS Y BLOQUEADOS:")
    print("-" * 80)
    
    if mandatory_assigned:
        worker_mandatory = defaultdict(list)
        for worker, date, line_num in mandatory_assigned:
            worker_mandatory[worker].append((date, line_num))
        
        for worker in sorted(worker_mandatory.keys()):
            dates = worker_mandatory[worker]
            print(f"\n  {worker}: {len(dates)} mandatory shifts")
            for date, line_num in sorted(dates):
                print(f"    ✅ {date} (línea {line_num})")
        
        print(f"\n  Total: {len(mandatory_assigned)} mandatory shifts asignados y bloqueados")
        print(f"  Total en locked set: {locked_count}")
        
        if len(mandatory_assigned) != locked_count:
            print(f"  ⚠️  ADVERTENCIA: Discrepancia detectada!")
    else:
        print("  ⚠️  No se detectaron mandatory shifts en el log")
    
    # Resumen de protecciones
    print("\n" + "=" * 80)
    print("🔒 PROTECCIONES DURANTE INITIAL FILL:")
    print("-" * 80)
    
    if mandatory_protected:
        protection_count = defaultdict(int)
        for worker, date, post, line_num in mandatory_protected:
            protection_count[worker] += 1
        
        print(f"\n  Total de intentos bloqueados: {len(mandatory_protected)}")
        print(f"\n  Por trabajador:")
        for worker in sorted(protection_count.keys()):
            count = protection_count[worker]
            print(f"    {worker}: {count} protecciones")
        
        # Mostrar los primeros 10
        print(f"\n  Primeras 10 protecciones detectadas:")
        for worker, date, post, line_num in mandatory_protected[:10]:
            print(f"    🔒 {worker} en {date} post {post} (línea {line_num})")
        
        if len(mandatory_protected) > 10:
            print(f"    ... y {len(mandatory_protected) - 10} más")
    else:
        print("  ℹ️  No se detectaron intentos de modificar mandatory (correcto si no hubo intentos)")
    
    # Verificar violaciones
    print("\n" + "=" * 80)
    print("🚨 VERIFICACIÓN DE VIOLACIONES:")
    print("-" * 80)
    
    if mandatory_violations:
        print(f"\n  ❌ {len(mandatory_violations)} VIOLACIONES DETECTADAS:")
        for worker, date, line_num in mandatory_violations:
            print(f"    ❌ {worker} en {date} (línea {line_num})")
    else:
        print("  ✅ No se detectaron violaciones de mandatory shifts")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL:")
    print("=" * 80)
    print(f"  Mandatory asignados: {len(mandatory_assigned)}")
    print(f"  Locked count: {locked_count}")
    print(f"  Protecciones aplicadas: {len(mandatory_protected)}")
    print(f"  Violaciones detectadas: {len(mandatory_violations)}")
    
    if len(mandatory_violations) == 0:
        print("\n  ✅ ESTADO: CORRECTO - Todos los mandatory están protegidos")
    else:
        print("\n  ❌ ESTADO: VIOLACIONES DETECTADAS - Revisar logs")
    
    print("=" * 80)

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
            print("\nUso: python diagnose_mandatory_real.py [archivo_log]")
            sys.exit(1)
    
    parse_log_file(log_file)
