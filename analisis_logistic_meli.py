import os
import numpy as np
import pandas as pd 
from scipy.optimize import minimize

# ==============================================================================
# BLOQUE 1: carga de datos y limpieza de datos
# ==============================================================================

#limpieza de datos
def cargar_y_limpiar_datos():
    # 1. Mapeos de estandarización
    mapa_dias = {
        'lunes': 'lunes',
        'martes': 'martes',
        'miercoles': 'miércoles',
        'jueves': 'jueves',
        'viernes': 'viernes',
        'sabado': 'sábado',
        'domingo': 'domingo'
    }

    mapa_subprocesos = {
        'descarga': 'descarga',
        'coniexion_in': 'conexion_in',
        'conexión_out': 'conexion_out',
        'despachador': 'despachador',
        'sport small': 'sort_small',
        'sport heavy': 'sort_heavy'
    }

    # --- A. Cargar y limpiar vol_programado ---
    vol_programado = pd.read_csv('vol_programado.csv')
    vol_programado['dia'] = vol_programado['dia'].str.strip().str.lower().map(lambda x: mapa_dias.get(x, x))

    # --- B. Cargar y limpiar pct_programados ---
    pct_programado = pd.read_csv('pct_programados.csv')
    pct_programado['dia'] = pct_programado['dia'].str.strip().str.lower().map(lambda x: mapa_dias.get(x, x))
    pct_programado['hora'] = pd.to_datetime(pct_programado['hora'].str.strip(), format='%H:%M:%S').dt.strftime('%H:%M')

    # --- C. Cargar y limpiar subproceso ---
    subprocesos = pd.read_csv('subproceso.csv')
    subprocesos['subproceso'] = subprocesos['subproceso'].str.strip().map(lambda x: mapa_subprocesos.get(x, x))
    subprocesos['diaristas'] = subprocesos['diaristas'].str.strip().str.lower()

    # --- D. Cargar y limpiar pct_envio ---
    pct_envio = pd.read_csv('pct_envio.csv')
    pct_envio['tipo_envio'] = pct_envio['tipo_envio'].str.strip().str.lower()

    # --- E. Cargar y limpiar KPIs ---
    kpis = pd.read_csv('KPIs.csv')
    kpis['KPI'] = kpis['KPI'].str.strip().str.lower()
    kpis['unidad'] = kpis['unidad'].str.strip().str.lower()

    # Devolvemos los 5 DataFrames limpios en memoria
    return vol_programado, pct_programado, subprocesos, pct_envio, kpis

# ==============================================================================
# BLOQUE 2 = clasificacion de volumen progrmaado en tipo de envio y palletisado
# ==============================================================================


# creamos una funcion para obtener el volumen de envio para cada fase de acuerdo a tipo y volumen progrmado
def calcular_volumenes_y_pallets_small(df_programacion, df_pct_envio, df_kpis):
    pct_small = df_pct_envio.loc[df_pct_envio['tipo_envio'] == 'small', 'pct_envio'].values[0]
    pct_heavy = df_pct_envio.loc[df_pct_envio['tipo_envio'] == 'heavy', 'pct_envio'].values[0]
    # extrraemos el promedio de envios por pallet de kpis
    spp = df_kpis.loc[df_kpis['KPI'] == 'spp', 'cantidad'].values[0] 

    # Cálculos por subproceso para paquetes tipo Small
    df_programacion['volumen_small_inbound']  = df_programacion['volumen'] * df_programacion['pct_inbound'] * pct_small
    df_programacion['volumen_small_storing']  = df_programacion['volumen'] * df_programacion['pct_storing'] * pct_small
    df_programacion['volumen_small_outbound'] = df_programacion['volumen'] * df_programacion['pct_outbound'] * pct_small
    
    # Cálculos por subproceso para paquetes tipo Heavy
    df_programacion['volumen_heavy_inbound']  = df_programacion['volumen'] * df_programacion['pct_inbound'] * pct_heavy
    df_programacion['volumen_heavy_storing']  = df_programacion['volumen'] * df_programacion['pct_storing'] * pct_heavy
    df_programacion['volumen_heavy_outbound'] = df_programacion['volumen'] * df_programacion['pct_outbound'] * pct_heavy

    # Convertimos el volumen de envíos a número de pallets, consideramos mismo volumen para ambos tipos de envíos (small y heavy) y el promedio de envíos por pallet (spp)
    df_programacion['pallets_small_inbound']  = df_programacion['volumen_small_inbound'] / spp
    df_programacion['pallets_small_storing']  = df_programacion['volumen_small_storing'] / spp
    df_programacion['pallets_small_outbound'] = df_programacion['volumen_small_outbound'] / spp
    df_programacion['pallets_heavy_inbound']  = df_programacion['volumen_heavy_inbound'] / spp
    df_programacion['pallets_heavy_storing']  = df_programacion['volumen_heavy_storing'] / spp
    df_programacion['pallets_heavy_outbound'] = df_programacion['volumen_heavy_outbound'] / spp

    return df_programacion

