import os
import numpy as np
import pandas as pd 

# ==============================================================================
# 0. CONSTANTES GLOBALES Y CONFIGURACIÓN DE TURNOS
# ==============================================================================
CAPACIDAD_MAX_PALLETS = 625      # (50,000 envíos / 80 spp)
MAX_LINEAS_SORTER = 16          # Máximo de líneas físicas
HC_POR_LINEA_SORTER = 25        # Operarios por línea
SPP_DEFAULT = 80                # Shipments per pallet por defecto

# PARÁMETROS DE SOBREVENTA DINÁMICA
# Puedes cambiar el día ('miércoles', 'jueves', etc.) y el porcentaje (0.14 = 14%)
DIA_SOBREVENTA = 'miércoles'
PCT_SOBREVENTA = 0.14  

TURNOS_MXXEM2 = [
    {"id": 1,  "tipo": "6x1", "in": 6.0,  "out": 14.0, "dias": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]},
    {"id": 2,  "tipo": "6x1", "in": 6.0,  "out": 14.0, "dias": ["lunes", "martes", "miércoles", "jueves", "viernes", "domingo"]},
    {"id": 3,  "tipo": "5x2", "in": 6.0,  "out": 15.5, "dias": ["martes", "miércoles", "jueves", "viernes", "sábado"]},
    {"id": 4,  "tipo": "5x2", "in": 6.0,  "out": 15.5, "dias": ["lunes", "martes", "miércoles", "jueves", "domingo"]},
    {"id": 5,  "tipo": "4x3", "in": 12.0, "out": 23.0, "dias": ["sábado", "domingo"]},
    {"id": 6,  "tipo": "5x2", "in": 13.0, "out": 22.0, "dias": ["lunes", "martes", "miércoles", "jueves", "domingo"]},
    {"id": 7,  "tipo": "5x2", "in": 14.0, "out": 23.0, "dias": ["martes", "miércoles", "jueves", "viernes", "sábado"]},
    {"id": 8,  "tipo": "5x2", "in": 14.0, "out": 23.0, "dias": ["lunes", "martes", "miércoles", "jueves", "domingo"]},
    {"id": 9,  "tipo": "4x3", "in": 18.5, "out": 5.0,  "dias": ["miércoles", "jueves", "viernes", "sábado"]},
    {"id": 10, "tipo": "4x3", "in": 18.5, "out": 5.0,  "dias": ["domingo", "lunes", "martes", "miércoles"]},
    {"id": 11, "tipo": "4x3", "in": 18.5, "out": 5.0,  "dias": ["miércoles", "jueves", "viernes", "sábado"]},
    {"id": 12, "tipo": "5x2", "in": 22.0, "out": 6.0,  "dias": ["martes", "miércoles", "jueves", "viernes", "sábado"]},
    {"id": 13, "tipo": "5x2", "in": 22.0, "out": 6.0,  "dias": ["lunes", "martes", "miércoles", "jueves", "domingo"]}
]


# ==============================================================================
# BLOQUE 1: CARGA Y LIMPIEZA DE DATOS
# ==============================================================================
def cargar_y_limpiar_datos():
    """Carga los CSVs locales, estandariza cadenas de texto y formatos de fecha/hora."""
    mapa_dias = {
        'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miércoles',
        'jueves': 'jueves', 'viernes': 'viernes', 'sabado': 'sábado', 'domingo': 'domingo'
    }

    mapa_subprocesos = {
        'descarga': 'descarga', 'coniexion_in': 'conexion_in',
        'conexión_out': 'conexion_out', 'despachador': 'despachador',
        'sport small': 'sort_small', 'sport heavy': 'sort_heavy'
    }

    vol_programado = pd.read_csv('vol_programado.csv')
    vol_programado['dia'] = vol_programado['dia'].str.strip().str.lower().map(lambda x: mapa_dias.get(x, x))

    pct_programado = pd.read_csv('pct_programados.csv')
    pct_programado['dia'] = pct_programado['dia'].str.strip().str.lower().map(lambda x: mapa_dias.get(x, x))
    pct_programado['hora'] = pd.to_datetime(pct_programado['hora'].str.strip(), format='%H:%M:%S').dt.strftime('%H:%M')

    subprocesos = pd.read_csv('subproceso.csv')
    subprocesos['subproceso'] = subprocesos['subproceso'].str.strip().map(lambda x: mapa_subprocesos.get(x, x))
    subprocesos['diaristas'] = subprocesos['diaristas'].str.strip().str.lower()

    pct_envio = pd.read_csv('pct_envio.csv')
    pct_envio['tipo_envio'] = pct_envio['tipo_envio'].str.strip().str.lower()

    kpis = pd.read_csv('KPIs.csv')
    kpis['KPI'] = kpis['KPI'].str.strip().str.lower()
    kpis['unidad'] = kpis['unidad'].str.strip().str.lower()

    return vol_programado, pct_programado, subprocesos, pct_envio, kpis

