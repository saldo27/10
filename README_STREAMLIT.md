# Sistema de Generación de Horarios - Interfaz Streamlit

## 🚀 Inicio Rápido

### Ejecutar la aplicación

```bash
streamlit run app_streamlit.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

### En GitHub Codespaces

La aplicación detectará automáticamente el puerto y te dará una URL para acceder:
```bash
streamlit run app_streamlit.py --server.port 8501
```

## 📋 Funcionalidades

### 1. **Gestión de Trabajadores** 👥
- ✅ Agregar/editar trabajadores con formulario interactivo
- ✅ Configurar turnos objetivo, porcentaje laboral
- ✅ Definir incompatibilidades entre trabajadores
- ✅ Asignar días obligatorios
- ✅ Importar/exportar desde JSON
- ✅ Vista de lista con todos los trabajadores

### 2. **Generación de Horarios** 📅
- ✅ Seleccionar mes y año
- ✅ Configurar parámetros (tolerancia, turnos por día, días entre turnos)
- ✅ Generación con indicador de progreso
- ✅ Visualización del calendario en tabla interactiva
- ✅ Descarga de calendario en CSV
- ✅ Descarga de PDFs generados

### 3. **Estadísticas** 📊
- ✅ Métricas de cobertura total
- ✅ Tabla de asignaciones por trabajador
- ✅ Comparación objetivo vs asignado (gráfico)
- ✅ Visualización de desviaciones (gráfico)
- ✅ Código de colores según tolerancia

### 4. **Verificación de Restricciones** ⚠️
- ✅ Verificación de incompatibilidades
- ✅ Verificación del patrón 7/14 días
- ✅ Verificación de turnos obligatorios
- ✅ Contador de violaciones
- ✅ Detalles expandibles de cada violación
- ✅ Recomendaciones automáticas

## 🎯 Ventajas sobre Kivy

| Característica | Kivy | Streamlit |
|---------------|------|-----------|
| Funciona sin GUI | ❌ | ✅ |
| Interfaz web moderna | ❌ | ✅ |
| Gráficos interactivos | ⚠️ | ✅ |
| Desarrollo rápido | ⚠️ | ✅ |
| Funciona en Codespaces | ❌ | ✅ |
| Responsive | ⚠️ | ✅ |
| Descarga de archivos | ⚠️ | ✅ |
| Auto-recarga en cambios | ❌ | ✅ |

## 📁 Archivos

- **`app_streamlit.py`**: Aplicación principal Streamlit
- **`trabajadores_ejemplo.json`**: Ejemplo de configuración de trabajadores
- **`main.py`**: Aplicación Kivy original (legacy)

## 🔧 Configuración

### Parámetros Ajustables (Sidebar)

1. **Mes/Año**: Selecciona el período a generar
2. **Tolerancia**: Porcentaje permitido de desviación (5-20%)
3. **Turnos por día**: Número de puestos a cubrir (1-10)
4. **Días mínimos entre turnos**: Gap de descanso (0-7 días)

### Formato JSON de Trabajadores

```json
[
  {
    "id": "TRAB001",
    "target_shifts": 12,
    "work_percentage": 1.0,
    "is_incompatible": false,
    "incompatible_with": ["TRAB002"],
    "mandatory_dates": ["2024-12-01", "2024-12-15"]
  }
]
```

## 🎨 Interfaz

### Tabs Principales

1. **👥 Gestión de Trabajadores**
   - Formulario para agregar/editar
   - Carga/descarga de JSON
   - Lista de trabajadores configurados

2. **📅 Calendario Generado**
   - Métricas de cobertura
   - Tabla del calendario completo
   - Descarga de CSV y PDFs

3. **📊 Estadísticas**
   - Métricas generales
   - Tabla de asignaciones
   - Gráficos comparativos
   - Gráfico de desviaciones

4. **⚠️ Verificación de Restricciones**
   - Resumen de violaciones
   - Detalles por tipo de restricción
   - Recomendaciones

## 🐛 Restricciones Verificadas

- ✅ **Turnos Obligatorios**: Protegidos durante toda la generación
- ✅ **Incompatibilidades**: Trabajadores incompatibles no en mismo día
- ✅ **Patrón 7/14 Días**: Mismo día de semana a 7 o 14 días
- ✅ **Gap entre Turnos**: Días mínimos de descanso
- ✅ **Balance de Fines de Semana**: Distribución proporcional
- ✅ **Tolerancia**: Desviación máxima respecto al objetivo

## 💡 Consejos de Uso

1. **Primer uso**: Carga `trabajadores_ejemplo.json` para probar
2. **Generación**: Puede tomar 2-5 minutos dependiendo de la complejidad
3. **Violaciones**: Si aparecen muchas, ajusta parámetros o trabajadores
4. **PDFs**: Se generan automáticamente durante la generación
5. **Estadísticas**: Usa las gráficas para identificar trabajadores sobrecargados

## 🚀 Próximos Pasos

- [ ] Historial de generaciones
- [ ] Comparación entre meses
- [ ] Edición manual de turnos en calendario
- [ ] Exportación a diferentes formatos (Excel, iCal)
- [ ] Notificaciones por email
- [ ] API REST para integración

## 📝 Notas

- La aplicación guarda el estado en `st.session_state`
- Los cambios en trabajadores requieren regenerar el horario
- Los PDFs se guardan en el directorio actual
- Los logs se guardan en `logs/scheduler.log`