# cargamos las variables
vol_programado, pct_programado, subprocesos, pct_envio, kpis = cargar_y_limpiar_datos()

# Unir curvas (vol_programado con pct_programado por día)
programacion = pd.merge(pct_programado, vol_programado, on='dia', how='inner')

#imprimimos los volumnes por fase, tipo de envio y pct por hora
programacion = calcular_volumenes_y_pallets_small(programacion, pct_envio, kpis)

# verificamos dias completos
#print(programacion['dia'].unique())

# verificamos datos en las columnas de interes 
columnas_interes = ['dia', 'hora', 
    'volumen_small_inbound', 'pallets_small_inbound',
    'volumen_small_storing', 'pallets_small_storing',
    'volumen_small_outbound', 'pallets_small_outbound']
#print(programacion[programacion['dia'] == 'lunes'][columnas_interes].head(10))


# ==============================================================================
# BLOQUE 3 = seleccion de palletisado y entrada al almacen
# ==============================================================================

#creamos tabla de resumen por dia y hora con los pallets por fase y tipo de envio
columna_resumen_palllets = [
    'dia',
    'hora', 
    'pallets_small_inbound', 
    'pallets_small_storing', 
    'pallets_small_outbound',
    'pallets_heavy_inbound', 
    'pallets_heavy_storing', 
    'pallets_heavy_outbound'
]

#creamos una copia para trabajar los datos de los pallets
programacion_pallets = programacion[columna_resumen_palllets].copy()

#verificacion de los datos de la tabla de resumen
#print(programacion_pallets.head(10))

# obtenemos la sumatoria de los pallets sin tomar en cuenta el tipo de envio 

programacion_pallets['pallets_totales_inbound'] = (
    programacion_pallets['pallets_small_inbound'] + programacion_pallets['pallets_heavy_inbound']
)
programacion_pallets['pallets_totales_storing'] = (
    programacion_pallets['pallets_small_storing'] + programacion_pallets['pallets_heavy_storing']
)

# creamos la diferencia entre los pallets que ingresan y los pallets que se procesan para cada hora
programacion_pallets['diferencia_pallets_hora'] = (
    programacion_pallets['pallets_totales_inbound'] - programacion_pallets['pallets_totales_storing']
)

#mostramos el acumulativo continuto 
programacion_pallets['backlog_acumulado_pallets'] = programacion_pallets['diferencia_pallets_hora'].cumsum()


# creamos alertas sobre el estado del almacen para cada hora, si el backlog acumulado de pallets es mayor a 0, se considera que hay un backlog y se genera una alerta
CAPACIDAD_MAX_PALLETS = 625  # (50,000 envíos / 80 spp)

# 1. Porcentaje de ocupación respecto al tope físico
programacion_pallets['pct_ocupacion'] = (
    programacion_pallets['backlog_acumulado_pallets'] / CAPACIDAD_MAX_PALLETS
) * 100

# 2. Estado del almacén (Semaforización)
condiciones = [
    (programacion_pallets['backlog_acumulado_pallets'] <= CAPACIDAD_MAX_PALLETS * 0.80),
    (programacion_pallets['backlog_acumulado_pallets'] > CAPACIDAD_MAX_PALLETS * 0.80) & 
    (programacion_pallets['backlog_acumulado_pallets'] <= CAPACIDAD_MAX_PALLETS),
    (programacion_pallets['backlog_acumulado_pallets'] > CAPACIDAD_MAX_PALLETS)
]
estados = ['Verde (Normal)', 'Amarillo (Prevención)', 'Rojo (Saturado)']

