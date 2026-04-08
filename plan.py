import streamlit as st
import pandas as pd
from datetime import date, timedelta
import calendar
import math

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Plan de Pagos",
    page_icon="💰",
    layout="wide",
)

# ─── CUSTOM CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Sora:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
}

/* Background */
.stApp {
    background: #0d0f1a;
    color: #e8eaf0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #13162a !important;
    border-right: 1px solid #1e2240;
}
[data-testid="stSidebar"] * {
    color: #c8cce0 !important;
}

/* Main header */
.main-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6ee7ff 0%, #a78bfa 60%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
}
.sub-title {
    font-size: 0.95rem;
    color: #6b7280;
    margin-bottom: 2rem;
    font-weight: 300;
}

/* Metric cards */
.metric-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 2rem;
}
.metric-card {
    background: linear-gradient(135deg, #161a2e 0%, #1a1e35 100%);
    border: 1px solid #2a2f50;
    border-radius: 16px;
    padding: 1.2rem 1.6rem;
    flex: 1;
    min-width: 160px;
}
.metric-card .label {
    font-size: 0.72rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    margin-bottom: 0.4rem;
}
.metric-card .value {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e8eaf0;
}
.metric-card .value.accent { color: #6ee7ff; }
.metric-card .value.warn   { color: #f472b6; }
.metric-card .value.good   { color: #4ade80; }

/* Section headers */
.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #a78bfa;
    border-left: 3px solid #a78bfa;
    padding-left: 0.75rem;
    margin: 1.5rem 0 1rem 0;
}

/* Table styling */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

/* Inputs */
.stNumberInput input, .stTextInput input, .stDateInput input, .stSelectbox select {
    background: #1a1e35 !important;
    border: 1px solid #2a2f50 !important;
    color: #e8eaf0 !important;
    border-radius: 8px !important;
}
.stSlider .stSlider { color: #6ee7ff; }

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, #6ee7ff22, #a78bfa22);
    border: 1px solid #a78bfa;
    color: #a78bfa;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    letter-spacing: 0.05em;
    transition: all 0.2s;
}
.stButton>button:hover {
    background: linear-gradient(135deg, #6ee7ff44, #a78bfa44);
    transform: translateY(-1px);
}

/* Expander */
.streamlit-expanderHeader {
    background: #13162a !important;
    border-radius: 8px !important;
    color: #c8cce0 !important;
}

/* Alerts */
.info-box {
    background: #161a2e;
    border: 1px solid #2a2f50;
    border-left: 4px solid #6ee7ff;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: #a0aec0;
}

/* Pill badge */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.badge-blue { background: #6ee7ff22; color: #6ee7ff; border: 1px solid #6ee7ff44; }
.badge-pink { background: #f472b622; color: #f472b6; border: 1px solid #f472b644; }
.badge-green { background: #4ade8022; color: #4ade80; border: 1px solid #4ade8044; }
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ────────────────────────────────────────────────────────────────

def fmt_cop(value: float) -> str:
    """Format number as Colombian peso."""
    if value < 0:
        return f"-${abs(value):,.0f}"
    return f"${value:,.0f}"

def add_months(dt: date, months: int) -> date:
    month = dt.month - 1 + months
    year  = dt.year + month // 12
    month = month % 12 + 1
    day   = min(dt.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def build_income_schedule(
    start_date: date,
    base_income: float,
    n_cuotas: int,
    prima_pct: float,           # % de prima (ej. 8.33 = 1 mes)
    prima_months: list[int],    # meses en que cae prima [6, 12]
    adelantos: list[dict],      # [{"cuota": int, "valor": float}]
):
    """
    Returns list of dicts with income for each cuota period.
    Income = salary of that month + prima if applicable + adelantos.
    """
    schedule = []
    current_salary = base_income
    for i in range(n_cuotas):
        cuota_date   = add_months(start_date, i)
        extra_prima  = 0.0
        note_parts   = []

        # Prima cada 6 meses
        if prima_months and cuota_date.month in prima_months:
            extra_prima = current_salary * (prima_pct / 100)
            note_parts.append(f"Prima {fmt_cop(extra_prima)}")

        # Adelantos / cesantías
        extra_adelanto = 0.0
        for adv in adelantos:
            if adv["cuota"] == i + 1:
                extra_adelanto += adv["valor"]
                note_parts.append(f"Adelanto {fmt_cop(adv['valor'])}")

        total_income = current_salary + extra_prima + extra_adelanto
        schedule.append({
            "cuota_num":    i + 1,
            "fecha":        cuota_date,
            "salario_base": current_salary,
            "prima":        extra_prima,
            "adelanto":     extra_adelanto,
            "ingreso_total": total_income,
            "notas":        ", ".join(note_parts) if note_parts else "—",
        })
    return schedule

def calculate_plan(
    valor_total: float,
    start_date: date,
    n_cuotas: int,
    base_income: float,
    prima_pct: float,
    prima_months: list[int],
    adelantos: list[dict],
    aumento_salario_pct: float,   # % de aumento cada 6 meses
    aumento_cada: int,             # cada cuántos meses aplica aumento
    porcentaje_ingreso: float,     # % del ingreso a destinar al pago
    cuota_fija: float | None,      # si None → usa porcentaje_ingreso o % deuda
    modo_base_cuota: str = "ingreso",  # "ingreso" | "deuda"
    porcentaje_deuda: float = 0.0,     # % del saldo restante a pagar cada mes
):
    """
    Core calculation. Returns (rows, summary).
    """
    income_sched = []
    current_salary = base_income
    saldo = valor_total

    rows = []
    total_pagado = 0.0
    total_prima  = 0.0
    total_adelanto = 0.0

    for i in range(n_cuotas):
        if saldo <= 0:
            break

        cuota_date = add_months(start_date, i)

        # Aumento de salario cada N meses
        if i > 0 and aumento_cada > 0 and i % aumento_cada == 0:
            current_salary *= (1 + aumento_salario_pct / 100)

        # Prima
        extra_prima = 0.0
        if prima_months and cuota_date.month in prima_months:
            extra_prima = current_salary * (prima_pct / 100)

        # Adelantos
        extra_adelanto = 0.0
        note_parts = []
        for adv in adelantos:
            if adv["cuota"] == i + 1:
                extra_adelanto += adv["valor"]
                note_parts.append(f"Adelanto {fmt_cop(adv['valor'])}")

        ingreso_total = current_salary + extra_prima + extra_adelanto

        # Cuota
        if cuota_fija is not None and cuota_fija > 0:
            cuota_val = cuota_fija
        elif modo_base_cuota == "deuda":
            # % del saldo actual: cuota decrece a medida que se paga
            cuota_val = saldo * (porcentaje_deuda / 100)
        else:
            cuota_val = ingreso_total * (porcentaje_ingreso / 100)

        # Última cuota no supera el saldo
        cuota_val = min(cuota_val, saldo)
        saldo_anterior = saldo
        saldo -= cuota_val
        total_pagado   += cuota_val
        total_prima    += extra_prima
        total_adelanto += extra_adelanto

        if extra_prima > 0:
            note_parts.insert(0, f"Prima {fmt_cop(extra_prima)}")

        valor_abono = cuota_val + extra_prima + extra_adelanto

        pct_cuota_sobre_ingreso = (cuota_val / ingreso_total * 100) if ingreso_total > 0 else 0.0

        rows.append({
            "Cuota #":         i + 1,
            "Fecha":           cuota_date.strftime("%b %Y"),
            "fecha_dt":        cuota_date,
            "Salario Base":    current_salary,
            "Prima":           extra_prima,
            "Adelanto/Ces.":   extra_adelanto,
            "Ingreso Total":   ingreso_total,
            "Valor Cuota":     cuota_val,
            "% s/Ingreso":     round(pct_cuota_sobre_ingreso, 1),
            "Valor Abono":     valor_abono,
            "Valor Acumulado": total_pagado,
            "Saldo Restante":  max(saldo, 0),
            "Notas":           ", ".join(note_parts) if note_parts else "—",
        })

        if saldo <= 0:
            break

    summary = {
        "cuotas_usadas":  len(rows),
        "total_pagado":   total_pagado,
        "saldo_final":    max(saldo, 0),
        "total_prima":    total_prima,
        "total_adelanto": total_adelanto,
        "liquidado":      saldo <= 0,
    }
    return rows, summary


# ════════════════════════════════════════════════════════════════════════════
#  UI
# ════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="main-title">📊 Plan de Pagos</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Simulador reactivo · Prima · Adelantos · Cesantías</p>', unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")

    st.markdown("---")
    st.markdown("### 💳 Deuda")
    valor_total = st.number_input(
        "Valor total a pagar ($)",
        min_value=0.0, value=10_000_000.0, step=100_000.0, format="%.0f"
    )

    st.markdown("### 📅 Plazo")
    modo_plazo = st.radio("Definir plazo por:", ["Número de cuotas", "Fecha de finalización"], horizontal=True)

    start_date = st.date_input("Fecha inicio", value=date.today().replace(day=1))

    if modo_plazo == "Número de cuotas":
        n_cuotas = st.number_input("Número de cuotas (meses)", min_value=1, max_value=360, value=24, step=1)
        end_date_est = add_months(start_date, n_cuotas - 1)
        st.caption(f"📌 Fecha estimada fin: **{end_date_est.strftime('%b %Y')}**")
    else:
        end_date = st.date_input("Fecha de finalización", value=add_months(date.today().replace(day=1), 24))
        if end_date <= start_date:
            st.error("La fecha de fin debe ser posterior a la de inicio.")
            n_cuotas = 1
        else:
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
            n_cuotas = max(1, months_diff)
            st.caption(f"📌 Total de cuotas: **{n_cuotas}**")

    st.markdown("---")
    st.markdown("### 💼 Ingreso")
    base_income = st.number_input(
        "Salario base mensual ($)",
        min_value=0.0, value=3_500_000.0, step=50_000.0, format="%.0f"
    )

    st.markdown("### 📈 Aumento de salario")
    tiene_aumento = st.checkbox("¿Aplica aumento periódico de salario?", value=True)
    if tiene_aumento:
        aumento_pct   = st.number_input("% de aumento", min_value=0.0, max_value=100.0, value=6.0, step=0.5)
        aumento_cada  = st.selectbox("Cada cuántos meses", [6, 12, 3], index=1)
    else:
        aumento_pct  = 0.0
        aumento_cada = 12

    st.markdown("### 🎁 Prima de salario")
    tiene_prima = st.checkbox("¿Recibe prima semestral?", value=True)
    if tiene_prima:
        prima_pct = st.number_input(
            "Prima como % del salario base",
            min_value=0.0, max_value=100.0, value=8.33, step=0.01,
            help="8.33% ≈ 1 mes de salario (prima legal Colombia)"
        )
        prima_meses_opciones = {
            "Junio y Diciembre (meses 6 y 12)": [6, 12],
            "Solo Junio (mes 6)": [6],
            "Solo Diciembre (mes 12)": [12],
        }
        prima_sel = st.selectbox("Meses de prima", list(prima_meses_opciones.keys()))
        prima_months = prima_meses_opciones[prima_sel]
    else:
        prima_pct    = 0.0
        prima_months = []

    st.markdown("---")
    st.markdown("### 💵 Cuota mensual")
    modo_cuota = st.radio(
        "Calcular cuota como:",
        ["% del ingreso total", "% del saldo restante", "Cuota fija"],
        horizontal=True,
    )
    if modo_cuota == "% del ingreso total":
        pct_ingreso = st.slider("% del ingreso destinado al pago", 5, 100, 40, step=5)
        pct_deuda = 0.0
        cuota_fija_val = None
        modo_base = "ingreso"
    elif modo_cuota == "% del saldo restante":
        pct_deuda = st.slider(
            "% del saldo restante a pagar cada mes", 1, 100, 10, step=1,
            help="La cuota se recalcula cada mes sobre el saldo pendiente: decrece conforme la deuda baja."
        )
        # Preview cuota inicial
        cuota_inicial_est = valor_total * (pct_deuda / 100)
        st.caption(f"📌 Cuota estimada mes 1: **{fmt_cop(cuota_inicial_est)}**")
        pct_ingreso = 0
        cuota_fija_val = None
        modo_base = "deuda"
    else:
        cuota_fija_val = st.number_input(
            "Cuota fija mensual ($)", min_value=0.0, value=400_000.0, step=10_000.0, format="%.0f"
        )
        pct_ingreso = 0
        pct_deuda = 0.0
        modo_base = "ingreso"

    st.markdown("---")
    st.markdown("### ⚡ Adelantos / Cesantías")
    num_adelantos = st.number_input("Número de adelantos a registrar", min_value=0, max_value=20, value=0, step=1)

adelantos = []
if num_adelantos > 0:
    st.markdown('<p class="section-header">⚡ Adelantos / Cesantías</p>', unsafe_allow_html=True)
    cols_adv = st.columns([1, 2, 3])
    cols_adv[0].markdown("**Cuota #**")
    cols_adv[1].markdown("**Valor ($)**")
    cols_adv[2].markdown("**Descripción**")
    for j in range(int(num_adelantos)):
        c1, c2, c3 = st.columns([1, 2, 3])
        with c1:
            cuota_num_adv = st.number_input(f"Cuota", min_value=1, max_value=n_cuotas, value=j+1,
                                             key=f"adv_cuota_{j}", label_visibility="collapsed")
        with c2:
            valor_adv = st.number_input(f"Valor", min_value=0.0, value=500_000.0, step=50_000.0,
                                         key=f"adv_valor_{j}", format="%.0f", label_visibility="collapsed")
        with c3:
            desc_adv = st.text_input(f"Desc.", value="Cesantías", key=f"adv_desc_{j}", label_visibility="collapsed")
        adelantos.append({"cuota": int(cuota_num_adv), "valor": valor_adv, "desc": desc_adv})

# ─── CALCULATION (reactive) ──────────────────────────────────────────────────
rows, summary = calculate_plan(
    valor_total       = valor_total,
    start_date        = start_date,
    n_cuotas          = n_cuotas,
    base_income       = base_income,
    prima_pct         = prima_pct,
    prima_months      = prima_months,
    adelantos         = adelantos,
    aumento_salario_pct = aumento_pct,
    aumento_cada      = aumento_cada,
    porcentaje_ingreso = pct_ingreso,
    cuota_fija        = cuota_fija_val,
    modo_base_cuota   = modo_base,
    porcentaje_deuda  = pct_deuda,
)

# ─── KPI CARDS ──────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Deuda Total</div>
        <div class="value accent">{fmt_cop(valor_total)}</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Cuotas Necesarias</div>
        <div class="value">{summary['cuotas_usadas']} / {n_cuotas}</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Total Pagado</div>
        <div class="value good">{fmt_cop(summary['total_pagado'])}</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Saldo Final</div>
        <div class="value {'good' if summary['liquidado'] else 'warn'}">{fmt_cop(summary['saldo_final'])}</div>
    </div>""", unsafe_allow_html=True)

with c5:
    estado = "✅ Liquidado" if summary['liquidado'] else "⚠️ Pendiente"
    color  = "good" if summary['liquidado'] else "warn"
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Estado</div>
        <div class="value {color}" style="font-size:1.1rem">{estado}</div>
    </div>""", unsafe_allow_html=True)

# ─── ALERT ──────────────────────────────────────────────────────────────────
if not summary['liquidado']:
    st.markdown(f"""
    <div class="info-box">
        ⚠️ Con la configuración actual la deuda <strong>no se liquida</strong> en {n_cuotas} cuotas.
        Saldo restante: <strong>{fmt_cop(summary['saldo_final'])}</strong>.
        Considera aumentar el % de ingreso, agregar adelantos o extender el plazo.
    </div>""", unsafe_allow_html=True)
else:
    if summary['cuotas_usadas'] < n_cuotas:
        st.markdown(f"""
        <div class="info-box" style="border-left-color:#4ade80">
            ✅ La deuda se liquida en <strong>{summary['cuotas_usadas']} cuotas</strong>
            ({n_cuotas - summary['cuotas_usadas']} cuotas antes del plazo máximo).
        </div>""", unsafe_allow_html=True)

# ─── TABLA DETALLADA ────────────────────────────────────────────────────────
st.markdown('<p class="section-header">📋 Tabla del Plan de Pagos</p>', unsafe_allow_html=True)

if rows:
    df = pd.DataFrame(rows)

    # Format currency columns for display
    currency_cols = ["Salario Base", "Prima", "Adelanto/Ces.", "Ingreso Total",
                     "Valor Cuota", "Valor Abono", "Valor Acumulado", "Saldo Restante"]
    df_display = df.drop(columns=["fecha_dt"], errors="ignore").copy()
    for col in currency_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(fmt_cop)
    if "% s/Ingreso" in df_display.columns:
        df_display["% s/Ingreso"] = df_display["% s/Ingreso"].apply(lambda x: f"{x:.1f}%")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cuota #":         st.column_config.NumberColumn(width="small"),
            "Fecha":           st.column_config.TextColumn(width="small"),
            "Salario Base":    st.column_config.TextColumn(),
            "Prima":           st.column_config.TextColumn(),
            "Adelanto/Ces.":   st.column_config.TextColumn(),
            "Ingreso Total":   st.column_config.TextColumn(),
            "Valor Cuota":     st.column_config.TextColumn(),
            "% s/Ingreso":     st.column_config.TextColumn(width="small"),
            "Valor Abono":     st.column_config.TextColumn(),
            "Valor Acumulado": st.column_config.TextColumn(),
            "Saldo Restante":  st.column_config.TextColumn(),
            "Notas":           st.column_config.TextColumn(width="medium"),
        }
    )

    # ─── GRÁFICO ────────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">📉 Evolución del Saldo</p>', unsafe_allow_html=True)

    # Usar fecha real (date) como índice para que el orden sea cronológico
    chart_df = df[["fecha_dt", "Saldo Restante", "Valor Cuota", "Ingreso Total"]].copy()
    chart_df["fecha_dt"] = pd.to_datetime(chart_df["fecha_dt"])
    chart_df = chart_df.sort_values("fecha_dt")
    chart_df = chart_df.rename(columns={
        "fecha_dt":       "Fecha",
        "Saldo Restante": "Saldo ($)",
        "Valor Cuota":    "Cuota ($)",
        "Ingreso Total":  "Ingreso ($)",
    })
    chart_df = chart_df.set_index("Fecha")

    tab1, tab2 = st.tabs(["📉 Saldo restante", "📊 Cuota vs Ingreso"])
    with tab1:
        st.area_chart(chart_df[["Saldo ($)"]], color=["#6ee7ff"])
    with tab2:
        st.bar_chart(chart_df[["Cuota ($)", "Ingreso ($)"]], color=["#a78bfa", "#f472b6"])

    # ─── RESUMEN EXTRA ──────────────────────────────────────────────────────
    with st.expander("📊 Resumen detallado"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Valor total deuda:** {fmt_cop(valor_total)}")
            st.markdown(f"**Total pagado:** {fmt_cop(summary['total_pagado'])}")
            st.markdown(f"**Saldo final:** {fmt_cop(summary['saldo_final'])}")
        with col_b:
            st.markdown(f"**Total primas aplicadas:** {fmt_cop(summary['total_prima'])}")
            st.markdown(f"**Total adelantos/cesantías:** {fmt_cop(summary['total_adelanto'])}")
            st.markdown(f"**Cuotas ejecutadas:** {summary['cuotas_usadas']}")

    # ─── EXPORT EXCEL ───────────────────────────────────────────────────────
    import io
    output = io.BytesIO()
    df_excel = df.drop(columns=["fecha_dt"], errors="ignore")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_excel.to_excel(writer, index=False, sheet_name="Plan de Pagos")
        ws = writer.sheets["Plan de Pagos"]
        for col_cells in ws.columns:
            max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col_cells)
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 30)
    output.seek(0)

    st.download_button(
        label="⬇️ Descargar plan en Excel",
        data=output,
        file_name="plan_de_pagos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.warning("No se generaron cuotas. Verifica los valores ingresados.")

# ─── FOOTER ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#374151;font-size:0.8rem;">Plan de Pagos · Desarrollado con Streamlit · Todos los cálculos son estimaciones</p>',
    unsafe_allow_html=True
)