# aplicamos sobre venta en caso de que se reporte 

def aplicar_sobreventa(vol_df, dia_sobreventa=DIA_SOBREVENTA, pct_sobreventa=PCT_SOBREVENTA):
    """Aplica la sobreventa al volumen base antes de realizar cualquier cálculo operativo."""
    vol_mod = vol_df.copy()
    vol_mod['volumen'] = vol_mod['volumen'].astype(float)
    
    if dia_sobreventa and dia_sobreventa in vol_mod['dia'].values:
        vol_mod.loc[vol_mod['dia'] == dia_sobreventa, 'volumen'] *= (1 + pct_sobreventa)
        print(f"--> Sobreventa de {pct_sobreventa*100}% aplicada al día: {dia_sobreventa.title()}")
        
    return vol_mod

# ==============================================================================
# BLOQUE 2: CLASIFICACIÓN DE VOLUMEN Y PALLETIZADO
# ==============================================================================
def calcular_volumenes_y_pallets(df_programacion, df_pct_envio, df_kpis):
    """Calcula volúmenes y conversión a pallets por tipo de paquete (Small / Heavy)."""
    pct_small = df_pct_envio.loc[df_pct_envio['tipo_envio'] == 'small', 'pct_envio'].values[0]
    pct_heavy = df_pct_envio.loc[df_pct_envio['tipo_envio'] == 'heavy', 'pct_envio'].values[0]
    spp = df_kpis.loc[df_kpis['KPI'] == 'spp', 'cantidad'].values[0] if 'spp' in df_kpis['KPI'].values else SPP_DEFAULT

    for fase in ['inbound', 'storing', 'outbound']:
        df_programacion[f'volumen_small_{fase}'] = df_programacion['volumen'] * df_programacion[f'pct_{fase}'] * pct_small
        df_programacion[f'volumen_heavy_{fase}'] = df_programacion['volumen'] * df_programacion[f'pct_{fase}'] * pct_heavy
        
        df_programacion[f'pallets_small_{fase}'] = df_programacion[f'volumen_small_{fase}'] / spp
        df_programacion[f'pallets_heavy_{fase}'] = df_programacion[f'volumen_heavy_{fase}'] / spp

    return df_programacion


# ==============================================================================
# BLOQUE 3: ANÁLISIS DE OCUPACIÓN Y BACKLOG EN ALMACÉN
# ==============================================================================
def analizar_backlog_almacen(df_programacion):
    """Evalúa la saturación física del almacén hora a hora."""
    df_pallets = df_programacion.copy()

    df_pallets['pallets_totales_inbound'] = df_pallets['pallets_small_inbound'] + df_pallets['pallets_heavy_inbound']
    df_pallets['pallets_totales_storing'] = df_pallets['pallets_small_storing'] + df_pallets['pallets_heavy_storing']

    df_pallets['diferencia_pallets_hora'] = df_pallets['pallets_totales_inbound'] - df_pallets['pallets_totales_storing']
    df_pallets['backlog_acumulado_pallets'] = df_pallets['diferencia_pallets_hora'].cumsum()

    df_pallets['pct_ocupacion'] = (df_pallets['backlog_acumulado_pallets'] / CAPACIDAD_MAX_PALLETS) * 100

    condiciones = [
        (df_pallets['backlog_acumulado_pallets'] <= CAPACIDAD_MAX_PALLETS * 0.80),
        (df_pallets['backlog_acumulado_pallets'] > CAPACIDAD_MAX_PALLETS * 0.80) & (df_pallets['backlog_acumulado_pallets'] <= CAPACIDAD_MAX_PALLETS),
        (df_pallets['backlog_acumulado_pallets'] > CAPACIDAD_MAX_PALLETS)
    ]
    estados = ['Verde (Normal)', 'Amarillo (Prevención)', 'Rojo (Saturado)']
    df_pallets['estado_almacen'] = np.select(condiciones, estados, default='Rojo (Saturado)')
    df_pallets['pallets_excedentes'] = (df_pallets['backlog_acumulado_pallets'] - CAPACIDAD_MAX_PALLETS).clip(lower=0)

    cols_resumen = [
        'dia', 'hora', 'pallets_totales_inbound', 'pallets_totales_storing', 
        'diferencia_pallets_hora', 'backlog_acumulado_pallets', 
        'pct_ocupacion', 'estado_almacen', 'pallets_excedentes'
    ]
    return df_pallets[cols_resumen]