programacion_pallets['estado_almacen'] = np.select(condiciones, estados, default='Rojo (Saturado)')

# 3. Excedente físico (pallets sin espacio de almacenamiento)
programacion_pallets['pallets_excedentes'] = (
    programacion_pallets['backlog_acumulado_pallets'] - CAPACIDAD_MAX_PALLETS
).clip(lower=0)

#Verificamos los datos de la tabla de resumen con el backlog acumulado
cols_verificacion = [
    'dia', 
    'hora', 
    'pallets_totales_inbound', 
    'pallets_totales_storing', 
    'diferencia_pallets_hora', 
    'backlog_acumulado_pallets', 
    'pct_ocupacion', 
    'estado_almacen', 
    'pallets_excedentes'
]

print(programacion_pallets[cols_verificacion].head(10))

#exportamos la tabla de resumen a un archivo xls

with pd.ExcelWriter('Planificacion_Pallets_backlog_almacen.xlsx', engine='openpyxl') as writer:
    programacion_pallets[cols_verificacion].to_excel(writer, sheet_name='Resumen_Backlog', index=False)
ruta_completa = os.path.abspath('Planificacion_Pallets_backlog_almacen.xlsx')

#ubicacion y nombre del archivo generado
print("Archivo 'Planificacion_Pallets_backlog_almacen.xlsx' generado exitosamente.")
print(f"El archivo se guardó en:\n{ruta_completa}")

# ==============================================================================
# BLOQUE 4: analisis par ala fase stoting. Trabajo con los datos de la fase de almacenaje (storing) para determinar el número de HC necesarios para procesar los pallets en cada hora.
# ==============================================================================

# tomamos los parametros de reglas de noegocio de los KPIs para la fase de storing

# --- FUNCIÓN 1: Cálculo del Requerimiento Teórico ---
def obtener_requerimiento_teorico(df, spp=80):
    """Toma las columnas existentes de pallets por tipo y calcula la demanda de líneas operativas."""
    df_temp = df.copy()

    # Rendimientos por línea expresados en Pallets / Hora
    prod_pallets_small = 1200 / spp  # 15.00 pallets/hr/línea
    prod_pallets_heavy = 390 / spp  #  4.875 pallets/hr/línea

    # 1. Aplicamos la regla directamente sobre las columnas de pallets previamente calculadas
    df_temp['lineas_req_small'] = (
        df_temp['pallets_small_storing'] / prod_pallets_small
    )
    df_temp['lineas_req_heavy'] = (
        df_temp['pallets_heavy_storing'] / prod_pallets_heavy
    )

    # 2. Redondeo entero operativo (capacidad física disponible de líneas)
    df_temp['lineas_op_small'] = np.ceil(df_temp['lineas_req_small'])
    df_temp['lineas_op_heavy'] = np.ceil(df_temp['lineas_req_heavy'])
    df_temp['lineas_teoricas_totales'] = (
        df_temp['lineas_op_small'] + df_temp['lineas_op_heavy']
    )

    return df_temp


