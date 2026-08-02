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
DIA_SOBREVENTA = 'miércoles'
PCT_SOBREVENTA = 0.14  

# SUPUESTOS FINANCIEROS Y OPERATIVOS
COSTO_UNITARIO_HC_HORA = 1.0          
FACTOR_COSTO_SOBREVENTA = 2.5         

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


def duplicar_escenarios_volumen(vol_base_df, dia_sobreventa=DIA_SOBREVENTA, pct_sobreventa=PCT_SOBREVENTA):
    vol_base = vol_base_df.copy()
    vol_base['volumen'] = vol_base['volumen'].astype(float)
    vol_base['escenario'] = 'Programado_Base'

    vol_sobre = vol_base_df.copy()
    vol_sobre['volumen'] = vol_sobre['volumen'].astype(float)
    if dia_sobreventa and dia_sobreventa in vol_sobre['dia'].values:
        vol_sobre.loc[vol_sobre['dia'] == dia_sobreventa, 'volumen'] *= (1 + pct_sobreventa)
    vol_sobre['escenario'] = 'Con_Sobreventa'

    return vol_base, vol_sobre


# ==============================================================================
# BLOQUE 2: CLASIFICACIÓN DE VOLUMEN Y PALLETIZADO
# ==============================================================================
def calcular_volumenes_y_pallets(df_programacion, df_pct_envio, df_kpis):
    pct_small = df_pct_envio.loc[df_pct_envio['tipo_envio'] == 'small', 'pct_envio'].values[0]
    pct_heavy = df_pct_envio.loc[df_pct_envio['tipo_envio'] == 'heavy', 'pct_envio'].values[0]
    spp = df_kpis.loc[df_kpis['KPI'] == 'spp', 'cantidad'].values[0] if 'spp' in df_kpis['KPI'].values else SPP_DEFAULT

    for fase in ['inbound', 'storing', 'outbound']:
        df_programacion[f'volumen_small_{fase}'] = df_programacion['volumen'] * df_programacion[f'pct_{fase}'] * pct_small
        df_programacion[f'volumen_heavy_{fase}'] = df_programacion['volumen'] * df_programacion[f'pct_{fase}'] * pct_heavy
        
        df_programacion[f'pallets_small_{fase}'] = df_programacion[f'volumen_small_{fase}'] / spp
        df_programacion[f'pallets_heavy_{fase}'] = df_programacion[f'volumen_heavy_{fase}'] / spp
        df_programacion[f'pallets_totales_{fase}'] = df_programacion[f'pallets_small_{fase}'] + df_programacion[f'pallets_heavy_{fase}']

    return df_programacion


# ==============================================================================
# BLOQUE 3: ANÁLISIS DE OCUPACIÓN Y BACKLOG EN ALMACÉN
# ==============================================================================
def analizar_backlog_almacen(df_programacion):
    df_pallets = df_programacion.copy()

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
    df_pallets['pallets_excedentes'] = (df_pallets['backlog_acumulado_pallets'] - CAPACIDAD_MAX_PALLETS).clip(0)

    cols_resumen = [
        'escenario', 'dia', 'hora', 'pallets_totales_inbound', 'pallets_totales_storing', 
        'diferencia_pallets_hora', 'backlog_acumulado_pallets', 
        'pct_ocupacion', 'estado_almacen', 'pallets_excedentes'
    ]
    return df_pallets[cols_resumen]


# ==============================================================================
# BLOQUE 4: COBERTURA, BALANCEO Y VALUACIÓN FINANCIERA POR SUBPROCESO
# ==============================================================================
def construir_matriz_cobertura(df_semana):
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
                else:  
                    if h_num >= t_in or h_num < t_out:
                        matriz[idx, t_idx] = 1
    return matriz


