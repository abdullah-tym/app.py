import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import pdfkit
import base64
from io import BytesIO
import plotly.io as pio

st.set_page_config(page_title="Accountant Dashboard", layout="wide")
st.markdown("<h1 style='text-align: center; font-size: 52px; color: #2A9D8F;'>Accountant Dashboard</h1>", unsafe_allow_html=True)

COLORS = {
    "primary": "#2A9D8F", "secondary": "#E76F51", "accent": "#F4A261",
    "purple": "#8E44AD", "green": "#43AA8B", "crimson": "#E63946"
}

def render_kpi(value, label, color):
    return f"""<div style="background-color:{color}15;padding:20px 25px;
        border-left:6px solid {color};border-radius:12px;
        box-shadow:0 2px 6px rgba(0,0,0,0.05);margin-bottom:20px;">
        <div style="font-size:26px;font-weight:700;color:{color}">{value}</div>
        <div style="font-size:14px;color:#444;margin-top:6px;">{label}</div></div>"""

def make_kpi_html(value, label, color):
    return f"""<div style="background-color:{color};padding:20px;border-radius:12px;
        color:#fff;font-family:Arial;text-align:center;width:22%;
        display:inline-block;margin:10px 1%;"><div style="font-size:28px;
        font-weight:700;">{value}</div><div style="font-size:16px;margin-top:5px;">
        {label}</div></div>"""

def fig_to_base64(fig):
    return base64.b64encode(pio.to_image(fig, format="png", width=600, height=400)).decode()

path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

