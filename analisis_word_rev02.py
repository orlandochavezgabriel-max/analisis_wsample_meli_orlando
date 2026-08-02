import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo visual
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.sans-serif': 'Arial', 'font.family': 'sans-serif'})

# 1. Cargar el dataset completo (168 horas de la semana)
archivo_excel = 'Reporte_Consolidado_Planificacion_MELI.xlsx'
df_hora = pd.read_excel(archivo_excel, sheet_name='Detalle_HC_Diaristas_Hora')

# Asegurar orden lógico de los días de la semana
dias_orden = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
df_hora['dia'] = pd.Categorical(df_hora['dia'], categories=dias_orden, ordered=True)
df_hora = df_hora.sort_values(['dia', 'hora']).reset_index(drop=True)

# ------------------------------------------------------------------------------
# 2. MÉTRICAS ESTADÍSTICAS GLOBALES Y POR DÍA
# ------------------------------------------------------------------------------
print("=== 1. RESUMEN ESTADÍSTICO DE DEMANDA TOTAL DE HC POR DÍA ===")
resumen_dias = df_hora.groupby('dia', observed=False)['hc_demanda_total'].agg(
    Media='mean',
    Mediana='median',
    Maximo='max',
    Desv_Estd='std',
    P95=lambda x: np.percentile(x, 95)
).reset_index()
print(resumen_dias.to_string(index=False))

print("\n=== 2. DIARISTAS REQUERIDOS (GAP DE COBERTURA) POR DÍA ===")
resumen_diaristas = df_hora.groupby('dia', observed=False)['diaristas_requeridos_hora'].agg(
    Total_Horas_Diaristas='sum',
    Max_Simultaneo='max',
    Promedio_Hora='mean'
).reset_index()
print(resumen_diaristas.to_string(index=False))


# ==============================================================================
# 3. GENERACIÓN DE GRÁFICOS (VISIÓN SEMANAL + FOCO MIÉRCOLES)
# ==============================================================================

# Create an index for the continuous timeline (168 hours)
df_hora['timeline_idx'] = range(len(df_hora))

# ------------------------------------------------------------------------------
# Figura 1: Curva Semanal Completa de Headcount (Demanda vs. Oferta Fija MELI)
# ------------------------------------------------------------------------------
plt.figure(figsize=(16, 6))
plt.plot(df_hora['timeline_idx'], df_hora['hc_demanda_total'], label='Demanda Total Operativa', color='#1f77b4', linewidth=2)
plt.plot(df_hora['timeline_idx'], df_hora['hc_oferta_meli'], label='Oferta Plantilla Fija MELI', color='#2ca02c', linestyle='--', linewidth=2)
plt.fill_between(df_hora['timeline_idx'], df_hora['hc_oferta_meli'], df_hora['hc_demanda_total'], 
                 where=(df_hora['hc_demanda_total'] > df_hora['hc_oferta_meli']),
                 color='#d62728', alpha=0.4, label='Brecha (Diaristas / Maniobras)')

# Marcar divisiones de días
line_positions = np.arange(0, 168, 24)
for pos in line_positions:
    plt.axvline(x=pos, color='gray', linestyle=':', alpha=0.6)

# Sombrear el Miércoles para destacar el Peak Day
plt.axvspan(48, 72, color='#ffe6e6', alpha=0.5, label='Miércoles (Peak Day)')

plt.xticks(ticks=line_positions + 12, labels=[d.title() for d in dias_orden])
plt.title('Evolución Semanal de Headcount: Demanda Operativa vs. Cobertura Fija MELI', fontsize=14, fontweight='bold')
plt.xlabel('Día de la Semana', fontsize=12)
plt.ylabel('Cantidad de Operarios (HC)', fontsize=12)
plt.legend(loc='upper right')
plt.tight_layout()
plt.savefig('figura1_curva_semanal_hc.png', dpi=300)
plt.close()

# ------------------------------------------------------------------------------
# Figura 2: Mapa de Calor (Heatmap) - Requerimiento de Diaristas por Día y Hora
# ------------------------------------------------------------------------------
pivot_diaristas = df_hora.pivot(index='hora', columns='dia', values='diaristas_requeridos_hora')

plt.figure(figsize=(10, 8))
sns.heatmap(pivot_diaristas, cmap='YlOrRd', annot=True, fmt='.0f', cbar_kws={'label': 'Diaristas Requeridos'})
plt.title('Mapa de Calor: Requerimiento de Diaristas (Horas x Día)', fontsize=13, fontweight='bold')
plt.xlabel('Día de la Semana', fontsize=11)
plt.ylabel('Hora del Día', fontsize=11)
plt.tight_layout()
plt.savefig('figura2_heatmap_diaristas_semanal.png', dpi=300)
plt.close()

# ------------------------------------------------------------------------------
# Figura 3: Foco Específico en el Miércoles (Peak Day) por Subproceso
# ------------------------------------------------------------------------------
df_miercoles = df_hora[df_hora['dia'] == 'miércoles'].copy()

plt.figure(figsize=(12, 5))
plt.plot(df_miercoles['hora'], df_miercoles['hc_descarga'], marker='o', label='Descarga (IN)', color='#2ca02c')
plt.plot(df_miercoles['hora'], df_miercoles['hc_conexion_in'], marker='s', label='Conexión IN', color='#98df8a')
plt.plot(df_miercoles['hora'], df_miercoles['hc_sorting'], marker='^', label='Sorting (Storing)', color='#ff7f0e')
plt.plot(df_miercoles['hora'], df_miercoles['hc_conexion_out'], marker='v', label='Conexión OUT', color='#aec7e8')
plt.plot(df_miercoles['hora'], df_miercoles['hc_despachador'], marker='d', label='Despachador (OUT)', color='#1f77b4')

plt.title('Foco Miércoles (Peak Day): Desglose de HC por Subproceso', fontsize=13, fontweight='bold')
plt.xlabel('Hora del Día', fontsize=11)
plt.ylabel('Headcount Requerido', fontsize=11)
plt.xticks(rotation=45)
plt.legend(title="Subprocesos", bbox_to_anchor=(1.02, 1), loc='upper left')
plt.tight_layout()
plt.savefig('figura3_foco_miercoles_subprocesos.png', dpi=300)
plt.close()

print("\n¡Proceso finalizado! Se han generado las 3 figuras clave para el Word:")
print("1. 'figura1_curva_semanal_hc.png' (Visión Macro 168h)")
print("2. 'figura2_heatmap_diaristas_semanal.png' (Identificación visual de picos)")
print("3. 'figura3_foco_miercoles_subprocesos.png' (Detalle operacional del Peak Day)")