def procesar_escenario_operativo(vol_df, pct_df, pct_envio, kpis, nombre_escenario):
    prog_full = pd.merge(pct_df, vol_df, on='dia', how='inner')
    prog_full = calcular_volumenes_y_pallets(prog_full, pct_envio, kpis)
    
    resultados_horarios = []
    for dia in vol_df['dia'].unique():
        df_dia = prog_full[prog_full['dia'] == dia].copy().reset_index(drop=True)
        df_dia['escenario'] = nombre_escenario
        
        # HC Demanda basado en tasas de productividad estándar exactas
        df_dia['hc_descarga'] = np.ceil(df_dia['pallets_totales_inbound'] / 20.0)      # 3 min/pallet -> 20 p/h
        df_dia['hc_conexion_in'] = np.ceil(df_dia['pallets_totales_inbound'] / 12.0)   # 5 min/pallet -> 12 p/h
        
        # Sorting HC (Sort General: 1200 shipments; Sort Large: 390 shipments)
        df_dia['lineas_small'] = np.ceil(df_dia['volumen_small_storing'] / 1200)
        df_dia['lineas_heavy'] = np.ceil(df_dia['volumen_heavy_storing'] / 390)
        df_dia['lineas_teoricas_totales'] = df_dia['lineas_small'] + df_dia['lineas_heavy']
        
        prop_small = np.where(df_dia['lineas_teoricas_totales'] > 0, df_dia['lineas_small'] / df_dia['lineas_teoricas_totales'], 0)
        excede = df_dia['lineas_teoricas_totales'] > MAX_LINEAS_SORTER
        
        df_dia['lineas_reales_small'] = np.where(excede, np.floor(MAX_LINEAS_SORTER * prop_small), df_dia['lineas_small'])
        df_dia['lineas_reales_heavy'] = np.where(excede, MAX_LINEAS_SORTER - df_dia['lineas_reales_small'], df_dia['lineas_heavy'])
        df_dia['hc_sorting'] = (df_dia['lineas_reales_small'] + df_dia['lineas_reales_heavy']) * HC_POR_LINEA_SORTER

        # Outbound HC
        df_dia['hc_conexion_out'] = np.ceil(df_dia['pallets_totales_outbound'] / 12.0)  # 5 min/pallet -> 12 p/h
        df_dia['hc_despachador'] = np.ceil(df_dia['pallets_totales_outbound'] / 30.0)   # 2 min/pallet -> 30 p/h
        
        resultados_horarios.append(df_dia)
        
    df_horario = pd.concat(resultados_horarios, ignore_index=True)
    matriz_cob = construir_matriz_cobertura(df_horario)
    
    return prog_full, df_horario, matriz_cob


