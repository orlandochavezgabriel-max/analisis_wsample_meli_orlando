import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo visual para gráficos del Word
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.sans-serif': 'Arial', 'font.family': 'sans-serif'})

# 1. Cargar el dataset generado en la fase anterior
archivo_excel = 'Reporte_Consolidado_Planificacion_MELI.xlsx'
df_hora = pd.read_excel(archivo_excel, sheet_name='Detalle_HC_Diaristas_Hora')

# Filtrar foco en Miércoles (Peak Day) manteniendo la visión semanal
df_miercoles = df_hora[df_hora['dia'] == 'miércoles'].copy()

print("=== 1. ANÁLISIS DIMENSIONAMIENTO INBOUND (MIÉRCOLES) ===")
inbound_stats = df_miercoles[['hora', 'hc_descarga', 'hc_conexion_in']].describe()
print(df_miercoles[['hora', 'pallets_in', 'hc_descarga', 'hc_conexion_in']].to_string(index=False))

print("\n=== 2. ANÁLISIS DIMENSIONAMIENTO OUTBOUND (MIÉRCOLES) ===")
outbound_stats = df_miercoles[['hora', 'hc_conexion_out', 'hc_despachador']].describe()
print(df_miercoles[['hora', 'pallets_out', 'hc_conexion_out', 'hc_despachador']].to_string(index=False))

print("\n=== 3. ANÁLISIS DIMENSIONAMIENTO SORTING (MIÉRCOLES) ===")
sorting_stats = df_miercoles[['hora', 'vol_storing', 'lineas_reales_small', 'lineas_reales_heavy', 'hc_sorting']].describe()
print(df_miercoles[['hora', 'vol_storing', 'lineas_reales_small', 'lineas_reales_heavy', 'hc_sorting']].to_string(index=False))

print("\n=== 4. ANÁLISIS DE DIARISTAS Y GAPS DE COBERTURA ===")
gap_stats = df_miercoles[['hora', 'hc_demanda_total', 'hc_oferta_meli', 'gap_hc', 'diaristas_requeridos_hora']].describe()
print(df_miercoles[['hora', 'hc_demanda_total', 'hc_oferta_meli', 'gap_hc', 'diaristas_requeridos_hora']].to_string(index=False))


# ==============================================================================
# GENERACIÓN DE GRÁFICOS PARA EL WORD
# ==============================================================================

# ------------------------------------------------------------------------------
# Figura 1: Demanda de HC por Subproceso en Miércoles (Peak Day)
# ------------------------------------------------------------------------------
plt.figure(figsize=(12, 5))
plt.plot(df_miercoles['hora'], df_miercoles['hc_descarga'], marker='o', label='Descarga (Inbound)', color='#2ca02c')
plt.plot(df_miercoles['hora'], df_miercoles['hc_conexion_in'], marker='s', label='Conexión IN', color='#98df8a')
plt.plot(df_miercoles['hora'], df_miercoles['hc_sorting'], marker='^', label='Sorting (Storing)', color='#ff7f0e')
plt.plot(df_miercoles['hora'], df_miercoles['hc_conexion_out'], marker='v', label='Conexión OUT', color='#aec7e8')
plt.plot(df_miercoles['hora'], df_miercoles['hc_despachador'], marker='d', label='Despachador (Outbound)', color='#1f77b4')

plt.title('Requerimiento Teórico de Headcount por Franja Horaria (Miércoles - Peak Day)', fontsize=13, fontweight='bold')
plt.xlabel('Hora del Día', fontsize=11)
plt.ylabel('Headcount Requerido (Personas)', fontsize=11)
plt.xticks(rotation=45)
plt.legend(title="Subprocesos", bbox_to_anchor=(1.02, 1), loc='upper left')
plt.tight_layout()
plt.savefig('figura1_demanda_subprocesos_miercoles.png', dpi=300)
plt.close()

# ------------------------------------------------------------------------------
# Figura 2: Balance entre Oferta Fija MELI y Necesidad de Diaristas
# ------------------------------------------------------------------------------
plt.figure(figsize=(12, 5))
plt.bar(df_miercoles['hora'], df_miercoles['hc_oferta_meli'], label='Oferta Plantilla Fija MELI', color='#2ca02c', alpha=0.85)
plt.bar(df_miercoles['hora'], df_miercoles['diaristas_requeridos_hora'], bottom=df_miercoles['hc_oferta_meli'], label='Diaristas Requeridos (Gap)', color='#d62728', alpha=0.85)
plt.plot(df_miercoles['hora'], df_miercoles['hc_demanda_total'], color='black', linestyle='--', marker='o', label='Demanda Total Operativa')

plt.title('Cobertura de Headcount: Plantilla Fija MELI vs. Requerimiento de Diaristas (Miércoles)', fontsize=13, fontweight='bold')
plt.xlabel('Hora del Día', fontsize=11)
plt.ylabel('Cantidad de Operarios (HC)', fontsize=11)
plt.xticks(rotation=45)
plt.legend(loc='upper right')
plt.tight_layout()
plt.savefig('figura2_oferta_vs_demanda_diaristas.png', dpi=300)
plt.close()

print("\n¡Gráficos e impresiones generados con éxito!")
print("Archivos guardados: 'figura1_demanda_subprocesos_miercoles.png' y 'figura2_oferta_vs_demanda_diaristas.png'")