import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import arabic_reshaper
from bidi.algorithm import get_display
import io
import os
import base64

# === Setup ===
st.set_page_config(page_title="Mojaz.App", layout="wide")
st.markdown(
    "<h1 style='text-align: center; font-size: 52px; color: #E76F51; margin-bottom: 0;'>Mojaz.App</h1>",
    unsafe_allow_html=True
)

# === Global Colors & Style ===
COLORS = {
    "primary": "#2A9D8F",
    "secondary": "#E76F51",
    "accent": "#F4A261",
    "purple": "#8E44AD",
    "green": "#43AA8B",
    "crimson": "#E63946",
    "bg": "#FFFFFF",
    "grid": "#E0E0E0",
    "text": "#222222"
}

plt.rcParams.update({
    "axes.facecolor": COLORS["bg"],
    "axes.edgecolor": COLORS["bg"],
    "axes.labelcolor": COLORS["text"],
    "xtick.color": COLORS["text"],
    "ytick.color": COLORS["text"],
    "axes.titlesize": 16,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "axes.titlepad": 15,
    "grid.color": COLORS["grid"],
    "grid.linestyle": "--",
    "grid.linewidth": 0.5,
})

# === Arabic helpers ===
def reshape(text):
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except:
        return str(text)

def fix_xticks(ax, labels, font):
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([reshape(x) for x in labels], rotation=45, fontproperties=font)

def plot_and_return(fig):
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches='tight')
    buf.seek(0)
    return buf