# ==============================================================================
# BLOQUE 5: EXTRACCIÓN MODULAR Y COMPARATIVA AISLADA POR SUBPROCESO (CALIBRADO AL 100%)
# ==============================================================================
def extraer_datos_fase_comparativa(df_detalle_master, matriz_cob, col_demanda_fase, col_pallets_fase, nombre_fase, admite_diaristas, nombre_escenario):
    turnos_activos_hora = np.sum(matriz_cob, axis=1)
    turnos_activos_hora_safe = np.where(turnos_activos_hora == 0, 1, turnos_activos_hora)
    
    # 1. Demanda específica de la subfase entre turnos activos
    demanda_alicuota = df_detalle_master[col_demanda_fase].values / turnos_activos_hora_safe
    
    # 2. CALIBRACIÓN AL 100%: Uso de Percentil 75 en lugar de Mediana para ajustar la Oferta Fija a la demanda real
    hc_turnos_fase = []
    for t_idx in range(matriz_cob.shape[1]):
        horas_activas = matriz_cob[:, t_idx] == 1
        if np.sum(horas_activas) > 0:
            valores_activos = demanda_alicuota[horas_activas]
            # Percentil 75 para asegurar cobertura cercana al 100% de la demanda recurrente
            hc_sugerido = int(np.ceil(np.percentile(valores_activos, 75)))
        else:
            hc_sugerido = 0
        hc_turnos_fase.append(hc_sugerido)
        
    hc_turnos_fase = np.array(hc_turnos_fase)
    oferta_fase = np.dot(matriz_cob, hc_turnos_fase) # Oferta fija calibrada por subfase
    
    demanda_hc = df_detalle_master[col_demanda_fase].values
    
    if admite_diaristas:
        gap_fase = (demanda_hc - oferta_fase).clip(0)
    else:
        gap_fase = np.zeros_like(demanda_hc)
    
    pallets_totales = df_detalle_master[col_pallets_fase].values
    
    if nombre_fase in ['Descarga', 'Inbound']:
        pallets_por_hc_hora = 20.0
    elif nombre_fase in ['Conexion_IN', 'Conexion_OUT']:
        pallets_por_hc_hora = 12.0
    elif nombre_fase == 'Despachadores':
        pallets_por_hc_hora = 30.0
    else:  
        pallets_por_hc_hora = 48.0  
        
    capacidad_pallets_fijos = oferta_fase * pallets_por_hc_hora
    pallets_atendidos_fijos = np.minimum(pallets_totales, capacidad_pallets_fijos)
    pallets_atendidos_diaristas = pallets_totales - pallets_atendidos_fijos if admite_diaristas else np.zeros_like(pallets_totales)

    costo_oferta_fase = oferta_fase * COSTO_UNITARIO_HC_HORA
    costo_diaristas_fase = gap_fase * COSTO_UNITARIO_HC_HORA
    gasto_total_fase = costo_oferta_fase + costo_diaristas_fase
    gasto_sobreventa_fase = demanda_hc * COSTO_UNITARIO_HC_HORA * FACTOR_COSTO_SOBREVENTA
    
    df_detalle_fase = pd.DataFrame({
        'Escenario': nombre_escenario,
        'Día': df_detalle_master['dia'],
        'Hora': df_detalle_master['hora'],
        'Volumen Total (paq/h)': df_detalle_master['volumen'],
        f'Pallets Totales ({nombre_fase})': pallets_totales.round(2),
        f'Pallets Atendidos (Turno Fijo)': pallets_atendidos_fijos.round(2),
        f'Pallets Atendidos (Diaristas / Gap)': pallets_atendidos_diaristas.round(2),
        f'HC Demanda ({nombre_fase})': demanda_hc,
        'Turnos Activos': turnos_activos_hora,
        f'Alicuota Promedio ({nombre_fase})': demanda_alicuota.round(2),
        'HC Oferta Fija MELI': oferta_fase,
        f'HC Diaristas Requeridos': gap_fase,
        f'Costo Base Oferta Fija': costo_oferta_fase,
        f'Costo Base Diaristas': costo_diaristas_fase,
        f'Gasto Total Base (Factor 1.0)': gasto_total_fase,
        f'Gasto Impacto Sobreventa (Factor 2.5)': gasto_sobreventa_fase
    })
    
    df_resumen_fase = pd.DataFrame({
        'Escenario': nombre_escenario,
        'ID_Turno': [t['id'] for t in TURNOS_MXXEM2],
        'Esquema': [t['tipo'] for t in TURNOS_MXXEM2],
        'Horario': [f"{int(t['in'])}:00 - {int(t['out'])}:00" if t['in'] % 1 == 0 else f"{int(t['in'])}:30 - {int(t['out'])}:00" for t in TURNOS_MXXEM2],
        'Dias_Laborables': [", ".join(t['dias']).title() for t in TURNOS_MXXEM2],
        f'HC Fijo Sugerido ({nombre_fase})': hc_turnos_fase
    })
    
    return df_detalle_fase, df_resumen_fase