# --- FUNCIÓN 2: Aplicación de Topes de Infraestructura y Headcount ---
def aplicar_restriccion_infraestructura(
    df, tope_max_lineas=16, hc_por_linea=25, spp=80
):
    """Acota la apertura de líneas al tope físico de 16 y calcula la salida real y HC."""
    # Trabajamos sobre una copia independiente
    df_temp = df.copy()

    # Productividad en Pallets/Hora por línea
    prod_pallets_small = 1200 / spp  # 15.00 pallets/hr/línea
    prod_pallets_heavy = 390 / spp  #  4.875 pallets/hr/línea

    # Criterio de ajuste por fila cuando se sobrepasa el límite físico
    def acotar_row(row):
        totales = row['lineas_teoricas_totales']
        if totales <= tope_max_lineas:
            return pd.Series([row['lineas_op_small'], row['lineas_op_heavy']])

        # Prorrateo proporcional acotado a 16 líneas físicas
        prop_small = row['lineas_op_small'] / totales
        l_small = np.floor(tope_max_lineas * prop_small)
        l_heavy = tope_max_lineas - l_small
        return pd.Series([l_small, l_heavy])

    # 1. Asignación de líneas reales considerando la restricción física
    df_temp[['lineas_reales_small', 'lineas_reales_heavy']] = df_temp.apply(
        acotar_row, axis=1
    )
    df_temp['lineas_reales_totales'] = (
        df_temp['lineas_reales_small'] + df_temp['lineas_reales_heavy']
    )

    # 2. Capacidad Real Procesada (Pallets y Envíos)
    df_temp['pallets_procesados_storing_real'] = (
        df_temp['lineas_reales_small'] * prod_pallets_small
    ) + (df_temp['lineas_reales_heavy'] * prod_pallets_heavy)

    df_temp['envios_procesados_storing_real'] = (
        df_temp['pallets_procesados_storing_real'] * spp
    )

    # 3. Headcount Real Requerido (Máximo 400 operarios)
    df_temp['hc_storing_real'] = df_temp['lineas_reales_totales'] * hc_por_linea

    # 4. Bandera de Saturación del Sorter
    df_temp['sorter_saturado'] = (
        df_temp['lineas_teoricas_totales'] > tope_max_lineas
    )

    return df_temp

# Creas tu copia de trabajo explícita
df_programacion_storing = programacion.copy()

# Paso 1: Requerimiento Teórico
df_programacion_storing = obtener_requerimiento_teorico(
    df_programacion_storing, spp=80
)

# Paso 2: Aplicación del tope físico (16 líneas) y cálculo de HC real
df_programacion_storing = aplicar_restriccion_infraestructura(
    df_programacion_storing, tope_max_lineas=16, hc_por_linea=25, spp=80
)   

cols_resumen_lineas_storing = [
    'dia', 
    'hora', 
    'pallets_small_storing', 
    'pallets_heavy_storing', 
    'lineas_req_small', 
    'lineas_req_heavy', 
    'lineas_teoricas_totales', 
    'lineas_reales_small', 
    'lineas_reales_heavy', 
    'lineas_reales_totales', 
    'pallets_procesados_storing_real', 
    'envios_procesados_storing_real', 
    'hc_storing_real', 
    'sorter_saturado'
]

df_programacion_storing = df_programacion_storing[cols_resumen_lineas_storing]

# Exportamos los resultados a un archivo Excel
with pd.ExcelWriter('lineas_fase_storing.xlsx', engine='openpyxl') as writer:
    df_programacion_storing.to_excel(writer, sheet_name='Resumen_Storing', index=False)

print("Archivo 'lineas_fase_storing.xlsx' generado exitosamente.")
print(f"El archivo se guardó en:\n{os.path.abspath('lineas_fase_storing.xlsx')}")

# ==============================================================================
# BLOQUE 5: Calculo de HC para cada una des las fases, se toma como minimo requerido la ocupacion de 
# ==============================================================================

