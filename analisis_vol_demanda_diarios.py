import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.sans-serif': 'Arial', 'font.family': 'sans-serif'})

# 1. Cargar el dataset
archivo_excel = 'Reporte_Consolidado_Planificacion_MELI.xlsx'
df_hora = pd.read_excel(archivo_excel, sheet_name='Detalle_HC_Diaristas_Hora')

dias_orden = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
df_hora['dia'] = pd.Categorical(df_hora['dia'], categories=dias_orden, ordered=True)
df_hora = df_hora.sort_values(['dia', 'hora']).reset_index(drop=True)

SPP_DEFAULT = 80

# 2. Asegurar/Calcular Pallets Storing en base a 'vol_storing' (si no viene como pallets)
if 'pallets_storing' not in df_hora.columns and 'vol_storing' in df_hora.columns:
    df_hora['pallets_storing'] = df_hora['vol_storing'] / SPP_DEFAULT

# ------------------------------------------------------------------------------
# 3. ANÁLISIS ESTADÍSTICO DE MOVIENTOS DE PALLETS POR DÍA DE LA SEMANA
# ------------------------------------------------------------------------------
print("=== 1. RESUMEN ACUMULADO DE PALLETS POR DÍA (SEMANAL) ===")
resumen_pallets = df_hora.groupby('dia', observed=False)[['pallets_in', 'pallets_storing', 'pallets_out']].sum().round(1)
resumen_pallets['Total_Movimientos_Pallets'] = resumen_pallets.sum(axis=1)
print(resumen_pallets.to_string())

print("\n=== 2. ESTADÍSTICAS DEL FLUJO HORARIO DE PALLETS - MIÉRCOLES (PEAK DAY) ===")
df_miercoles = df_hora[df_hora['dia'] == 'miércoles'].copy()
stats_miercoles = df_miercoles[['pallets_in', 'pallets_storing', 'pallets_out']].describe().round(2)
print(stats_miercoles.to_string())


# ==============================================================================
# 4. GENERACIÓN DE GRÁFICOS DE DEMANDA POR PALLETS
# ==============================================================================

# ------------------------------------------------------------------------------
# Figura 4: Comportamiento Horario del Mover de Pallets el Miércoles (Peak Day)
# ------------------------------------------------------------------------------
plt.figure(figsize=(13, 6))
plt.plot(df_miercoles['hora'], df_miercoles['pallets_in'], marker='o', color='#2ca02c', linewidth=2.5, label='Pallets IN (Inbound)')
plt.plot(df_miercoles['hora'], df_miercoles['pallets_storing'], marker='^', color='#ff7f0e', linewidth=2.5, label='Pallets STORING (Sorter Eq.)')
plt.plot(df_miercoles['hora'], df_miercoles['pallets_out'], marker='s', color='#1f77b4', linewidth=2.5, label='Pallets OUT (Outbound)')

plt.title('Demanda Operativa Horaria por Flujo de Pallets - Miércoles (Peak Day)', fontsize=14, fontweight='bold')
plt.xlabel('Hora del Día', fontsize=12)
plt.ylabel('Cantidad de Pallets / Hora', fontsize=12)
plt.xticks(rotation=45)
plt.legend(title="Fase del Proceso", loc='upper right')
plt.tight_layout()
plt.savefig('figura4_flujo_pallets_miercoles.png', dpi=300)
plt.close()

# ------------------------------------------------------------------------------
# Figura 5: Pallets Totales Procesados por Día (Inbound vs Storing vs Outbound)
# ------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5))
resumen_pallets[['pallets_in', 'pallets_storing', 'pallets_out']].plot(
    kind='bar', stacked=False, ax=ax, color=['#2ca02c', '#ff7f0e', '#1f77b4'], alpha=0.85, width=0.8
)

plt.title('Comparativo Semanal de Carga Total de Pallets por Fase', fontsize=13, fontweight='bold')
plt.xlabel('Día de la Semana', fontsize=11)
plt.ylabel('Volumen Total de Pallets', fontsize=11)
plt.xticks(rotation=0)
plt.legend(['Inbound (Entradas)', 'Storing (Procesamiento)', 'Outbound (Salidas)'], title="Fase")
plt.tight_layout()
plt.savefig('figura5_pallets_acumulado_semanal.png', dpi=300)
plt.close()

print("\n¡Proceso completado con éxito!")
print("Archivos generados: 'figura4_flujo_pallets_miercoles.png' y 'figura5_pallets_acumulado_semanal.png'")