# ==============================================================================
# EJECUCIÓN PRINCIPAL Y CONSOLIDACIÓN EN EXCEL
# ==============================================================================
if __name__ == "__main__":
    print("=== INICIANDO COMPARATIVA: EVALUACIÓN SIMULTÁNEA E INDEPENDIENTE POR SUBFASE ===")
    
    vol_prog_base, pct_prog, subprocesos, pct_envio, kpis = cargar_y_limpiar_datos()
    vol_base_df, vol_sobre_df = duplicar_escenarios_volumen(vol_prog_base, DIA_SOBREVENTA, PCT_SOBREVENTA)
    
    prog_base_full, df_detalle_base, matriz_cob_base = procesar_escenario_operativo(
        vol_base_df, pct_prog, pct_envio, kpis, 'Programado_Base'
    )
    prog_sobre_full, df_detalle_sobre, matriz_cob_sobre = procesar_escenario_operativo(
        vol_sobre_df, pct_prog, pct_envio, kpis, 'Con_Sobreventa'
    )
    
    df_backlog_base = analizar_backlog_almacen(prog_base_full)
    df_backlog_sobre = analizar_backlog_almacen(prog_sobre_full)
    df_backlog_general = pd.concat([df_backlog_base, df_backlog_sobre], ignore_index=True)
    
    fases_config = {
        'Descarga': (lambda df: df['hc_descarga'], 'pallets_totales_inbound', True),
        'Conexion_IN': (lambda df: df['hc_conexion_in'], 'pallets_totales_inbound', True),
        'Sorting': (lambda df: df['hc_sorting'], 'pallets_totales_storing', True),
        'Conexion_OUT': (lambda df: df['hc_conexion_out'], 'pallets_totales_outbound', True),
        'Despachadores': (lambda df: df['hc_despachador'], 'pallets_totales_outbound', False)
    }
    
    hojas_fases_data = {}
    df_resumen_turnos_lista = []
    
    for escenario_nombre, df_det, matriz_c in [('Base', df_detalle_base, matriz_cob_base), ('Sobreventa', df_detalle_sobre, matriz_cob_sobre)]:
        for nombre_fase, (func_demanda, col_pallets, admite_diaristas) in fases_config.items():
            df_subfase_work = df_det.copy()
            df_subfase_work['_dem_subfase'] = func_demanda(df_subfase_work)
            
            det_f, res_f = extraer_datos_fase_comparativa(
                df_subfase_work, matriz_c, '_dem_subfase', col_pallets, nombre_fase, admite_diaristas, f'Escenario_{escenario_nombre}'
            )
            
            # Agregamos explícitamente la columna de la subfase actual para claridad absoluta en el reporte general
            res_f['Subproceso'] = nombre_fase
            
            hojas_fases_data[f'{escenario_nombre}_{nombre_fase}'] = det_f
            hojas_fases_data[f'Turnos_{escenario_nombre}_{nombre_fase}'] = res_f
            df_resumen_turnos_lista.append(res_f)

    df_resumen_turnos_general = pd.concat(df_resumen_turnos_lista, ignore_index=True)
    
    # Reordenamos las columnas del reporte general de turnos para que la visibilidad sea óptima
    cols_orden_turnos = ['Escenario', 'Subproceso', 'ID_Turno', 'Esquema', 'Horario', 'Dias_Laborables'] + [c for c in df_resumen_turnos_general.columns if c not in ['Escenario', 'Subproceso', 'ID_Turno', 'Esquema', 'Horario', 'Dias_Laborables']]
    df_resumen_turnos_general = df_resumen_turnos_general[cols_orden_turnos]

    archivo_salida = 'comparativa_programado_vs_sobrevente.xlsx'
    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
        df_resumen_turnos_general.to_excel(writer, sheet_name='Distribucion_Turnos_General', index=False)
        df_backlog_general.to_excel(writer, sheet_name='Resumen_Backlog_Almacen', index=False)
        
        for nombre_hoja, df_hoja in hojas_fases_data.items():
            df_hoja.to_excel(writer, sheet_name=nombre_hoja, index=False)
        
    print(f"\n¡Proceso completado con éxito!")
    print(f"La hoja 'Distribucion_Turnos_General' ahora incluye la columna 'Subproceso' y el personal exacto por turno.")
    print(f"Archivo guardado en: {os.path.abspath(archivo_salida)}")
# ==============================================================================
# BLOQUE 6: CONSOLIDACIÓN MAESTRA CON OFERTA FIJA, DEMANDA Y BRECHAS POR HORA
# ==============================================================================
print("\n=== GENERANDO ARCHIVO ADICIONAL: datasets_analisis.xlsx (Con Oferta Fija y Brechas) ===")

macrofases_config = {
    'Inbound': ['Descarga', 'Conexion_IN'],
    'Outbound': ['Conexion_OUT', 'Despachadores'],
    'Sorting_Storing': ['Sorting']
}

datasets_analisis_dict = {}