uploaded_file = st.file_uploader("⬆️ Upload your Excel file", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()
    for col in ['Invoice Date', 'Due Date', 'Payment Date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    if 'filters_init' not in st.session_state:
        st.session_state.client_filter = sorted(df['Customer'].dropna().unique())
        st.session_state.flow_filter = sorted(df['Cash Flow Type'].dropna().unique())
        st.session_state.overdue_filter = [True, False]
        st.session_state.date_range = (df['Invoice Date'].min(), df['Invoice Date'].max())
        st.session_state.filters_init = True

    st.sidebar.header("Filter Data")
    if st.sidebar.button("🔄 Reset Filters"):
        for key in ['client_filter', 'flow_filter', 'overdue_filter', 'date_range', 'filters_init']:
            if key in st.session_state: del st.session_state[key]
        st.experimental_rerun()

    clients = st.sidebar.multiselect("Customer", sorted(df['Customer'].dropna().unique()), default=st.session_state.client_filter, key='client_filter')
    flow_types = st.sidebar.multiselect("Cash Flow Type", sorted(df['Cash Flow Type'].dropna().unique()), default=st.session_state.flow_filter, key='flow_filter')
    overdue = st.sidebar.multiselect("Overdue", [True, False], format_func=lambda x: "Yes" if x else "No", default=st.session_state.overdue_filter, key='overdue_filter')
    date_range = st.sidebar.date_input("Invoice Date Range", value=st.session_state.date_range, key='date_range')

    if not clients: clients = sorted(df['Customer'].dropna().unique())
    if not flow_types: flow_types = sorted(df['Cash Flow Type'].dropna().unique())
    if not overdue: overdue = [True, False]

    filtered = df[
        df['Customer'].isin(clients) &
        df['Cash Flow Type'].isin(flow_types) &
        df['Overdue'].isin(overdue) &
        (df['Invoice Date'] >= pd.to_datetime(date_range[0])) &
        (df['Invoice Date'] <= pd.to_datetime(date_range[1]))
    ]
    if filtered.empty: st.warning("⚠️ No data matches your filters."); st.stop()
    if st.checkbox("Show raw data"): st.dataframe(filtered)

    total_invoiced = filtered['Invoice Amount'].sum()
    total_paid = filtered['Payment Made'].sum()
    total_outstanding = total_invoiced - total_paid
    overdue_count = filtered[filtered['Overdue'] == True].shape[0]

    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(render_kpi(f"${total_invoiced:,.2f}", "Total Invoiced", COLORS["primary"]), unsafe_allow_html=True)
    with k2: st.markdown(render_kpi(f"${total_paid:,.2f}", "Total Paid", COLORS["secondary"]), unsafe_allow_html=True)
    with k3: st.markdown(render_kpi(f"${total_outstanding:,.2f}", "Outstanding", COLORS["crimson"]), unsafe_allow_html=True)
    with k4: st.markdown(render_kpi(str(overdue_count), "Overdue Invoices", COLORS["accent"]), unsafe_allow_html=True)

    filtered['Month'] = filtered['Invoice Date'].dt.to_period('M').astype(str)
    filtered['Paid Month'] = filtered['Payment Date'].dt.to_period('M').astype(str)

    monthly = filtered.groupby('Month')[['Invoice Amount', 'Payment Made']].sum().reset_index()
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=monthly['Month'], y=monthly['Invoice Amount'], name='Invoiced', marker_color=COLORS['primary']))
    fig1.add_trace(go.Scatter(x=monthly['Month'], y=monthly['Payment Made'], name='Paid', mode='lines+markers', marker_color=COLORS['secondary']))
    fig1.update_layout(title='Monthly Invoiced vs Paid', xaxis_title='Month', yaxis_title='Amount ($)', template='plotly_white')

    top_clients = filtered.groupby('Customer')['Invoice Amount'].sum().nlargest(5).reset_index()
    fig2 = go.Figure(go.Bar(x=top_clients['Invoice Amount'], y=top_clients['Customer'], orientation='h', marker_color=COLORS['green']))
    fig2.update_layout(title='Top 5 Clients by Invoice Amount', xaxis_title='Invoice Amount ($)', yaxis=dict(autorange='reversed'), template='plotly_white')

    overdue_counts = filtered['Overdue'].value_counts().reset_index()
    overdue_counts.columns = ['Overdue', 'Count']
    overdue_counts['Overdue'] = overdue_counts['Overdue'].map({True: 'Overdue', False: 'On-time'})
    fig3 = go.Figure(go.Pie(labels=overdue_counts['Overdue'], values=overdue_counts['Count'], hole=0.4, marker_colors=[COLORS['crimson'], COLORS['green']]))
    fig3.update_layout(title='Overdue vs On-time Invoices', template='plotly_white')

    paid_monthly = filtered.groupby('Paid Month')['Payment Made'].sum().reset_index()
    fig4 = go.Figure(go.Scatter(x=paid_monthly['Paid Month'], y=paid_monthly['Payment Made'], mode='lines+markers', marker_color=COLORS['primary']))
    fig4.update_layout(title='Monthly Payments', xaxis_title='Month', yaxis_title='Amount ($)', template='plotly_white')

    invoice_counts = filtered.groupby('Month').size().reset_index(name='Count')
    fig5 = go.Figure(go.Bar(x=invoice_counts['Month'], y=invoice_counts['Count'], marker_color=COLORS['purple']))
    fig5.update_layout(title='Invoice Count Per Month', xaxis_title='Month', yaxis_title='Count', template='plotly_white')

    filtered['Outstanding'] = filtered['Invoice Amount'] - filtered['Payment Made']
    outstanding_flow = filtered.groupby('Cash Flow Type')['Outstanding'].sum().reset_index()
    fig6 = go.Figure(go.Bar(x=outstanding_flow['Cash Flow Type'], y=outstanding_flow['Outstanding'], marker_color=COLORS['crimson']))
    fig6.update_layout(title='Outstanding by Cash Flow Type', xaxis_title='Cash Flow Type', yaxis_title='Amount ($)', template='plotly_white')

    charts = [fig1, fig2, fig3, fig4, fig5, fig6]
    for i in range(0, 6, 3):
        cols = st.columns(3)
        for j, fig in enumerate(charts[i:i+3]):
            with cols[j]: st.plotly_chart(fig, use_container_width=True)

    if st.button("📄 Export Dashboard to PDF"):
        try:
            kpi_html = (
                make_kpi_html(f"${total_invoiced:,.2f}", "Total Invoiced", COLORS["primary"]) +
                make_kpi_html(f"${total_paid:,.2f}", "Total Paid", COLORS["secondary"]) +
                make_kpi_html(f"${total_outstanding:,.2f}", "Outstanding", COLORS["crimson"]) +
                make_kpi_html(str(overdue_count), "Overdue Invoices", COLORS["accent"])
            )
            chart_html = ""
            for i, fig in enumerate(charts):
                style = "width:31%;margin:1%;" if i % 3 != 2 else "width:31%;margin:1%;clear:right;"
                chart_html += f'<img src="data:image/png;base64,{fig_to_base64(fig)}" style="{style}" />'
            html = f"""<html><head><meta charset="utf-8">
            <style>body{{font-family:Arial;padding:30px;background:#f7f9fc;}}
            h1{{text-align:center;color:{COLORS["primary"]};}}.kpis{{text-align:center;margin-bottom:20px;}}
            .charts{{text-align:center;}}</style></head><body>
            <h1>Accountant Dashboard Report</h1>
            <div class="kpis">{kpi_html}</div>
            <div class="charts">{chart_html}</div>
            </body></html>"""
            pdf = pdfkit.from_string(html, False, configuration=config, options={"orientation": "Landscape"})
            st.download_button("📥 Download PDF Report", data=pdf, file_name="accountant_dashboard.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF export failed: {e}")
else:
    st.info("Please upload your Excel file to view the dashboard.")