# ==============================================================================
# BLOQUE 4: CAPACIDAD Y RESTRICCIONES FÍSICAS EN FASE STORING
# ==============================================================================
def calcular_restricciones_storing(df, spp=SPP_DEFAULT):
    """Calcula requerimiento teórico y acota las líneas operativas a la capacidad del Sorter."""
    df_temp = df.copy()

    prod_pallets_small = 1200 / spp  
    prod_pallets_heavy = 390 / spp   

    df_temp['lineas_req_small'] = df_temp['pallets_small_storing'] / prod_pallets_small
    df_temp['lineas_req_heavy'] = df_temp['pallets_heavy_storing'] / prod_pallets_heavy
    df_temp['lineas_op_small'] = np.ceil(df_temp['lineas_req_small'])
    df_temp['lineas_op_heavy'] = np.ceil(df_temp['lineas_req_heavy'])
    df_temp['lineas_teoricas_totales'] = df_temp['lineas_op_small'] + df_temp['lineas_op_heavy']

    excede_limite = df_temp['lineas_teoricas_totales'] > MAX_LINEAS_SORTER
    prop_small = np.where(df_temp['lineas_teoricas_totales'] > 0, df_temp['lineas_op_small'] / df_temp['lineas_teoricas_totales'], 0)
    
    df_temp['lineas_reales_small'] = np.where(
        excede_limite, 
        np.floor(MAX_LINEAS_SORTER * prop_small), 
        df_temp['lineas_op_small']
    )
    df_temp['lineas_reales_heavy'] = np.where(
        excede_limite, 
        MAX_LINEAS_SORTER - df_temp['lineas_reales_small'], 
        df_temp['lineas_op_heavy']
    )
    
    df_temp['lineas_reales_totales'] = df_temp['lineas_reales_small'] + df_temp['lineas_reales_heavy']
    df_temp['pallets_procesados_storing_real'] = (df_temp['lineas_reales_small'] * prod_pallets_small) + (df_temp['lineas_reales_heavy'] * prod_pallets_heavy)
    df_temp['envios_procesados_storing_real'] = df_temp['pallets_procesados_storing_real'] * spp
    df_temp['hc_storing_real'] = df_temp['lineas_reales_totales'] * HC_POR_LINEA_SORTER
    df_temp['sorter_saturado'] = excede_limite

    cols_resumen = [
        'dia', 'hora', 'pallets_small_storing', 'pallets_heavy_storing', 
        'lineas_req_small', 'lineas_req_heavy', 'lineas_teoricas_totales', 
        'lineas_reales_small', 'lineas_reales_heavy', 'lineas_reales_totales', 
        'pallets_procesados_storing_real', 'envios_procesados_storing_real', 
        'hc_storing_real', 'sorter_saturado'
    ]
    return df_temp[cols_resumen]