# ==============================================================================
# 0. CONFIGURACIÓN MATRIZ REAL DE LOS 13 TURNOS EN MXXEM2
# ==============================================================================
TURNOS_MXXEM2 = [
    {"id": 1,  "tipo": "6x1", "in": 6.0,  "out": 14.0, "dias": ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]},
    {"id": 2,  "tipo": "6x1", "in": 6.0,  "out": 14.0, "dias": ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Domingo"]},
    {"id": 3,  "tipo": "5x2", "in": 6.0,  "out": 15.5, "dias": ["Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]},
    {"id": 4,  "tipo": "5x2", "in": 6.0,  "out": 15.5, "dias": ["Lunes", "Martes", "Miercoles", "Jueves", "Domingo"]},
    {"id": 5,  "tipo": "4x3", "in": 12.0, "out": 23.0, "dias": ["Sabado", "Domingo"]},
    {"id": 6,  "tipo": "5x2", "in": 13.0, "out": 22.0, "dias": ["Lunes", "Martes", "Miercoles", "Jueves", "Domingo"]},
    {"id": 7,  "tipo": "5x2", "in": 14.0, "out": 23.0, "dias": ["Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]},
    {"id": 8,  "tipo": "5x2", "in": 14.0, "out": 23.0, "dias": ["Lunes", "Martes", "Miercoles", "Jueves", "Domingo"]},
    {"id": 9,  "tipo": "4x3", "in": 18.5, "out": 5.0,  "dias": ["Miercoles", "Jueves", "Viernes", "Sabado"]},
    {"id": 10, "tipo": "4x3", "in": 18.5, "out": 5.0,  "dias": ["Domingo", "Lunes", "Martes", "Miercoles"]},
    {"id": 11, "tipo": "4x3", "in": 18.5, "out": 5.0,  "dias": ["Miercoles", "Jueves", "Viernes", "Sabado"]},
    {"id": 12, "tipo": "5x2", "in": 22.0, "out": 6.0,  "dias": ["Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]},
    {"id": 13, "tipo": "5x2", "in": 22.0, "out": 6.0,  "dias": ["Lunes", "Martes", "Miercoles", "Jueves", "Domingo"]}
]

def construir_matriz_cobertura(df_semana):
    n_filas = len(df_semana)
    matriz = np.zeros((n_filas, 13))
    
    for idx, row in df_semana.iterrows():
        dia = row['dia']
        h_num = float(str(row['hora']).split(':')[0])
        
        for t_idx, t in enumerate(TURNOS_MXXEM2):
            if dia in t["dias"]:
                t_in = t["in"]
                t_out = t["out"]
                
                if t_in < t_out:
                    if t_in <= h_num < t_out:
                        matriz[idx, t_idx] = 1
                else:
                    if h_num >= t_in or h_num < t_out:
                        matriz[idx, t_idx] = 1
                        
    return matriz

# ==============================================================================
# MOTOR PRINCIPAL DE PLANIFICACIÓN E INTEGRACIÓN
# ==============================================================================
def procesar_planificacion_hc(vol_df, pct_df):
    resultados_horarios = []
    
    for dia in vol_df['dia'].unique():
        vol_dia = vol_df[vol_df['dia'] == dia]['volumen'].values[0]
        df_dia = pct_df[pct_df['dia'] == dia].copy().reset_index(drop=True)
        
        # 1. FASE INBOUND (Cálculos por minuto)
        df_dia['pallets_in'] = (vol_dia * df_dia['pct_inbound']) / 80
        df_dia['pallets_in_minuto'] = df_dia['pallets_in'] / 60.0
        
        df_dia['hc_descarga'] = np.ceil(df_dia['pallets_in_minuto'] / (20.0 / 60.0))
        df_dia['hc_conexion_in'] = np.ceil(df_dia['pallets_in_minuto'] / (12.0 / 60.0))
        
        # 2. FASE SORTING (Acotación a máximo 16 líneas)
        df_dia['vol_storing'] = vol_dia * df_dia['pct_storing']
        df_dia['lineas_small'] = np.ceil(df_dia['vol_storing'] * 0.89 / 1200)
        df_dia['lineas_heavy'] = np.ceil(df_dia['vol_storing'] * 0.11 / 390)
        df_dia['lineas_teoricas_totales'] = df_dia['lineas_small'] + df_dia['lineas_heavy']
        
        def acotar_row(row):
            totales = row['lineas_teoricas_totales']
            if totales <= 16:
                return pd.Series([row['lineas_small'], row['lineas_heavy']])
            
            prop_small = row['lineas_small'] / totales if totales > 0 else 0
            l_small = np.floor(16 * prop_small)
            l_heavy = 16 - l_small
            return pd.Series([l_small, l_heavy])

        df_dia[['lineas_reales_small', 'lineas_reales_heavy']] = df_dia.apply(acotar_row, axis=1)
        df_dia['lineas_reales_totales'] = df_dia['lineas_reales_small'] + df_dia['lineas_reales_heavy']
        df_dia['hc_sorting'] = df_dia['lineas_reales_totales'] * 25
        df_dia['sorter_saturado'] = df_dia['lineas_teoricas_totales'] > 16

        # 3. FASE OUTBOUND
        df_dia['hc_conexion_out'] = np.ceil(df_dia['pallets_in_minuto'] / (12.0 / 60.0))
        df_dia['pallets_out'] = (vol_dia * df_dia['pct_outbound']) / 80
        df_dia['pallets_out_minuto'] = df_dia['pallets_out'] / 60.0
        
        df_dia['hc_despachador'] = np.ceil(df_dia['pallets_out_minuto'] / (30.0 / 60.0))
        
        # DEMANDA TOTAL REQUERIDA
        df_dia['hc_demanda_total'] = (
            df_dia['hc_descarga'] + 
            df_dia['hc_conexion_in'] + 
            df_dia['hc_sorting'] + 
            df_dia['hc_conexion_out'] + 
            df_dia['hc_despachador']
        )
        
        resultados_horarios.append(df_dia)
        
    df_horario_base = pd.concat(resultados_horarios, ignore_index=True)
    
    # 4. Y 5. OPTIMIZACIÓN BASADA EN PICO MÁXIMO DE CAPACIDAD TÉCNICA (SORTING + ANDENES)
    pico_maximo_semanal = df_horario_base['hc_demanda_total'].max()
    print(f"--> Pico máximo técnico semanal detectado: {int(pico_maximo_semanal)} HC")

    matriz_cob = construir_matriz_cobertura(df_horario_base)
    demanda_total = df_horario_base['hc_demanda_total'].values
    demanda_despacho = df_horario_base['hc_despachador'].values

    def funcion_costo(x_turnos):
        oferta_hora = np.dot(matriz_cob, x_turnos)
        diaristas_hora = np.maximum(0, demanda_total - oferta_hora)
        despacho_falta = np.maximum(0, demanda_despacho - oferta_hora)
        return np.sum(diaristas_hora) + (np.sum(despacho_falta) * 10000)

    res = minimize(
        funcion_costo, 
        x0=[pico_maximo_semanal / 13.0] * 13, 
        method='SLSQP', 
        bounds=[(0, None)] * 13, 
        constraints={'type': 'ineq', 'fun': lambda x: pico_maximo_semanal - np.sum(x)}
    )
    
    hc_optimo_turnos = np.round(res.x).astype(int)
    
    # Aplicar Cobertura MELI Calculada al Detalle Horario
    df_horario_base['hc_oferta_meli'] = np.dot(matriz_cob, hc_optimo_turnos)
    df_horario_base['gap_hc'] = df_horario_base['hc_demanda_total'] - df_horario_base['hc_oferta_meli']
    df_horario_base['diaristas_requeridos_hora'] = df_horario_base['gap_hc'].apply(lambda x: max(0, x))
    
    df_horario_base['alerta_despacho'] = np.where(
        df_horario_base['hc_oferta_meli'] < df_horario_base['hc_despachador'],
        '¡CRÍTICO! MELI no cubre Despacho',
        'OK'
    )
    
    df_distribucion_turnos = pd.DataFrame({
        'ID_Turno': [t['id'] for t in TURNOS_MXXEM2],
        'Esquema': [t['tipo'] for t in TURNOS_MXXEM2],
        'Horario': [f"{int(t['in'])}:00 - {int(t['out'])}:00" if t['in'] % 1 == 0 else f"{int(t['in'])}:30 - {int(t['out'])}:00" for t in TURNOS_MXXEM2],
        'Dias_Laborables': [", ".join(t['dias']) for t in TURNOS_MXXEM2],
        'HC_Sugerido_MELI': hc_optimo_turnos
    })

    return df_horario_base, df_distribucion_turnos


# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    vol_programado = pd.read_csv('vol_programado.csv')
    pct_programado = pd.read_csv('pct_programados.csv')
    
    df_detalle_hora, df_resumen_turnos = procesar_planificacion_hc(
        vol_programado, 
        pct_programado
    )
    
    with pd.ExcelWriter('Reporte_Analisis_HC_Diaristas.xlsx', engine='openpyxl') as writer:
        df_resumen_turnos.to_excel(writer, sheet_name='Distribucion_13_Turnos_MELI', index=False)
        df_detalle_hora.to_excel(writer, sheet_name='Detalle_Horario_HC', index=False)
        
    print("¡Reporte generado exitosamente en 'Reporte_Analisis_HC_Diaristas.xlsx'!")