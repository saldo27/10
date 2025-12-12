#!/usr/bin/env python3
"""
Analiza el estado final del Attempt 1 buscando el último estado conocido
de cada trabajador durante el proceso de optimización
"""

import re
from collections import defaultdict
import json

def load_config():
    """Carga configuración"""
    with open('schedule_config_test_real.json', 'r') as f:
        config = json.load(f)
    return config

def extract_final_state_from_log():
    """Extrae el último estado conocido de cada trabajador del log"""
    
    print("📋 Analizando test_120days_v3.log...")
    
    with open('test_120days_v3.log', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar el segmento del Attempt 1
    attempt1_start = content.find('🎯 COMPLETE ATTEMPT 1')
    attempt1_end = content.find('🎯 COMPLETE ATTEMPT 2', attempt1_start)
    if attempt1_end == -1:
        attempt1_end = len(content)
    
    attempt1_section = content[attempt1_start:attempt1_end]
    
    # Extraer todas las menciones de estado de trabajadores
    # Patrón: "Worker X: ... current: Y, target: Z"
    # Buscar en mensajes de HEAVY penalty, BLOCKED, etc que muestran estado actual
    
    patterns = [
        r'Worker (\d+):.*?current[:\s]+(\d+).*?target[:\s]+(\d+)',
        r'Worker (\d+).*?\(current: (\d+), target: (\d+)\)',
        r'(\d+) would exceed.*?\((\d+) >.*?target: (\d+)\)',
    ]
    
    worker_states = {}
    
    for pattern in patterns:
        matches = re.findall(pattern, attempt1_section, re.IGNORECASE)
        for match in matches:
            try:
                worker_id = int(match[0])
                current = int(match[1])
                target = int(match[2])
                
                # Guardar el mayor valor encontrado (más cercano al final)
                if worker_id not in worker_states or current > worker_states[worker_id]['current']:
                    worker_states[worker_id] = {
                        'current': current,
                        'target': target
                    }
            except (ValueError, IndexError):
                continue
    
    print(f"  Encontrados estados para {len(worker_states)} trabajadores")
    
    # Si no encontramos estados razonables, buscar de otra forma
    if not worker_states or all(v['current'] == 0 for v in worker_states.values()):
        print("  ⚠️  Estados iniciales encontrados, buscando en optimización...")
        
        # Buscar en la fase de optimización
        opt_start = attempt1_section.find('Starting optimization')
        if opt_start > 0:
            opt_section = attempt1_section[opt_start:]
            
            # Buscar líneas que muestran estado durante optimización
            for pattern in patterns:
                matches = re.findall(pattern, opt_section, re.IGNORECASE)
                for match in matches:
                    try:
                        worker_id = int(match[0])
                        current = int(match[1])
                        target = int(match[2])
                        
                        if current > 0:  # Solo si tiene asignaciones
                            if worker_id not in worker_states or current > worker_states[worker_id]['current']:
                                worker_states[worker_id] = {
                                    'current': current,
                                    'target': target
                                }
                    except (ValueError, IndexError):
                        continue
    
    return worker_states

def analyze_distribution():
    """Analiza distribución de turnos"""
    
    # Cargar config
    config = load_config()
    workers_config = config['workers_data']
    
    # Crear mapas
    targets = {}
    work_percentages = {}
    for w in workers_config:
        worker_id = int(w['id'])
        targets[worker_id] = w.get('target_shifts', 0)
        work_percentages[worker_id] = w.get('work_percentage', 100)
    
    # Extraer estados del log
    worker_states = extract_final_state_from_log()
    
    if not worker_states:
        print("\n❌ No se pudo extraer información de estados")
        return
    
    # Verificar cobertura de 98.12% = 471 turnos de 480
    total_assigned = sum(s['current'] for s in worker_states.values())
    print(f"\n📊 Total turnos asignados según log: {total_assigned}")
    print(f"   Esperados (98.12% de 480): 471")
    
    if total_assigned < 400:
        print("\n⚠️  ADVERTENCIA: Los datos extraídos parecen incompletos")
        print("   El total es muy bajo comparado con la cobertura reportada de 98.12%")
        print("   Esto puede deberse a que el log se cortó durante la optimización\n")
    
    # Análisis por porcentaje de jornada
    print("\n" + "="*80)
    print("📊 DISTRIBUCIÓN DE TURNOS - ATTEMPT 1")
    print("="*80)
    
    workers_by_percentage = defaultdict(list)
    for worker_id in targets.keys():
        pct = work_percentages.get(worker_id, 100)
        workers_by_percentage[pct].append(worker_id)
    
    violations_8 = []
    violations_10 = []
    violations_15 = []
    violations_extreme = []
    
    for percentage in sorted(workers_by_percentage.keys()):
        worker_ids = workers_by_percentage[percentage]
        print(f"\n  📌 Trabajadores al {percentage}%:")
        print(f"     {'ID':<6} {'Asignados':<12} {'Target':<10} {'Desv.':<10} {'%':<10} {'Estado'}")
        print(f"     {'-'*6} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*20}")
        
        for worker_id in sorted(worker_ids):
            target = targets[worker_id]
            
            if worker_id in worker_states:
                assigned = worker_states[worker_id]['current']
            else:
                assigned = 0
                print(f"     {worker_id:<6} {'N/A':<12} {target:<10} {'N/A':<10} {'N/A':<10} ⚠️  Sin datos")
                continue
            
            deviation = assigned - target
            dev_pct = (deviation / target * 100) if target > 0 else 0
            
            if abs(dev_pct) <= 8:
                status = "✅ Objetivo"
                icon = "✅"
            elif abs(dev_pct) <= 10:
                status = "⚠️  Emergencia"
                icon = "⚠️"
                violations_8.append((worker_id, dev_pct, assigned, target))
            elif abs(dev_pct) <= 15:
                status = "🚨 Crítico"
                icon = "🚨"
                violations_10.append((worker_id, dev_pct, assigned, target))
            else:
                status = "❌ Extremo"
                icon = "❌"
                violations_extreme.append((worker_id, dev_pct, assigned, target))
            
            print(f"     {worker_id:<6} {assigned:<12} {target:<10} {deviation:+4d}      {dev_pct:+6.1f}%   {status}")
    
    # Resumen
    print(f"\n" + "="*80)
    print(f"🎯 RESUMEN DE CUMPLIMIENTO:")
    print(f"="*80)
    
    total_workers = len([w for w in targets.keys() if w in worker_states])
    within_8 = total_workers - len(violations_8) - len(violations_10) - len(violations_extreme)
    
    print(f"\n  ✅ Dentro de tolerancia objetivo (±8%):  {within_8}/{total_workers} trabajadores ({within_8/total_workers*100:.1f}%)")
    
    if violations_8:
        print(f"\n  ⚠️  Tolerancia emergencia (8-10%):       {len(violations_8)} trabajadores")
        for worker_id, dev_pct, assigned, target in violations_8:
            print(f"      Worker {worker_id}: {assigned}/{target} ({dev_pct:+.1f}%)")
    
    if violations_10:
        print(f"\n  🚨 Tolerancia crítica (10-15%):         {len(violations_10)} trabajadores")
        for worker_id, dev_pct, assigned, target in violations_10:
            print(f"      Worker {worker_id}: {assigned}/{target} ({dev_pct:+.1f}%)")
    
    if violations_extreme:
        print(f"\n  ❌ Violación extrema (>15%):            {len(violations_extreme)} trabajadores")
        for worker_id, dev_pct, assigned, target in violations_extreme:
            print(f"      Worker {worker_id}: {assigned}/{target} ({dev_pct:+.1f}%)")
    
    if not violations_10 and not violations_extreme:
        print(f"\n  🏆 TODOS LOS TRABAJADORES DENTRO DEL LÍMITE DE ±10%")
    
    # Estadísticas adicionales
    if worker_states:
        deviations = [abs((worker_states[w]['current'] - targets[w]) / targets[w] * 100) 
                     for w in worker_states.keys() if targets[w] > 0]
        if deviations:
            avg_dev = sum(deviations) / len(deviations)
            max_dev = max(deviations)
            print(f"\n  📈 Desviación promedio: {avg_dev:.1f}%")
            print(f"  📈 Desviación máxima: {max_dev:.1f}%")

def main():
    print("="*80)
    print("ANÁLISIS DE COMPLETE ATTEMPT 1")
    print("="*80)
    
    analyze_distribution()
    
    print("\n" + "="*80)
    print("ℹ️  NOTA SOBRE ANÁLISIS MENSUAL Y DE FINES DE SEMANA:")
    print("="*80)
    print("""
El log test_120days_v3.log no contiene el schedule completo guardado
porque el proceso se cortó por timeout durante el Attempt 2.

Para obtener análisis mensual y de fines de semana necesitamos:
1. Completar la ejecución con timeout mayor (3000s)
2. O exportar el schedule del Attempt 1 desde el código

El análisis actual muestra la distribución global de turnos,
que es el indicador más importante para verificar el balance.
""")
    
    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80)

if __name__ == '__main__':
    main()