for macrofase, subfases in macrofases_config.items():
    key_base_primera = f'Base_{subfases[0]}'
    key_sobre_primera = f'Sobreventa_{subfases[0]}'
    
    if key_base_primera not in hojas_fases_data or key_sobre_primera not in hojas_fases_data:
        continue
        
    df_base_ref = hojas_fases_data[key_base_primera]
    df_sobre_ref = hojas_fases_data[key_sobre_primera]
    
    df_analisis = pd.DataFrame({
        'ID_Hora': df_base_ref['Día'].astype(str) + '_' + df_base_ref['Hora'].astype(str),
        'Escenario_Comparacion': 'Base_vs_Sobreventa',
        'Día': df_base_ref['Día'],
        'Hora': df_base_ref['Hora'],
        'Volumen Paquetes (Base)': df_base_ref['Volumen Total (paq/h)'],
        'Volumen Paquetes (Sobreventa)': df_sobre_ref['Volumen Total (paq/h)']
    })
    
    pallets_base_macro = 0
    pallets_sobre_macro = 0
    hc_dem_base_macro = 0
    hc_dem_sobre_macro = 0
    hc_fijo_base_macro = 0
    hc_fijo_sobre_macro = 0
    
    for sf in subfases:
        df_b_sf = hojas_fases_data[f'Base_{sf}']
        df_s_sf = hojas_fases_data[f'Sobreventa_{sf}']
        
        col_p_sf = f'Pallets Totales ({sf})' if f'Pallets Totales ({sf})' in df_b_sf.columns else 'Pallets Totales (Inbound)'
        
        # Pallets
        df_analisis[f'Pallets Base ({sf})'] = df_b_sf[col_p_sf]
        df_analisis[f'Pallets Sobreventa ({sf})'] = df_s_sf[col_p_sf]
        
        # HC Demanda
        df_analisis[f'HC Demanda Base ({sf})'] = df_b_sf[f'HC Demanda ({sf})']
        df_analisis[f'HC Demanda Sobreventa ({sf})'] = df_s_sf[f'HC Demanda ({sf})']
        
        # HC Oferta Fija MELI (Plantilla Fija disponible por hora)
        hc_fija_b = df_b_sf['HC Oferta Fija MELI'] if 'HC Oferta Fija MELI' in df_b_sf.columns else 0
        hc_fija_s = df_s_sf['HC Oferta Fija MELI'] if 'HC Oferta Fija MELI' in df_s_sf.columns else 0
        
        df_analisis[f'HC Oferta Fija Base ({sf})'] = df_b_sf['HC Oferta Fija MELI']
        df_analisis[f'HC Oferta Fija Sobreventa ({sf})'] = df_b_sf['HC Oferta Fija MELI']  # <- Fijo igual a la base
        
        # HC Diaristas (Brecha / Personal Temporal requerido)
        df_analisis[f'HC Diaristas Base ({sf})'] = df_b_sf['HC Diaristas Requeridos'] if 'HC Diaristas Requeridos' in df_b_sf.columns else 0
        df_analisis[f'HC Diaristas Sobreventa ({sf})'] = df_s_sf['HC Diaristas Requeridos'] if 'HC Diaristas Requeridos' in df_s_sf.columns else 0
        
        # Acumulados para Macro
        pallets_base_macro += df_b_sf[col_p_sf]
        pallets_sobre_macro += df_s_sf[col_p_sf]
        hc_dem_base_macro += df_b_sf[f'HC Demanda ({sf})']
        hc_dem_sobre_macro += df_s_sf[f'HC Demanda ({sf})']
        hc_fijo_base_macro += hc_fija_b
        hc_fijo_sobre_macro += hc_fija_s

    # Productividad Efectiva Ponderada Macro
    df_analisis['Prod Ponderada Macro (Base)'] = np.where(
        hc_dem_base_macro > 0, (pallets_base_macro / hc_dem_base_macro).round(2), 0
    )
    df_analisis['Prod Ponderada Macro (Sobreventa)'] = np.where(
        hc_dem_sobre_macro > 0, (pallets_sobre_macro / hc_dem_sobre_macro).round(2), 0
    )
    
    datasets_analisis_dict[f'Impacto_{macrofase}'] = df_analisis

# Exportación
archivo_analisis_salida = 'datasets_analisis.xlsx'
with pd.ExcelWriter(archivo_analisis_salida, engine='openpyxl') as writer_analisis:
    for nombre_hoja, df_data in datasets_analisis_dict.items():
        df_data.to_excel(writer_analisis, sheet_name=nombre_hoja, index=False)

print(f"¡Dataset actualizado con HC Oferta Fija MELI y Diaristas por hora con éxito!")