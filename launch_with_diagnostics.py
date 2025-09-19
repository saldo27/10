#!/usr/bin/env python3
"""
Test de la aplicación Kivy real con diagnóstico integrado
"""

import os
import sys

# Configurar variables de entorno para Kivy
os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ['KIVY_LOG_LEVEL'] = 'info'

# Test básico de acceso a datos antes de lanzar Kivy
def test_data_access_before_kivy():
    print("🔍 PRE-TEST: Verificando acceso a datos antes de iniciar Kivy...")
    
    import json
    
    # Try multiple paths
    possible_paths = [
        '/workspaces/10/historical_data/consolidated_history.json',
        './historical_data/consolidated_history.json',
        'historical_data/consolidated_history.json'
    ]
    
    found_path = None
    for path in possible_paths:
        if os.path.exists(path):
            found_path = path
            break
    
    if found_path:
        try:
            with open(found_path, 'r') as f:
                data = json.load(f)
            records = data.get('records', [])
            print(f"✅ DATOS ACCESIBLES: {len(records)} registros en {found_path}")
            return True
        except Exception as e:
            print(f"❌ ERROR LEYENDO DATOS: {e}")
            return False
    else:
        print(f"❌ NO SE ENCONTRARON DATOS en directorio: {os.getcwd()}")
        return False

# Test de acceso antes de iniciar Kivy
data_accessible = test_data_access_before_kivy()

if data_accessible:
    print("✅ Datos históricos accesibles - Iniciando aplicación Kivy...")
    try:
        # Importar y ejecutar la aplicación
        from main import ShiftManagerApp
        
        print("🚀 Iniciando ShiftManagerApp...")
        app = ShiftManagerApp()
        app.run()
        
    except Exception as e:
        print(f"❌ ERROR EN APLICACIÓN KIVY: {e}")
        print("💡 Ejecuta 'python test_welcome_screen_improvements.py' como alternativa")
else:
    print("❌ Datos históricos no accesibles - No se puede iniciar la aplicación")
    print("💡 Genera algunos horarios primero con la aplicación")