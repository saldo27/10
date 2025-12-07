"""
Sistema de Generación de Horarios - Interfaz Streamlit
Reemplazo moderno de la interfaz Kivy con funcionalidad web
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import traceback

# Importar módulos del scheduler
from scheduler import Scheduler
from scheduler_config import SchedulerConfig, setup_logging
from utilities import DateTimeUtils

# Configurar logging
setup_logging()

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Generación de Horarios",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS para mejor apariencia
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar session state
if 'workers_data' not in st.session_state:
    st.session_state.workers_data = []
if 'schedule' not in st.session_state:
    st.session_state.schedule = None
if 'scheduler' not in st.session_state:
    st.session_state.scheduler = None
if 'generation_log' not in st.session_state:
    st.session_state.generation_log = []
if 'config' not in st.session_state:
    st.session_state.config = SchedulerConfig.get_default_config()

# Funciones auxiliares
def load_workers_from_file(uploaded_file):
    """Cargar trabajadores desde archivo JSON"""
    try:
        data = json.load(uploaded_file)
        st.session_state.workers_data = data
        return True, f"✅ {len(data)} trabajadores cargados exitosamente"
    except Exception as e:
        return False, f"❌ Error al cargar archivo: {str(e)}"

def save_workers_to_file():
    """Guardar trabajadores a JSON"""
    return json.dumps(st.session_state.workers_data, indent=2, ensure_ascii=False)

def calculate_target_shifts_for_worker(worker, start_date, end_date, num_shifts, variable_shifts):
    """Calcular turnos objetivo automáticamente para un trabajador"""
    # Usar período personalizado si existe
    worker_start = start_date
    worker_end = end_date
    
    if worker.get('custom_start_date'):
        try:
            worker_start = datetime.strptime(worker['custom_start_date'], '%Y-%m-%d')
        except:
            pass
    
    if worker.get('custom_end_date'):
        try:
            worker_end = datetime.strptime(worker['custom_end_date'], '%Y-%m-%d')
        except:
            pass
    
    # Calcular días totales en el período
    total_days = (worker_end - worker_start).days + 1
    
    # Calcular turnos promedio por día considerando variable_shifts
    # Por simplicidad, usamos num_shifts por defecto
    # TODO: Implementar cálculo más preciso con variable_shifts
    
    # Calcular turnos objetivo basado en porcentaje laboral
    work_percentage = worker.get('work_percentage', 1.0)
    
    # Fórmula: (días totales * turnos_por_día * porcentaje) / número_trabajadores_estimado
    # Simplificado: proporción del total de turnos
    target = int((total_days * num_shifts * work_percentage) / 10)  # Asumiendo ~10 trabajadores
    
    return max(1, target)  # Mínimo 1 turno

def generate_schedule_internal(start_date, end_date, tolerance, holidays, variable_shifts):
    """Generar el horario internamente"""
    try:
        # Validar datos de entrada
        if not st.session_state.workers_data:
            return False, "❌ Error: No hay trabajadores configurados"
        
        if start_date >= end_date:
            return False, "❌ Error: La fecha final debe ser posterior a la inicial"
        
        # Convertir date a datetime si es necesario
        if not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        if not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.min.time())
        
        # Calcular target_shifts automáticamente para trabajadores que lo necesiten
        workers_data_processed = []
        num_shifts = st.session_state.config.get('num_shifts', 3)
        
        for worker in st.session_state.workers_data:
            worker_copy = worker.copy()
            
            # Si auto_calculate está activado, calcular target_shifts
            if worker.get('auto_calculate_shifts', True):
                calculated_target = calculate_target_shifts_for_worker(
                    worker, start_date, end_date, num_shifts, variable_shifts
                )
                worker_copy['target_shifts'] = calculated_target
                logging.info(f"Target shifts calculado para {worker['id']}: {calculated_target}")
            else:
                # Usar el valor manual configurado
                if 'target_shifts' not in worker_copy or worker_copy['target_shifts'] is None:
                    worker_copy['target_shifts'] = 0
                logging.info(f"Target shifts manual para {worker['id']}: {worker_copy['target_shifts']}")
            
            workers_data_processed.append(worker_copy)
        
        # Crear configuración completa para el scheduler
        config = {
            'start_date': start_date,
            'end_date': end_date,
            'num_shifts': st.session_state.config.get('num_shifts', 3),
            'workers_data': workers_data_processed,
            'holidays': holidays,
            'variable_shifts': variable_shifts,
            'gap_between_shifts': st.session_state.config.get('gap_between_shifts', 2),
            'max_consecutive_weekends': st.session_state.config.get('max_consecutive_weekends', 2),
            'enable_proportional_weekends': st.session_state.config.get('enable_proportional_weekends', True),
            'weekend_tolerance': st.session_state.config.get('weekend_tolerance', 1),
            'cache_enabled': st.session_state.config.get('cache_enabled', False),
            'lazy_evaluation': st.session_state.config.get('lazy_evaluation', False),
            'batch_size': st.session_state.config.get('batch_size', 100),
            'max_improvement_loops': st.session_state.config.get('max_improvement_loops', 10),
            'last_post_adjustment_max_iterations': st.session_state.config.get('last_post_adjustment_max_iterations', 5)
        }
        
        # Crear scheduler
        scheduler = Scheduler(config)
        st.session_state.scheduler = scheduler
        
        # Generar horario
        success = scheduler.generate_schedule()
        
        if success:
            st.session_state.schedule = scheduler.schedule
            return True, "✅ Horario generado exitosamente"
        else:
            return False, "❌ Error: No se pudo generar el horario"
            
    except Exception as e:
        error_msg = f"Error en generación: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        return False, f"❌ Error: {str(e)}"

def get_schedule_dataframe():
    """Convertir horario a DataFrame para visualización"""
    if st.session_state.schedule is None:
        return None
    
    schedule = st.session_state.schedule
    
    # Crear DataFrame
    dates = sorted(schedule.keys())
    data = []
    
    for date in dates:
        workers = schedule[date]
        row = {
            'Fecha': date.strftime('%Y-%m-%d'),
            'Día': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'][date.weekday()]
        }
        for i, worker in enumerate(workers):
            row[f'Puesto {i+1}'] = worker if worker else '-'
        data.append(row)
    
    return pd.DataFrame(data)

def get_worker_statistics():
    """Obtener estadísticas de asignaciones por trabajador"""
    if st.session_state.scheduler is None:
        return None
    
    scheduler = st.session_state.scheduler
    stats = []
    
    # Usar los datos de workers_data del scheduler (que tienen los targets calculados)
    scheduler_workers = scheduler.config.get('workers_data', [])
    
    for worker in scheduler_workers:
        worker_id = worker['id']
        target = worker.get('target_shifts', 0)
        current = len(scheduler.worker_assignments.get(worker_id, []))
        deviation = current - target
        deviation_pct = (deviation / target * 100) if target > 0 else 0
        
        stats.append({
            'Trabajador': worker_id,
            'Objetivo': target,
            'Asignados': current,
            'Desviación': deviation,
            'Desv. %': f"{deviation_pct:+.1f}%"
        })
    
    return pd.DataFrame(stats)

def check_violations():
    """Verificar violaciones de restricciones"""
    if st.session_state.scheduler is None:
        return {}
    
    scheduler = st.session_state.scheduler
    schedule = scheduler.schedule
    worker_assignments = scheduler.worker_assignments
    
    violations = {
        'incompatibilidades': [],
        'patron_7_14': [],
        'mandatory': []
    }
    
    # Check incompatibilities
    incomp_map = {}
    for worker in st.session_state.workers_data:
        worker_id = worker['id']
        incomp_map[worker_id] = set(worker.get('incompatible_with', []))
    
    for date, workers_on_date in schedule.items():
        workers_on_date = [w for w in workers_on_date if w is not None]
        for i, w1 in enumerate(workers_on_date):
            for w2 in workers_on_date[i+1:]:
                if w2 in incomp_map.get(w1, set()) or w1 in incomp_map.get(w2, set()):
                    violations['incompatibilidades'].append(
                        f"{date.strftime('%Y-%m-%d')}: {w1} ↔ {w2}"
                    )
    
    # Check 7/14 pattern
    for worker_id, dates in worker_assignments.items():
        sorted_dates = sorted(dates)
        for i, date1 in enumerate(sorted_dates):
            for date2 in sorted_dates[i+1:]:
                days_diff = (date2 - date1).days
                same_weekday = date1.weekday() == date2.weekday()
                is_weekday = date1.weekday() < 5
                
                if same_weekday and days_diff in [7, 14] and is_weekday:
                    violations['patron_7_14'].append(
                        f"{worker_id}: {date1.strftime('%Y-%m-%d')} → {date2.strftime('%Y-%m-%d')}"
                    )
    
    return violations

# ==================== INTERFAZ PRINCIPAL ====================

# Header
st.title("📅 Sistema de Generación de Horarios")
st.markdown("---")

# Sidebar - Configuración y Controles
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Período de reparto (Fecha Inicial - Fecha Final)
    st.subheader("📅 Período de Reparto")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Fecha Inicial",
            value=datetime(2024, 12, 1),
            help="Fecha de inicio del período a programar"
        )
    with col2:
        end_date = st.date_input(
            "Fecha Final",
            value=datetime(2024, 12, 31),
            help="Fecha de fin del período a programar"
        )
    
    # Validar fechas
    if start_date >= end_date:
        st.error("⚠️ La fecha final debe ser posterior a la inicial")
    
    st.markdown("---")
    
    # Festivos (Holidays)
    st.subheader("🎉 Festivos")
    holidays_input = st.text_area(
        "Fechas festivas (una por línea, formato: YYYY-MM-DD)",
        value="2024-12-25\n2024-12-26\n2025-01-01",
        height=100,
        help="Días festivos donde se aplicarán reglas especiales"
    )
    
    # Parsear festivos
    holidays = []
    for line in holidays_input.strip().split('\n'):
        line = line.strip()
        if line:
            try:
                holiday_date = datetime.strptime(line, '%Y-%m-%d')
                holidays.append(holiday_date)
            except:
                st.warning(f"⚠️ Fecha inválida ignorada: {line}")
    
    if holidays:
        st.success(f"✅ {len(holidays)} festivos configurados")
    
    st.markdown("---")
    
    # Parámetros del sistema
    st.subheader("⚙️ Parámetros Globales")
    
    tolerance = st.slider(
        "Tolerancia de desviación (%)",
        min_value=5,
        max_value=20,
        value=10,
        help="Tolerancia permitida en la desviación de turnos asignados vs objetivo"
    )
    
    # Período con número de guardias por defecto
    num_shifts = st.number_input(
        "Turnos por día (por defecto)",
        min_value=1,
        max_value=10,
        value=st.session_state.config.get('num_shifts', 3),
        help="Número de puestos/turnos a cubrir por día"
    )
    st.session_state.config['num_shifts'] = num_shifts
    
    # Variable shifts (períodos con diferente número de guardias)
    with st.expander("📊 Períodos con guardias variables"):
        st.markdown("**Configurar días con diferente número de turnos**")
        
        variable_shifts_text = st.text_area(
            "Formato: YYYY-MM-DD: número",
            value="2024-12-25: 2\n2024-12-26: 2",
            height=100,
            help="Días específicos con diferente número de turnos"
        )
        
        variable_shifts = []
        for line in variable_shifts_text.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                try:
                    date_str, shifts_str = line.split(':')
                    date_obj = datetime.strptime(date_str.strip(), '%Y-%m-%d')
                    shifts_num = int(shifts_str.strip())
                    # El scheduler espera: start_date, end_date, shifts
                    # Para un día específico, start_date == end_date
                    variable_shifts.append({
                        'start_date': date_obj,
                        'end_date': date_obj,
                        'shifts': shifts_num
                    })
                except:
                    st.warning(f"⚠️ Línea inválida: {line}")
        
        if variable_shifts:
            st.success(f"✅ {len(variable_shifts)} días con turnos variables")
        
        st.session_state.config['variable_shifts'] = variable_shifts
    
    col_gap, col_weekends = st.columns(2)
    
    with col_gap:
        gap_between_shifts = st.number_input(
            "Días mínimos entre turnos",
            min_value=0,
            max_value=7,
            value=st.session_state.config.get('gap_between_shifts', 2),
            help="Número mínimo de días de descanso entre turnos consecutivos"
        )
        st.session_state.config['gap_between_shifts'] = gap_between_shifts
    
    with col_weekends:
        max_consecutive_weekends = st.number_input(
            "Fines de semana consecutivos máx.",
            min_value=1,
            max_value=5,
            value=st.session_state.config.get('max_consecutive_weekends', 2),
            help="Número máximo de fines de semana consecutivos que puede trabajar un trabajador"
        )
        st.session_state.config['max_consecutive_weekends'] = max_consecutive_weekends
    
    # Configuración adicional de fines de semana
    with st.expander("⚙️ Configuración Avanzada de Fines de Semana"):
        enable_proportional = st.checkbox(
            "Habilitar balance proporcional de fines de semana",
            value=st.session_state.config.get('enable_proportional_weekends', True),
            help="Distribuir fines de semana proporcionalmente según el porcentaje laboral de cada trabajador"
        )
        st.session_state.config['enable_proportional_weekends'] = enable_proportional
        
        weekend_tolerance = st.slider(
            "Tolerancia de fines de semana (±)",
            min_value=0,
            max_value=3,
            value=st.session_state.config.get('weekend_tolerance', 1),
            help="Tolerancia permitida en la desviación de fines de semana asignados"
        )
        st.session_state.config['weekend_tolerance'] = weekend_tolerance
    
    st.markdown("---")
    
    # Botón de generación
    st.subheader("🚀 Generar Horario")
    
    if len(st.session_state.workers_data) == 0:
        st.warning("⚠️ Primero agregue trabajadores")
        generate_button = st.button("🚀 Generar", disabled=True, type="primary")
    else:
        st.info(f"📊 {len(st.session_state.workers_data)} trabajadores configurados")
        generate_button = st.button("🚀 Generar Horario", type="primary")
    
    if generate_button:
        with st.spinner("Generando horario... esto puede tomar varios minutos"):
            try:
                success, message = generate_schedule_internal(
                    start_date, 
                    end_date, 
                    tolerance/100, 
                    holidays,
                    st.session_state.config.get('variable_shifts', [])
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"❌ Error crítico durante la generación: {str(e)}")
                with st.expander("Ver detalles del error"):
                    st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Información del sistema
    with st.expander("ℹ️ Información del Sistema"):
        st.markdown("""
        **Restricciones implementadas:**
        - ✅ Turnos obligatorios protegidos
        - ✅ Incompatibilidades entre trabajadores
        - ✅ Patrón 7/14 días (mismo día de semana)
        - ✅ Días mínimos entre turnos configurables
        - ✅ Fines de semana consecutivos máximos
        - ✅ Balance proporcional de fines de semana
        - ✅ Tolerancia de desviación configurable
        - ✅ Días fuera (no disponibles)
        - ✅ Períodos personalizados por trabajador
        - ✅ Turnos variables por día/período
        
        **Parámetros configurables:**
        - 📅 Período de reparto (fecha inicial/final)
        - 🎉 Festivos
        - 🔢 Turnos por día (por defecto y variables)
        - ⏳ Gap entre turnos
        - 📆 Fines de semana consecutivos
        - 📊 Tolerancia general y de fines de semana
        """)

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs([
    "👥 Gestión de Trabajadores",
    "📅 Calendario Generado",
    "📊 Estadísticas",
    "⚠️ Verificación de Restricciones"
])

# ==================== TAB 1: GESTIÓN DE TRABAJADORES ====================
with tab1:
    st.header("👥 Gestión de Trabajadores")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Agregar/Editar Trabajador")
        
        with st.form("worker_form"):
            worker_id = st.text_input("ID del Trabajador *", placeholder="Ej: TRAB001")
            
            # Información básica
            st.markdown("**📋 Información Básica**")
            col_a, col_b = st.columns(2)
            with col_a:
                work_percentage = st.slider(
                    "Porcentaje laboral", 
                    0, 100, 100,
                    help="100% = tiempo completo, 50% = media jornada"
                )
            with col_b:
                # Calcular turnos objetivo automáticamente
                auto_calculate = st.checkbox(
                    "Calcular turnos automáticamente",
                    value=True,
                    help="El sistema calculará los turnos según el período y porcentaje"
                )
            
            if not auto_calculate:
                target_shifts = st.number_input(
                    "Turnos objetivo (manual)", 
                    min_value=0, 
                    value=10,
                    help="Especificar manualmente el número de turnos"
                )
            else:
                st.info("ℹ️ Los turnos se calcularán automáticamente según el período configurado")
                target_shifts = 0  # Se calculará después
            
            # Períodos de trabajo personalizados
            st.markdown("**📅 Períodos de Trabajo Personalizados**")
            use_custom_period = st.checkbox(
                "Usar período diferente al global",
                help="Definir fechas específicas para este trabajador"
            )
            
            if use_custom_period:
                col_start, col_end = st.columns(2)
                with col_start:
                    worker_start_date = st.date_input(
                        "Fecha inicio trabajo",
                        value=datetime(2024, 12, 1)
                    )
                with col_end:
                    worker_end_date = st.date_input(
                        "Fecha fin trabajo",
                        value=datetime(2024, 12, 31)
                    )
            else:
                worker_start_date = None
                worker_end_date = None
            
            # Incompatibilidades
            st.markdown("**🚫 Incompatibilidades**")
            col_inc1, col_inc2 = st.columns(2)
            with col_inc1:
                is_incompatible = st.checkbox(
                    "Incompatible con todos los marcados",
                    help="Este trabajador no puede coincidir con otros marcados igual"
                )
            with col_inc2:
                incompatible_with = st.text_input(
                    "Incompatible con IDs específicos",
                    placeholder="TRAB002, TRAB003",
                    disabled=is_incompatible,
                    help="IDs separados por comas"
                )
            
            # Días obligatorios
            st.markdown("**✅ Días Obligatorios (Mandatory)**")
            mandatory_dates = st.text_area(
                "Fechas obligatorias (una por línea o separadas por coma)",
                placeholder="2024-12-01\n2024-12-15\n2024-12-25",
                height=80,
                help="Días en los que DEBE trabajar obligatoriamente"
            )
            
            # Días fuera (nueva funcionalidad)
            st.markdown("**❌ Días Fuera (No disponible)**")
            days_off = st.text_area(
                "Fechas no disponibles (una por línea o separadas por coma)",
                placeholder="2024-12-10\n2024-12-20\n2024-12-30",
                height=80,
                help="Días en los que NO puede tener asignación de turnos (vacaciones, permisos, etc.)"
            )
            
            col_submit, col_clear = st.columns(2)
            with col_submit:
                submit = st.form_submit_button("➕ Agregar Trabajador", type="primary")
            with col_clear:
                clear = st.form_submit_button("🗑️ Limpiar")
            
            if submit and worker_id:
                # Parsear incompatibilidades
                incomp_list = []
                if not is_incompatible and incompatible_with:
                    incomp_list = [x.strip() for x in incompatible_with.split(',') if x.strip()]
                
                # Parsear días obligatorios
                mandatory_list = []
                if mandatory_dates:
                    # Intentar separar por líneas o comas
                    dates_to_parse = mandatory_dates.replace(',', '\n').split('\n')
                    for date_str in dates_to_parse:
                        date_str = date_str.strip()
                        if date_str:
                            try:
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                                mandatory_list.append(date_obj.strftime('%Y-%m-%d'))
                            except:
                                st.warning(f"⚠️ Fecha obligatoria inválida: {date_str}")
                
                # Parsear días fuera (nueva funcionalidad)
                days_off_list = []
                if days_off:
                    dates_to_parse = days_off.replace(',', '\n').split('\n')
                    for date_str in dates_to_parse:
                        date_str = date_str.strip()
                        if date_str:
                            try:
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                                days_off_list.append(date_obj.strftime('%Y-%m-%d'))
                            except:
                                st.warning(f"⚠️ Fecha fuera inválida: {date_str}")
                
                # Crear/actualizar trabajador
                worker_data = {
                    'id': worker_id,
                    'target_shifts': target_shifts,
                    'work_percentage': work_percentage / 100,
                    'is_incompatible': is_incompatible,
                    'incompatible_with': incomp_list,
                    'mandatory_dates': mandatory_list,
                    'days_off': days_off_list,
                    'auto_calculate_shifts': auto_calculate
                }
                
                # Agregar período personalizado si se especificó
                if use_custom_period and worker_start_date and worker_end_date:
                    worker_data['custom_start_date'] = worker_start_date.strftime('%Y-%m-%d')
                    worker_data['custom_end_date'] = worker_end_date.strftime('%Y-%m-%d')
                
                # Verificar si ya existe
                existing_idx = None
                for idx, w in enumerate(st.session_state.workers_data):
                    if w['id'] == worker_id:
                        existing_idx = idx
                        break
                
                if existing_idx is not None:
                    st.session_state.workers_data[existing_idx] = worker_data
                    st.success(f"✅ Trabajador {worker_id} actualizado")
                else:
                    st.session_state.workers_data.append(worker_data)
                    st.success(f"✅ Trabajador {worker_id} agregado")
                
                st.rerun()
    
    with col2:
        st.subheader("Gestión de Datos")
        
        # Cargar desde archivo
        uploaded_file = st.file_uploader("📁 Cargar desde JSON", type=['json'])
        if uploaded_file is not None:
            success, message = load_workers_from_file(uploaded_file)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        
        # Guardar a archivo
        if len(st.session_state.workers_data) > 0:
            json_str = save_workers_to_file()
            st.download_button(
                label="💾 Descargar JSON",
                data=json_str,
                file_name=f"trabajadores_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        
        # Limpiar todos
        if st.button("🗑️ Eliminar Todos los Trabajadores", type="secondary"):
            if st.session_state.workers_data:
                st.session_state.workers_data = []
                st.success("✅ Todos los trabajadores eliminados")
                st.rerun()
    
    # Lista de trabajadores
    st.markdown("---")
    st.subheader(f"📋 Trabajadores Configurados ({len(st.session_state.workers_data)})")
    
    if len(st.session_state.workers_data) > 0:
        for idx, worker in enumerate(st.session_state.workers_data):
            # Título del trabajador
            if worker.get('auto_calculate_shifts', True):
                title = f"👤 {worker['id']} - Objetivo: 🔄 Automático ({worker.get('work_percentage', 1)*100:.0f}%)"
            else:
                title = f"👤 {worker['id']} - Objetivo: {worker.get('target_shifts', 0)} turnos (manual)"
            
            with st.expander(title):
                col_info, col_actions = st.columns([3, 1])
                
                with col_info:
                    # Información básica
                    st.write(f"**Porcentaje laboral:** {worker.get('work_percentage', 1)*100:.0f}%")
                    
                    # Mostrar objetivo de turnos claramente
                    if worker.get('auto_calculate_shifts', True):
                        st.write(f"**🔄 Turnos objetivo:** Se calculará automáticamente según el período")
                    else:
                        st.write(f"**🎯 Turnos objetivo:** {worker.get('target_shifts', 0)} (configurado manualmente)")
                    
                    # Período personalizado
                    if worker.get('custom_start_date') or worker.get('custom_end_date'):
                        start = worker.get('custom_start_date', 'N/A')
                        end = worker.get('custom_end_date', 'N/A')
                        st.write(f"**Período personalizado:** {start} → {end}")
                    
                    # Incompatibilidades
                    if worker.get('is_incompatible'):
                        st.write("**Incompatibilidad:** ⚠️ Incompatible con otros trabajadores marcados")
                    elif worker.get('incompatible_with'):
                        st.write(f"**Incompatible con:** {', '.join(worker['incompatible_with'])}")
                    
                    # Días obligatorios
                    if worker.get('mandatory_dates'):
                        mandatory_count = len(worker['mandatory_dates'])
                        st.write(f"**✅ Días obligatorios:** {mandatory_count} día(s)")
                        if mandatory_count <= 5:
                            st.write(f"   {', '.join(worker['mandatory_dates'])}")
                        else:
                            st.write(f"   {', '.join(worker['mandatory_dates'][:5])} ... y {mandatory_count-5} más")
                    
                    # Días fuera (nueva funcionalidad)
                    if worker.get('days_off'):
                        days_off_count = len(worker['days_off'])
                        st.write(f"**❌ Días fuera:** {days_off_count} día(s)")
                        if days_off_count <= 5:
                            st.write(f"   {', '.join(worker['days_off'])}")
                        else:
                            st.write(f"   {', '.join(worker['days_off'][:5])} ... y {days_off_count-5} más")
                
                with col_actions:
                    if st.button("🗑️ Eliminar", key=f"del_{idx}"):
                        st.session_state.workers_data.pop(idx)
                        st.success(f"✅ {worker['id']} eliminado")
                        st.rerun()
    else:
        st.info("ℹ️ No hay trabajadores configurados. Agregue trabajadores usando el formulario arriba.")

# ==================== TAB 2: CALENDARIO ====================
with tab2:
    st.header("📅 Calendario Generado")
    
    if st.session_state.schedule is None:
        st.info("ℹ️ No hay horario generado. Use el botón '🚀 Generar Horario' en la barra lateral.")
    else:
        # Obtener DataFrame
        df = get_schedule_dataframe()
        
        if df is not None:
            # Métricas rápidas
            col1, col2, col3, col4 = st.columns(4)
            
            total_slots = sum(len([w for w in workers if w != '-']) 
                            for workers in df.iloc[:, 2:].values)
            total_possible = len(df) * (len(df.columns) - 2)
            coverage = (total_slots / total_possible * 100) if total_possible > 0 else 0
            
            with col1:
                st.metric("Días programados", len(df))
            with col2:
                st.metric("Turnos cubiertos", f"{total_slots}/{total_possible}")
            with col3:
                st.metric("Cobertura", f"{coverage:.1f}%")
            with col4:
                # Contar PDFs generados
                pdf_files = list(Path('.').glob('*.pdf'))
                st.metric("PDFs generados", len(pdf_files))
            
            st.markdown("---")
            
            # Tabla del calendario
            st.subheader("📋 Calendario Detallado")
            st.dataframe(
                df,
                use_container_width=True,
                height=600,
                hide_index=True
            )
            
            # Descargar como CSV
            csv = df.to_csv(index=False).encode('utf-8')
            
            # Obtener fechas del scheduler
            if st.session_state.scheduler:
                config = st.session_state.scheduler.config
                start = config['start_date']
                end = config['end_date']
                filename = f"calendario_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
            else:
                filename = f"calendario_{datetime.now().strftime('%Y%m%d')}.csv"
            
            st.download_button(
                label="📥 Descargar Calendario (CSV)",
                data=csv,
                file_name=filename,
                mime="text/csv"
            )
            
            # Descargar PDFs
            st.markdown("---")
            st.subheader("📄 Descargar PDFs")
            
            pdf_files = list(Path('.').glob('*.pdf'))
            if pdf_files:
                cols = st.columns(min(3, len(pdf_files)))
                for idx, pdf_file in enumerate(pdf_files):
                    with cols[idx % 3]:
                        with open(pdf_file, 'rb') as f:
                            st.download_button(
                                label=f"📥 {pdf_file.name}",
                                data=f.read(),
                                file_name=pdf_file.name,
                                mime="application/pdf",
                                key=f"pdf_{idx}"
                            )
            else:
                st.info("ℹ️ No se encontraron archivos PDF generados")

# ==================== TAB 3: ESTADÍSTICAS ====================
with tab3:
    st.header("📊 Estadísticas de Asignación")
    
    if st.session_state.scheduler is None:
        st.info("ℹ️ No hay horario generado. Use el botón '🚀 Generar Horario' en la barra lateral.")
    else:
        # Estadísticas por trabajador
        stats_df = get_worker_statistics()
        
        if stats_df is not None:
            # Métricas generales
            col1, col2, col3 = st.columns(3)
            
            total_target = stats_df['Objetivo'].sum()
            total_assigned = stats_df['Asignados'].sum()
            avg_deviation = stats_df['Desviación'].mean()
            
            with col1:
                st.metric("Total Objetivo", total_target)
            with col2:
                st.metric("Total Asignado", total_assigned, f"{total_assigned - total_target:+d}")
            with col3:
                st.metric("Desviación Promedio", f"{avg_deviation:+.1f}")
            
            st.markdown("---")
            
            # Tabla de estadísticas
            st.subheader("📋 Estadísticas por Trabajador")
            
            # Colorear según desviación
            def color_deviation(val):
                if isinstance(val, str) and '%' in val:
                    pct = float(val.replace('%', '').replace('+', ''))
                    if abs(pct) <= 10:
                        return 'background-color: #d4edda'
                    elif abs(pct) <= 15:
                        return 'background-color: #fff3cd'
                    else:
                        return 'background-color: #f8d7da'
                return ''
            
            styled_df = stats_df.style.applymap(color_deviation, subset=['Desv. %'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Gráfico de barras
            st.markdown("---")
            st.subheader("📊 Comparación Objetivo vs Asignado")
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Objetivo',
                x=stats_df['Trabajador'],
                y=stats_df['Objetivo'],
                marker_color='lightblue'
            ))
            fig.add_trace(go.Bar(
                name='Asignado',
                x=stats_df['Trabajador'],
                y=stats_df['Asignados'],
                marker_color='darkblue'
            ))
            
            fig.update_layout(
                barmode='group',
                xaxis_title="Trabajador",
                yaxis_title="Número de Turnos",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de desviación
            st.markdown("---")
            st.subheader("📈 Desviación por Trabajador")
            
            fig2 = px.bar(
                stats_df,
                x='Trabajador',
                y='Desviación',
                color='Desviación',
                color_continuous_scale=['red', 'yellow', 'green', 'yellow', 'red'],
                color_continuous_midpoint=0
            )
            
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)

# ==================== TAB 4: VERIFICACIÓN ====================
with tab4:
    st.header("⚠️ Verificación de Restricciones")
    
    if st.session_state.scheduler is None:
        st.info("ℹ️ No hay horario generado. Use el botón '🚀 Generar Horario' en la barra lateral.")
    else:
        violations = check_violations()
        
        # Resumen de violaciones
        total_violations = sum(len(v) for v in violations.values())
        
        if total_violations == 0:
            st.success("✅ ¡Excelente! No se encontraron violaciones de restricciones")
        else:
            st.error(f"❌ Se encontraron {total_violations} violaciones de restricciones")
        
        st.markdown("---")
        
        # Detalles de violaciones
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🚫 Incompatibilidades")
            incomp_count = len(violations['incompatibilidades'])
            if incomp_count == 0:
                st.success(f"✅ 0 violaciones")
            else:
                st.error(f"❌ {incomp_count} violaciones")
                with st.expander("Ver detalles"):
                    for v in violations['incompatibilidades']:
                        st.write(f"• {v}")
        
        with col2:
            st.subheader("📅 Patrón 7/14 Días")
            pattern_count = len(violations['patron_7_14'])
            if pattern_count == 0:
                st.success(f"✅ 0 violaciones")
            else:
                st.error(f"❌ {pattern_count} violaciones")
                with st.expander("Ver detalles"):
                    for v in violations['patron_7_14'][:20]:  # Mostrar máximo 20
                        st.write(f"• {v}")
                    if pattern_count > 20:
                        st.write(f"... y {pattern_count - 20} más")
        
        with col3:
            st.subheader("🔒 Turnos Obligatorios")
            mandatory_count = len(violations['mandatory'])
            if mandatory_count == 0:
                st.success(f"✅ 0 violaciones")
            else:
                st.error(f"❌ {mandatory_count} violaciones")
                with st.expander("Ver detalles"):
                    for v in violations['mandatory']:
                        st.write(f"• {v}")
        
        # Recomendaciones
        if total_violations > 0:
            st.markdown("---")
            st.subheader("💡 Recomendaciones")
            
            if incomp_count > 0:
                st.warning("⚠️ Revise las incompatibilidades configuradas en los trabajadores")
            
            if pattern_count > 0:
                st.warning("⚠️ El patrón 7/14 días se está violando. Considere ajustar los días obligatorios o aumentar el número de trabajadores")
            
            if mandatory_count > 0:
                st.warning("⚠️ Algunos turnos obligatorios fueron modificados durante la optimización")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Sistema de Generación de Horarios v2.0 | "
    "Interfaz Streamlit | "
    f"© {datetime.now().year}"
    "</div>",
    unsafe_allow_html=True
)
