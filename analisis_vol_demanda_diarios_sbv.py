import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración visual
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.sans-serif': 'Arial', 'font.family': 'sans-serif'})

FACTOR_SOBREVENTA = 1.14  # 14% de sobreventa el miércoles

# 1. Cargar dataset consolidado
archivo_excel = 'Reporte_Consolidado_Planificacion_MELI.xlsx'
df_hora = pd.read_excel(archivo_excel, sheet_name='Detalle_HC_Diaristas_Hora')

dias_orden = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
df_hora['dia'] = pd.Categorical(df_hora['dia'], categories=dias_orden, ordered=True)
df_hora = df_hora.sort_values(['dia', 'hora']).reset_index(drop=True)

# 2. Reconstruir valores BASE (Sin sobreventa)
# Solo el miércoles tiene el incremento del 14%, los demás días se mantienen idénticos
df_hora['pallets_in_base'] = np.where(df_hora['dia'] == 'miércoles', df_hora['pallets_in'] / FACTOR_SOBREVENTA, df_hora['pallets_in'])
df_hora['pallets_out_base'] = np.where(df_hora['dia'] == 'miércoles', df_hora['pallets_out'] / FACTOR_SOBREVENTA, df_hora['pallets_out'])

# Recalcular Headcount y Diaristas Base
df_hora['hc_demanda_base'] = np.where(df_hora['dia'] == 'miércoles', np.ceil(df_hora['hc_demanda_total'] / FACTOR_SOBREVENTA), df_hora['hc_demanda_total'])
df_hora['diaristas_base'] = (df_hora['hc_demanda_base'] - df_hora['hc_oferta_meli']).clip(lower=0)

# Índice de línea de tiempo continua (168 horas)
df_hora['timeline_idx'] = range(len(df_hora))

# ------------------------------------------------------------------------------
# FIGURA 7: COMPARATIVO SEMANAL CONTINUO (168 HORAS) - INBOUND Y OUTBOUND
# ------------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True)

# Plot Inbound
ax1.plot(df_hora['timeline_idx'], df_hora['pallets_in_base'], color='#2ca02c', linestyle='--', linewidth=1.8, label='Pallets IN (Base Forecast)')
ax1.plot(df_hora['timeline_idx'], df_hora['pallets_in'], color='#1b5e20', linewidth=2.2, label='Pallets IN (Con Sobreventa +14% Miércoles)')
ax1.fill_between(df_hora['timeline_idx'], df_hora['pallets_in_base'], df_hora['pallets_in'], color='#2ca02c', alpha=0.35, label='Volumen Adicional Sobreventa')
ax1.set_title('Evolución Semanal: Flujo Inbound de Pallets (Base vs. Sobreventa)', fontsize=13, fontweight='bold')
ax1.set_ylabel('Pallets IN / Hora', fontsize=11)
ax1.legend(loc='upper right')

# Plot Outbound
ax2.plot(df_hora['timeline_idx'], df_hora['pallets_out_base'], color='#1f77b4', linestyle='--', linewidth=1.8, label='Pallets OUT (Base Forecast)')
ax2.plot(df_hora['timeline_idx'], df_hora['pallets_out'], color='#0d47a1', linewidth=2.2, label='Pallets OUT (Con Sobreventa +14% Miércoles)')
ax2.fill_between(df_hora['timeline_idx'], df_hora['pallets_out_base'], df_hora['pallets_out'], color='#1f77b4', alpha=0.35, label='Volumen Adicional Sobreventa')
ax2.set_title('Evolución Semanal: Flujo Outbound de Pallets (Base vs. Sobreventa)', fontsize=13, fontweight='bold')
ax2.set_ylabel('Pallets OUT / Hora', fontsize=11)
ax2.set_xlabel('Día de la Semana', fontsize=11)
ax2.legend(loc='upper right')

# Divisiones de días (cada 24 horas)
line_positions = np.arange(0, 168, 24)
for pos in line_positions:
    ax1.axvline(x=pos, color='gray', linestyle=':', alpha=0.6)
    ax2.axvline(x=pos, color='gray', linestyle=':', alpha=0.6)

# Sombrear la ventana del Miércoles (Peak Day)
ax1.axvspan(48, 72, color='#ffe6e6', alpha=0.4)
ax2.axvspan(48, 72, color='#ffe6e6', alpha=0.4)

ax2.set_xticks(line_positions + 12)
ax2.set_xticklabels([d.title() for d in dias_orden])

plt.tight_layout()
plt.savefig('figura7_comparativo_semanal_pallets.png', dpi=300)
plt.close()

# ------------------------------------------------------------------------------
# FIGURA 8: RESUMEN ACUMULADO DIARIO (BARRAS BARRAS COMPARATIVAS)
# ------------------------------------------------------------------------------
resumen_semanal = df_hora.groupby('dia', observed=False).agg({
    'pallets_in_base': 'sum',
    'pallets_in': 'sum',
    'diaristas_base': 'sum',
    'diaristas_requeridos_hora': 'sum'
}).reset_index()

fig, (ax_p, ax_d) = plt.subplots(1, 2, figsize=(14, 5))
x = np.arange(len(dias_orden))
width = 0.35

# Subplot Pallets Totales por Día
ax_p.bar(x - width/2, resumen_semanal['pallets_in_base'], width, label='Pallets IN (Base)', color='#81c784')
ax_p.bar(x + width/2, resumen_semanal['pallets_in'], width, label='Pallets IN (Con Sobreventa)', color='#2e7d32')
ax_p.set_title('Pallets Totales IN por Día de la Semana', fontsize=12, fontweight='bold')
ax_p.set_xticks(x)
ax_p.set_xticklabels([d.title() for d in dias_orden], rotation=30)
ax_p.set_ylabel('Total Pallets', fontsize=11)
ax_p.legend()

# Subplot Diaristas Totales Requeridos por Día
ax_d.bar(x - width/2, resumen_semanal['diaristas_base'], width, label='Horas-Diarista (Base)', color='#e57373')
ax_d.bar(x + width/2, resumen_semanal['diaristas_requeridos_hora'], width, label='Horas-Diarista (Con Sobreventa)', color='#c62828')
ax_d.set_title('Impacto en Horas de Diaristas por Día', fontsize=12, fontweight='bold')
ax_d.set_xticks(x)
ax_d.set_xticklabels([d.title() for d in dias_orden], rotation=30)
ax_d.set_ylabel('Total Horas-Diarista Requeridas', fontsize=11)
ax_d.legend()

plt.tight_layout()
plt.savefig('figura8_comparativo_diario_barras.png', dpi=300)
plt.close()

print("¡Imágenes semanales generadas con éxito!")