# ==============================================================================
# BLOQUE 5: COBERTURA Y BALANCEO DE PLANTILLA (MEDIANA + ALÍCUOTAS POR EMPALME)
# ==============================================================================
def construir_matriz_cobertura(df_semana):
    """Construye la matriz binaria de presencia por hora para los 13 turnos."""
    n_filas = len(df_semana)
    matriz = np.zeros((n_filas, len(TURNOS_MXXEM2)))
    
    for idx, row in df_semana.iterrows():
        dia = row['dia']
        h_num = float(str(row['hora']).split(':')[0])
        
        for t_idx, t in enumerate(TURNOS_MXXEM2):
            if dia in t["dias"]:
                t_in, t_out = t["in"], t["out"]
                if t_in < t_out:
                    if t_in <= h_num < t_out:
                        matriz[idx, t_idx] = 1
                else:  # Cruza medianoche
                    if h_num >= t_in or h_num < t_out:
                        matriz[idx, t_idx] = 1
    return matriz


def calcular_oferta_meli_por_mediana(df_horario, matriz_cob):
    """
    Calcula el HC sugerido por turno considerando el EMPALME de turnos.
    Divide la demanda horaria entre el número de turnos concurrentes en cada hora
    antes de obtener la mediana del turno.
    """
    # 1. Contar cuántos turnos coinciden activos en cada hora
    turnos_activos_por_hora = np.sum(matriz_cob, axis=1)
    
    # Evitar división entre cero en horas sin turnos programados
    turnos_activos_por_hora = np.where(turnos_activos_por_hora == 0, 1, turnos_activos_por_hora)
    
    # 2. Asignar a cada hora la demanda que le corresponde a CADA turno activo
    demanda_alicuota_por_hora = df_horario['hc_demanda_total'].values / turnos_activos_por_hora
    
    hc_turnos = []
    for t_idx in range(matriz_cob.shape[1]):
        horas_activas = matriz_cob[:, t_idx] == 1
        if np.sum(horas_activas) > 0:
            # Mediana de la alícuota de demanda que le toca a este turno específico
            demanda_mediana_turno = np.median(demanda_alicuota_por_hora[horas_activas])
            hc_sugerido = int(np.ceil(demanda_mediana_turno))
        else:
            hc_sugerido = 0
            
        hc_turnos.append(hc_sugerido)
        
    return np.array(hc_turnos)