def clean_chart(ax, title):
    ax.set_facecolor(COLORS["bg"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(True, axis='y')
    ax.set_title(reshape(title), fontproperties=arabic_font_prop, color=COLORS["text"])

# === Load Amiri Font ===
font_path = "Amiri.ttf"
if os.path.exists(font_path):
    arabic_font_prop = fm.FontProperties(fname=font_path)
else:
    arabic_font_prop = fm.FontProperties()
    st.warning("⚠️ خط Amiri غير موجود. سيتم استخدام الخط الافتراضي.")

# === File Upload ===
uploaded_file = st.file_uploader("⬆️ حمّل ملف Excel الخاص بالعميل", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # === Rename columns ===
    df = df.rename(columns={
        'مبلغ الفاتورة (ر.س)': 'invoice_amount',
        'المبلغ المدفوع (ر.س)': 'paid_amount',
        'حالة الدفع': 'payment_status',
        'أيام التأخير': 'delay_days',
        'تاريخ الفاتورة': 'issue_date',
        'تاريخ الاستحقاق': 'due_date',
        'تاريخ الدفع': 'payment_date',
        'اسم العميل': 'client',
        'طريقة الدفع': 'payment_method',
        'رقم الفاتورة': 'invoice_no'
    })

    for date_col in ['issue_date', 'due_date', 'payment_date']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # === Filters (with Reset support) ===
    st.sidebar.header("تصفية البيانات")

    if 'filters_initialized' not in st.session_state or st.sidebar.button("🔄 إعادة تعيين الفلاتر"):
        st.session_state.client_filter = sorted(df['client'].dropna().unique())
        st.session_state.payment_status_filter = sorted(df['payment_status'].dropna().unique())
        st.session_state.payment_method_filter = sorted(df['payment_method'].dropna().unique())
        st.session_state.issue_date_range = (df['issue_date'].min(), df['issue_date'].max())
        st.session_state.due_date_range = (df['due_date'].min(), df['due_date'].max())
        st.session_state.delay_days_range = (int(df['delay_days'].min()), int(df['delay_days'].max()))
        st.session_state.filters_initialized = True

    client_filter = st.sidebar.multiselect(
        "اختر العملاء",
        sorted(df['client'].dropna().unique()),
        default=st.session_state.client_filter,
        key="client_filter"
    )

    payment_status_filter = st.sidebar.multiselect(
        "حالة الدفع",
        sorted(df['payment_status'].dropna().unique()),
        default=st.session_state.payment_status_filter,
        key="payment_status_filter"
    )

    payment_method_filter = st.sidebar.multiselect(
        "طريقة الدفع",
        sorted(df['payment_method'].dropna().unique()),
        default=st.session_state.payment_method_filter,
        key="payment_method_filter"
    )

    issue_date_range = st.sidebar.date_input(
        "تاريخ الفاتورة من - إلى",
        value=st.session_state.issue_date_range,
        key="issue_date_range"
    )

    due_date_range = st.sidebar.date_input(
        "تاريخ الاستحقاق من - إلى",
        value=st.session_state.due_date_range,
        key="due_date_range"
    )

    delay_days_range = st.sidebar.slider(
        "عدد أيام التأخير",
        int(df['delay_days'].min()),
        int(df['delay_days'].max()),
        value=st.session_state.delay_days_range,
        key="delay_days_range"
    )

    filtered_df = df[
        (df['client'].isin(client_filter)) &
        (df['payment_status'].isin(payment_status_filter)) &
        (df['payment_method'].isin(payment_method_filter)) &
        (df['issue_date'] >= pd.to_datetime(issue_date_range[0])) &
        (df['issue_date'] <= pd.to_datetime(issue_date_range[1])) &
        (df['due_date'] >= pd.to_datetime(due_date_range[0])) &
        (df['due_date'] <= pd.to_datetime(due_date_range[1])) &
        (df['delay_days'] >= delay_days_range[0]) &
        (df['delay_days'] <= delay_days_range[1])
    ]

    if filtered_df.empty:
        st.warning("⚠️ لا توجد بيانات تطابق الفلاتر المختارة.")
    else:
        # --- Show raw data toggle ---
        if st.checkbox("📋 Show Raw Data"):
            st.subheader("البيانات الخام")
            st.dataframe(filtered_df)

        # === KPIs ===
        total_invoices_amount = filtered_df['invoice_amount'].sum()
        total_paid_amount = filtered_df['paid_amount'].sum()
        total_outstanding = total_invoices_amount - total_paid_amount
        paid_invoices_count = filtered_df[filtered_df['payment_status'] == 'مدفوع'].shape[0]
        late_invoices_count = filtered_df[filtered_df['delay_days'] > 0].shape[0]
        avg_delay_days = filtered_df.loc[filtered_df['delay_days'] > 0, 'delay_days'].mean()

        def render_kpi(value, label, color):
            return f"""<div style="background-color:{color}15;padding:20px 25px;
                border-left:6px solid {color};border-radius:12px;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);margin-bottom:20px;">
                <div style="font-size:26px;font-weight:700;color:{color}">{value}</div>
                <div style="font-size:14px;color:#444;margin-top:6px;">{label}</div></div>"""

        kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
        kpi1.markdown(render_kpi(f"{total_invoices_amount:,.0f} ﷼", "إجمالي مبلغ الفواتير", COLORS["primary"]), unsafe_allow_html=True)
        kpi2.markdown(render_kpi(f"{total_paid_amount:,.0f} ﷼", "إجمالي المبلغ المدفوع", COLORS["secondary"]), unsafe_allow_html=True)
        kpi3.markdown(render_kpi(f"{total_outstanding:,.0f} ﷼", "إجمالي المتبقي", COLORS["crimson"]), unsafe_allow_html=True)
        kpi4.markdown(render_kpi(f"{paid_invoices_count}", "عدد الفواتير المدفوعة بالكامل", COLORS["accent"]), unsafe_allow_html=True)
        kpi5.markdown(render_kpi(f"{late_invoices_count}", "عدد الفواتير المتأخرة", COLORS["purple"]), unsafe_allow_html=True)
        kpi6.markdown(render_kpi(f"{avg_delay_days:.1f} يوم", "متوسط أيام التأخير", COLORS["green"]), unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # === Charts ===
        chart_images = []

        # 1. Monthly Invoice vs Paid
        filtered_df['Month'] = filtered_df['issue_date'].dt.to_period('M').astype(str)
        monthly = filtered_df.groupby('Month')[['invoice_amount', 'paid_amount']].sum()
        fig, ax = plt.subplots(figsize=(7, 4))
        monthly['invoice_amount'].plot(kind='bar', ax=ax, color=COLORS['primary'], label=reshape("الفواتير"))
        monthly['paid_amount'].plot(kind='line', ax=ax, color=COLORS['secondary'], marker='o', label=reshape("المدفوع"), linewidth=2)
        fix_xticks(ax, monthly.index, arabic_font_prop)
        ax.legend(prop=arabic_font_prop)
        clean_chart(ax, "مقارنة الفواتير والمدفوع شهرياً")
        ax.set_xlabel(reshape("شهر الإصدار"), fontproperties=arabic_font_prop, color=COLORS["text"])
        chart_images.append(plot_and_return(fig))

        # 2. Top Clients
        top_clients = filtered_df.groupby('client')['invoice_amount'].sum().nlargest(5)
        fig, ax = plt.subplots(figsize=(6, 3))
        top_clients.plot(kind='barh', ax=ax, color=COLORS['green'], edgecolor='black')
        ax.set_yticklabels([reshape(x) for x in top_clients.index], fontproperties=arabic_font_prop)
        clean_chart(ax, "أعلى ٥ عملاء حسب مبلغ الفاتورة")
        chart_images.append(plot_and_return(fig))

        # 3. Donut by Payment Method (smaller)
        by_method = filtered_df.groupby('payment_method')['invoice_amount'].sum()
        fig, ax = plt.subplots(figsize=(3, 3))  # smaller figure size
        wedges, _, _ = ax.pie(by_method, labels=[reshape(x) for x in by_method.index], autopct='%1.1f%%',
                              startangle=90, wedgeprops=dict(width=0.4), colors=plt.cm.Set2.colors)
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        fig.gca().add_artist(centre_circle)
        ax.set_title(reshape("توزيع طرق الدفع"), fontproperties=arabic_font_prop, color=COLORS["text"])
        chart_images.append(plot_and_return(fig))

        # 4. Payment Status Pie
        counts = filtered_df['payment_status'].value_counts()
        fig, ax = plt.subplots(figsize=(4, 4))
        labels = [reshape(label) for label in counts.index]
        counts.plot(kind='pie', autopct='%1.1f%%', startangle=90, ax=ax, colors=plt.cm.Paired.colors, labels=labels)
        ax.set_ylabel('')
        ax.set_title(reshape("حالة الدفع"), fontproperties=arabic_font_prop, color=COLORS["text"])
        chart_images.append(plot_and_return(fig))

        # 5. Late Invoices Per Month
        filtered_df['Late Month'] = filtered_df['due_date'].dt.to_period('M').astype(str)
        delayed = filtered_df[filtered_df['delay_days'] > 0].groupby('Late Month').size()
        fig, ax = plt.subplots(figsize=(6, 3))
        delayed.plot(kind='line', ax=ax, color=COLORS['crimson'], marker='o', linewidth=2)
        fix_xticks(ax, delayed.index, arabic_font_prop)
        clean_chart(ax, "عدد الفواتير المتأخرة شهرياً")
        ax.set_xlabel(reshape("شهر التأخير"), fontproperties=arabic_font_prop, color=COLORS["text"])
        chart_images.append(plot_and_return(fig))

        # 6. Avg Delay by Client
        avg_delay = filtered_df.groupby('client')['delay_days'].mean().nlargest(5)
        fig, ax = plt.subplots(figsize=(6, 3))
        avg_delay.plot(kind='bar', ax=ax, color=COLORS['crimson'], edgecolor='black')
        fix_xticks(ax, avg_delay.index, arabic_font_prop)
        ax.set_xlabel(reshape("عميل"), fontproperties=arabic_font_prop)
        clean_chart(ax, "متوسط التأخير حسب العميل")
        chart_images.append(plot_and_return(fig))

        # 7. Invoice Count per Month
        filtered_df['Issue Month'] = filtered_df['issue_date'].dt.to_period('M').astype(str)
        invoice_count = filtered_df.groupby('Issue Month').size()
        fig, ax = plt.subplots(figsize=(6, 3))
        invoice_count.plot(kind='bar', ax=ax, color=COLORS['purple'])
        fix_xticks(ax, invoice_count.index, arabic_font_prop)
        clean_chart(ax, "عدد الفواتير شهرياً")
        ax.set_xlabel(reshape("شهر الإصدار"), fontproperties=arabic_font_prop, color=COLORS["text"])
        chart_images.append(plot_and_return(fig))

        # 8. Paid Amount Trend
        filtered_df['Pay Month'] = filtered_df['payment_date'].dt.to_period('M').astype(str)
        paid_monthly = filtered_df.groupby('Pay Month')['paid_amount'].sum()
        fig, ax = plt.subplots(figsize=(6, 3))
        paid_monthly.plot(kind='line', ax=ax, color=COLORS['primary'], marker='o', linewidth=2)
        fix_xticks(ax, paid_monthly.index, arabic_font_prop)
        clean_chart(ax, "اتجاه المبالغ المدفوعة شهرياً")
        ax.set_xlabel(reshape("شهر الدفع"), fontproperties=arabic_font_prop, color=COLORS["text"])
        chart_images.append(plot_and_return(fig))

        # 9. Outstanding by Payment Method
        filtered_df['outstanding'] = filtered_df['invoice_amount'] - filtered_df['paid_amount']
        outstanding_by_method = filtered_df.groupby('payment_method')['outstanding'].sum()
        fig, ax = plt.subplots(figsize=(6, 3))
        outstanding_by_method.plot(kind='bar', ax=ax, color=COLORS['accent'], edgecolor='black')
        fix_xticks(ax, outstanding_by_method.index, arabic_font_prop)
        ax.set_xlabel(reshape("طريقة الدفع"), fontproperties=arabic_font_prop)
        clean_chart(ax, "المبالغ المتبقية حسب طريقة الدفع")
        chart_images.append(plot_and_return(fig))

        # === Display Charts in Grid ===
        for row_i in range(3):
            cols = st.columns(3)
            for col_i in range(3):
                idx = row_i * 3 + col_i
                if idx < len(chart_images):
                    img_base64 = base64.b64encode(chart_images[idx].getvalue()).decode()
                    if idx == 2 or idx == 3:
                        # Pie charts smaller width
                        cols[col_i].markdown(
                            f'<img src="data:image/png;base64,{img_base64}" style="width:70%;display:block;margin:auto;">',
                            unsafe_allow_html=True)
                    else:
                        cols[col_i].markdown(
                            f'<img src="data:image/png;base64,{img_base64}" style="width:100%;">',
                            unsafe_allow_html=True)
else:
    st.info("يرجى تحميل ملف Excel لعرض البيانات.")

