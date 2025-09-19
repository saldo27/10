#!/usr/bin/env python3
"""
Script de diagnóstico para problemas de acceso a datos históricos
en el WelcomeScreen del scheduler.
"""

import os
import sys
import json

def test_path_access():
    print("🔍 DIAGNÓSTICO DE ACCESO A DATOS HISTÓRICOS")
    print("=" * 60)
    
    # 1. Información del entorno
    print("📍 INFORMACIÓN DEL ENTORNO:")
    print(f"• Directorio de trabajo actual: {os.getcwd()}")
    print(f"• Directorio del script: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"• Ruta de Python: {sys.executable}")
    print("")
    
    # 2. Probar diferentes rutas posibles
    print("🔎 PROBANDO RUTAS POSIBLES:")
    possible_paths = [
        '/workspaces/10/historical_data/consolidated_history.json',
        './historical_data/consolidated_history.json',
        'historical_data/consolidated_history.json',
        os.path.join(os.path.dirname(__file__), 'historical_data', 'consolidated_history.json'),
        os.path.join(os.getcwd(), 'historical_data', 'consolidated_history.json')
    ]
    
    found_path = None
    for i, path in enumerate(possible_paths, 1):
        exists = os.path.exists(path)
        print(f"{i}. {path}")
        print(f"   {'✅ EXISTE' if exists else '❌ NO EXISTE'}")
        if exists and not found_path:
            found_path = path
        print("")
    
    # 3. Listar contenido del directorio actual
    print("📁 CONTENIDO DEL DIRECTORIO ACTUAL:")
    try:
        current_items = os.listdir(os.getcwd())
        directories = [item for item in current_items if os.path.isdir(item)]
        files = [item for item in current_items if os.path.isfile(item)]
        
        print(f"• Directorios: {', '.join(directories[:10])}")
        print(f"• Archivos: {', '.join(files[:10])}")
        
        # Comprobar específicamente si existe historical_data
        if 'historical_data' in directories:
            print("✅ Directorio 'historical_data' ENCONTRADO")
            hist_contents = os.listdir('historical_data')
            print(f"• Contenido de historical_data: {len(hist_contents)} archivos")
            json_files = [f for f in hist_contents if f.endswith('.json')]
            print(f"• Archivos JSON: {len(json_files)}")
            if 'consolidated_history.json' in hist_contents:
                print("✅ consolidated_history.json ENCONTRADO")
            else:
                print("❌ consolidated_history.json NO ENCONTRADO")
        else:
            print("❌ Directorio 'historical_data' NO ENCONTRADO")
    except Exception as e:
        print(f"❌ Error listando directorio: {e}")
    
    print("")
    
    # 4. Si encontramos una ruta válida, probar leer los datos
    if found_path:
        print("📊 PROBANDO LECTURA DE DATOS:")
        print(f"• Usando ruta: {found_path}")
        try:
            with open(found_path, 'r') as f:
                data = json.load(f)
            
            records = data.get('records', [])
            print(f"✅ Datos cargados exitosamente")
            print(f"• Registros encontrados: {len(records)}")
            
            if records:
                latest = records[-1]
                timestamp = latest.get('timestamp', 'N/A')
                coverage = latest.get('coverage_metrics', {}).get('overall_coverage', 'N/A')
                print(f"• Último timestamp: {timestamp}")
                print(f"• Última cobertura: {coverage}")
                
                # Test de la función de estadísticas
                print("")
                print("🧪 SIMULANDO FUNCIÓN DE ESTADÍSTICAS:")
                try:
                    result = simulate_statistics_function(found_path)
                    print("✅ Función de estadísticas ejecutada correctamente")
                    print(f"• Resultado: {len(result)} caracteres generados")
                except Exception as e:
                    print(f"❌ Error en función de estadísticas: {e}")
            
        except Exception as e:
            print(f"❌ Error leyendo datos: {e}")
    else:
        print("❌ NO SE ENCONTRÓ NINGUNA RUTA VÁLIDA")
        print("")
        print("💡 POSIBLES SOLUCIONES:")
        print("1. Ejecutar el script desde el directorio /workspaces/10")
        print("2. Verificar que el directorio historical_data existe")
        print("3. Generar algunos horarios para crear datos históricos")
    
    print("")
    print("=" * 60)

def simulate_statistics_function(path):
    """Simula la función _load_historical_statistics"""
    import json
    
    with open(path, 'r') as f:
        history = json.load(f)
    
    records = history.get('records', [])
    if not records:
        return "No hay registros históricos"
    
    # Analyze historical data
    latest_record = records[-1]
    total_records = len(records)
    
    # Get metrics from latest record
    coverage_metrics = latest_record.get('coverage_metrics', {})
    
    # Calculate averages across all records
    avg_coverage = sum(r.get('coverage_metrics', {}).get('overall_coverage', 0) for r in records) / total_records
    avg_efficiency = sum(r.get('efficiency_score', 0) for r in records) / total_records
    
    # Latest period info
    period = latest_record.get('schedule_period', {})
    
    result = f"""📊 Estadísticas Históricas del Sistema:

📈 Resumen General:
• Total de registros históricos: {total_records}
• Cobertura promedio: {avg_coverage:.1f}%
• Eficiencia promedio: {avg_efficiency:.1f}%
• Último período: {period.get('start_date', 'N/A')[:10]} - {period.get('end_date', 'N/A')[:10]}

🎯 Último Horario Registrado:
• Cobertura general: {coverage_metrics.get('overall_coverage', 0):.1f}%
• Espacios críticos sin cubrir: {len(coverage_metrics.get('critical_gaps', []))}
• Patrones estacionales detectados: ✓
• Análisis de trabajadores disponible: ✓

💡 Métricas Avanzadas:
• Sistema de validación: Activo
• Motor de tiempo real: Disponible
• IA Predictiva: Con {total_records} registros de entrenamiento
• Historial consolidado: Actualizado"""
    
    return result

if __name__ == "__main__":
    test_path_access()