def procesar_escenario_operativo(vol_mod, pct_df):
    """Calcula demanda horaria y equilibra plantilla fija MELI usando el volumen ya transformado."""
    resultados_horarios = []
    for dia in vol_mod['dia'].unique():
        vol_dia = vol_mod[vol_mod['dia'] == dia]['volumen'].values[0]
        df_dia = pct_df[pct_df['dia'] == dia].copy().reset_index(drop=True)
        
        # 1. Inbound
        df_dia['pallets_in'] = (vol_dia * df_dia['pct_inbound']) / SPP_DEFAULT
        df_dia['pallets_in_minuto'] = df_dia['pallets_in'] / 60.0
        df_dia['hc_descarga'] = np.ceil(df_dia['pallets_in_minuto'] / (20.0 / 60.0))
        df_dia['hc_conexion_in'] = np.ceil(df_dia['pallets_in_minuto'] / (12.0 / 60.0))
        
        # 2. Sorting
        df_dia['vol_storing'] = vol_dia * df_dia['pct_storing']
        df_dia['lineas_small'] = np.ceil(df_dia['vol_storing'] * 0.89 / 1200)
        df_dia['lineas_heavy'] = np.ceil(df_dia['vol_storing'] * 0.11 / 390)
        df_dia['lineas_teoricas_totales'] = df_dia['lineas_small'] + df_dia['lineas_heavy']
        
        prop_small = np.where(df_dia['lineas_teoricas_totales'] > 0, df_dia['lineas_small'] / df_dia['lineas_teoricas_totales'], 0)
        excede = df_dia['lineas_teoricas_totales'] > MAX_LINEAS_SORTER
        
        df_dia['lineas_reales_small'] = np.where(excede, np.floor(MAX_LINEAS_SORTER * prop_small), df_dia['lineas_small'])
        df_dia['lineas_reales_heavy'] = np.where(excede, MAX_LINEAS_SORTER - df_dia['lineas_reales_small'], df_dia['lineas_heavy'])
        df_dia['hc_sorting'] = (df_dia['lineas_reales_small'] + df_dia['lineas_reales_heavy']) * HC_POR_LINEA_SORTER

        # 3. Outbound
        df_dia['hc_conexion_out'] = np.ceil(df_dia['pallets_in_minuto'] / (12.0 / 60.0))
        df_dia['pallets_out'] = (vol_dia * df_dia['pct_outbound']) / SPP_DEFAULT
        df_dia['pallets_out_minuto'] = df_dia['pallets_out'] / 60.0
        df_dia['hc_despachador'] = np.ceil(df_dia['pallets_out_minuto'] / (30.0 / 60.0))
        
        # Demanda Total Horaria
        df_dia['hc_demanda_total'] = (
            df_dia['hc_descarga'] + df_dia['hc_conexion_in'] + 
            df_dia['hc_sorting'] + df_dia['hc_conexion_out'] + 
            df_dia['hc_despachador']
        )
        resultados_horarios.append(df_dia)
        
    df_horario = pd.concat(resultados_horarios, ignore_index=True)
    matriz_cob = construir_matriz_cobertura(df_horario)
    
    # 4. Asignación de Plantilla Fija mediante MEDIANA
    hc_turnos_meli = calcular_oferta_meli_por_mediana(df_horario, matriz_cob)
    
    # Métricas finales de cobertura y brecha (diaristas)
    df_horario['hc_oferta_meli'] = np.dot(matriz_cob, hc_turnos_meli)
    df_horario['gap_hc'] = df_horario['hc_demanda_total'] - df_horario['hc_oferta_meli']
    df_horario['diaristas_requeridos_hora'] = df_horario['gap_hc'].clip(lower=0)
    
    df_resumen_turnos = pd.DataFrame({
        'ID_Turno': [t['id'] for t in TURNOS_MXXEM2],
        'Esquema': [t['tipo'] for t in TURNOS_MXXEM2],
        'Horario': [f"{int(t['in'])}:00 - {int(t['out'])}:00" if t['in'] % 1 == 0 else f"{int(t['in'])}:30 - {int(t['out'])}:00" for t in TURNOS_MXXEM2],
        'Dias_Laborables': [", ".join(t['dias']).title() for t in TURNOS_MXXEM2],
        'HC_Meli_Fijo_Sugerido': hc_turnos_meli
    })

    return df_horario, df_resumen_turnos


# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    print("=== INICIANDO MODELO DE PLANIFICACIÓN LOGÍSTICA MELI ===")
    
    # 1. Cargar datos base
    vol_prog_base, pct_prog, subprocesos, pct_envio, kpis = cargar_y_limpiar_datos()
    
    # 2. Aplicar sobreventa UNA SOLA VEZ AL INICIO
    vol_prog = aplicar_sobreventa(vol_prog_base, DIA_SOBREVENTA, PCT_SOBREVENTA)
    
    # 3. Unir y clasificar volúmenes (ya con la sobreventa integrada)
    programacion = pd.merge(pct_prog, vol_prog, on='dia', how='inner')
    programacion = calcular_volumenes_y_pallets(programacion, pct_envio, kpis)
    
    # 4. Procesar análisis operativos alineados
    df_backlog = analizar_backlog_almacen(programacion)
    df_storing = calcular_restricciones_storing(programacion)
    df_detalle_hora, df_resumen_turnos = procesar_escenario_operativo(vol_prog, pct_prog)
    
    # 5. Exportar reporte consolidado en Excel
    archivo_salida = 'Reporte_Consolidado_Planificacion_MELI.xlsx'
    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
        df_resumen_turnos.to_excel(writer, sheet_name='Distribucion_Turnos_MELI', index=False)
        df_detalle_hora.to_excel(writer, sheet_name='Detalle_HC_Diaristas_Hora', index=False)
        df_storing.to_excel(writer, sheet_name='Capacidad_Storing_Sorter', index=False)
        df_backlog.to_excel(writer, sheet_name='Resumen_Backlog_Almacen', index=False)
        
    print(f"\n¡Proceso completado exitosamente!")
    print(f"Reporte consolidado generado en: {os.path.abspath(archivo_salida)}")