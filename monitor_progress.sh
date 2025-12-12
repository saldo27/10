#!/bin/bash
# Monitor del progreso del scheduler

echo "🔍 Monitoreando progreso del scheduler..."
echo "Presiona Ctrl+C para detener el monitoreo"
echo ""

while true; do
    clear
    echo "═══════════════════════════════════════════════════════════════"
    echo "⏰ $(date '+%H:%M:%S') - ESTADO DEL SCHEDULER"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # Verificar si el proceso está corriendo
    if ps aux | grep -E "[t]est_scheduler_only.py" > /dev/null; then
        echo "✅ Proceso ACTIVO"
    else
        echo "❌ Proceso DETENIDO o FINALIZADO"
        echo ""
        # Buscar archivo generado
        if ls schedule_complete_*.json 1> /dev/null 2>&1; then
            echo "🎉 Archivo generado:"
            ls -lht schedule_complete_*.json | head -1
        fi
        break
    fi
    
    echo ""
    echo "📋 Últimas líneas importantes del log:"
    echo "───────────────────────────────────────────────────────────────"
    tail -500 logs/scheduler.log | grep -E "(Starting|SUMMARY|violations|empty shifts|Optimization|ATTEMPTS|Best attempt|Selected)" | tail -8
    
    echo ""
    echo "⏱️  Próxima actualización en 30 segundos..."
    sleep 30
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Monitoreo finalizado"
