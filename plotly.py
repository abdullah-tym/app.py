import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io # Import io for handling file-like objects

# === Setup ===
st.set_page_config(page_title="لوحة تحكم الفواتير", layout="wide", page_icon="📊")

# === Global Colors & Style ===
# These colors are used for KPIs and can be referenced for Plotly charts if needed
COLORS = {
    "primary": "#2A9D8F",  # Teal/Green
    "secondary": "#E76F51", # Orange-Red
    "accent": "#F4A261",   # Orange
    "purple": "#8E44AD",   # Purple
    "green": "#43AA8B",    # Darker Green
    "crimson": "#E63946",  # Red
    "bg": "#FFFFFF",       # White background for charts/KPIs
    "grid": "#E0E0E0",     # Light gray for grid lines (not directly used by Plotly default)
    "text": "#222222"      # Dark text
}

# === Custom CSS for dashboard elements ===
st.markdown(f"""
<style>
    /* Target Streamlit's main app view container for the background color */
    [data-testid="stAppViewContainer"] {{
        background-color: #f9f9f9; /* Lighter gray background */
    }}

    /* Main content area padding */
    .main .block-container {{
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }}

    /* Sidebar styling */
    .css-1d391kg {{ /* Streamlit sidebar container */
        background-color: #ffffff; /* White sidebar */
        border-right: 1px solid #e0e0e0;
        box-shadow: 2px 0 5px rgba(0,0,0,0.05);
    }}

    /* Header styling */
    h1, h2, h3, h4, h5, h6 {{
        color: #2c3e50; /* Dark blue-grey for headers */
        font-weight: 600;
    }}

    /* Custom KPI box styling */
    .kpi-box {{
        border-radius: 10px;
        padding: 10px 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: flex-end; /* Align text to the end (right for RTL) */
        height: 110px; /* Fixed height for all KPIs to ensure uniformity */
        text-align: right;
        box-sizing: border-box;
        overflow: hidden;
    }}

    .kpi-label {{
        font-size: 0.9rem;
        color: #555555;
        font-weight: 500;
        margin-bottom: 2px;
        line-height: 1.2;
    }}

    .kpi-value {{
        font-size: 1.8rem; /* Adjusted for better visibility */
        font-weight: 700;
        color: #2c3e50;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }}

    /* Specific KPI background colors */
    .kpi-total-invoice {{
        background-color: #e0f2f7; /* Light blue */
        border-left: 5px solid #007bff; /* Blue accent */
    }}
    .kpi-total-paid {{
        background-color: #e6ffe6; /* Light green */
        border-left: 5px solid #28a745; /* Green accent */
    }}
    .kpi-outstanding {{
        background-color: #fff3e0; /* Light orange */
        border-left: 5px solid #ffc107; /* Orange accent */
    }}
    .kpi-overdue-count {{
        background-color: #ffe6e6; /* Light red */
        border-left: 5px solid #dc3545; /* Red accent */
    }}
    .kpi-avg-overdue {{
        background-color: #fff8e1; /* Amber */
        border-left: 5px solid #ff9800; /* Amber accent */
    }}
    .kpi-payment-rate {{
        background-color: #e0f7fa; /* Light teal */
        border-left: 5px solid #17a2b8; /* Teal accent */
    }}

    /* Chart container styling for Plotly charts */
    .stPlotlyChart {{
        border-radius: 10px;
        background-color: #ffffff; /* White background for charts */
        box-shadow: 0 0 15px rgba(0,0,0,0.15); /* Enhanced shadow on all sides */
        overflow: hidden; /* Ensures rounded corners apply to content */
        margin-bottom: 20px;
        padding: 15px; /* Add padding inside chart container for better spacing */
    }}

    /* Button styling */
    .stButton>button {{
        background-color: #3498db;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: background-color 0.3s ease;
    }}

    .stButton>button:hover {{
        background-color: #2980b9;
    }}

    /* Info/Warning messages */
    .stAlert {{
        border-radius: 8px;
    }}

    /* Checkbox styling */
    .stCheckbox > label {{
        font-weight: 500;
    }}

</style>
""", unsafe_allow_html=True)

# === Column name alternatives to detect from any file ===
COLUMN_MAP = {
    'invoice_amount': ['invoice_amount', 'amount', 'invoice total', 'مبلغ الفاتورة (ر.س)', 'invoice', 'total'],
    'paid_amount': ['paid_amount', 'amount_paid', 'payment', 'paid', 'المبلغ المدفوع (ر.س)'],
    'payment_status': ['payment_status', 'status', 'حالة الدفع', 'payment state', 'payment status'],
    'delay_days': ['delay_days', 'days_late', 'late days', 'أيام التأخير', 'delay'],
    'issue_date': ['issue_date', 'invoice_date', 'date', 'تاريخ الفاتورة', 'invoice date', 'date issued'],
    'due_date': ['due_date', 'due', 'due date', 'تاريخ الاستحقاق', 'payment due date'],
    'payment_date': ['payment_date', 'date_paid', 'تاريخ الدفع', 'payment date'],
    'client': ['client', 'customer', 'client name', 'اسم العميل', 'customer name'],
    'payment_method': ['payment_method', 'method', 'طريقة الدفع', 'payment type'],
    'invoice_no': ['invoice_no', 'invoice number', 'رقم الفاتورة', 'invoice id']
}

def find_column(df_cols, possible_names):
    """Find first matching column from possible_names in df_cols (case-insensitive)."""
    df_cols_lower = [c.lower() for c in df_cols]
    for name in possible_names:
        if name.lower() in df_cols_lower:
            return df_cols[df_cols_lower.index(name.lower())]
    return None

# --- Data Preprocessing Function ---
@st.cache_data
def load_and_preprocess_data(uploaded_file):
    """
    Loads raw invoice data from an uploaded file, preprocesses it, and returns a pandas DataFrame.
    Steps include:
    - Reading data based on file type (tab-separated for txt/csv, Excel for xlsx/xls).
    - Renaming columns to English for easier programmatic access.
    - Converting currency strings to float numbers.
    - Converting date strings to datetime objects.
    - Calculating 'Outstanding_Amount_SAR'.
    """
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension in ['csv', 'txt']:
            df = pd.read_csv(io.StringIO(uploaded_file.getvalue().decode("utf-8")), sep='\t')
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file)
        else:
            st.error("نوع الملف غير مدعوم. يرجى تحميل ملف CSV/TXT أو Excel.")
            return pd.DataFrame(), {} # Return empty DataFrame and empty detected_cols

        # Find actual columns in uploaded df
        cols = df.columns.tolist()
        detected_cols = {}
        for key, names in COLUMN_MAP.items():
            detected_cols[key] = find_column(cols, names)

        # Convert currency columns from string (e.g., "SAR 35,830") to float
        for col_key in ['invoice_amount', 'paid_amount']:
            col_name = detected_cols.get(col_key)
            if col_name and col_name in df.columns:
                df[col_name] = df[col_name].astype(str).str.replace('SAR', '').str.replace(',', '').astype(float)

        # Convert date columns to datetime objects, coercing errors to NaT (Not a Time)
        date_cols_keys = ['issue_date', 'due_date', 'payment_date']
        for col_key in date_cols_keys:
            col_name = detected_cols.get(col_key)
            if col_name and col_name in df.columns:
                df[col_name] = pd.to_datetime(df[col_name], errors='coerce')

        # Calculate the outstanding amount if both invoice_amount and paid_amount are available
        if detected_cols.get('invoice_amount') and detected_cols.get('paid_amount'):
            df['Outstanding_Amount_SAR'] = df[detected_cols['invoice_amount']] - df[detected_cols['paid_amount']]
        else:
            df['Outstanding_Amount_SAR'] = 0 # Default to 0 if columns are missing

        return df, detected_cols
    else:
        return pd.DataFrame(), {} # Return empty DataFrame and empty detected_cols

# === File Upload ===
uploaded_file = st.sidebar.file_uploader(
    "⬆️ حمّل ملف Excel الخاص بالفواتير (ملف نصي مفصول بعلامات جدولة أو ملف Excel)",
    type=["txt", "csv", "xlsx", "xls"]
)

df, detected_cols = load_and_preprocess_data(uploaded_file)

# Check if DataFrame is empty (no file uploaded or empty file)
if df.empty and uploaded_file is None:
    st.info("الرجاء تحميل ملف بيانات الفواتير لعرض لوحة التحكم.")
    st.stop()

# Helper to check if a column is available
def has_col(key):
    return detected_cols.get(key) in df.columns and detected_cols.get(key) is not None

# === Sidebar Filters Section ===
st.sidebar.header("تصفية البيانات")

# Get unique sorted values for filters
def get_unique_sorted(key):
    col = detected_cols.get(key)
    if col and col in df.columns:
        return sorted(df[col].dropna().unique().tolist())
    return []

# Initialize or reset filters in session state
if 'filters_initialized' not in st.session_state or st.sidebar.button("🔄 إعادة تعيين الفلاتر"):
    st.session_state.client_filter = get_unique_sorted('client')
    st.session_state.payment_status_filter = get_unique_sorted('payment_status')
    st.session_state.payment_method_filter = get_unique_sorted('payment_method')

    # Date ranges
    for dcol_key in ['issue_date', 'due_date']:
        col_name = detected_cols.get(dcol_key)
        if col_name and col_name in df.columns and not df[col_name].empty:
            st.session_state[f"{dcol_key}_range"] = (df[col_name].min().date(), df[col_name].max().date())
        else:
            st.session_state[f"{dcol_key}_range"] = (datetime.now().date(), datetime.now().date())

    # Delay days range
    delay_col = detected_cols.get('delay_days')
    if delay_col and delay_col in df.columns and not df[delay_col].empty:
        st.session_state.delay_days_range = (int(df[delay_col].min()), int(df[delay_col].max()))
    else:
        st.session_state.delay_days_range = (0, 0)

    st.session_state.filters_initialized = True

# Filter widgets with safe defaults (only options that exist)
client_options = get_unique_sorted('client')
payment_status_options = get_unique_sorted('payment_status')
payment_method_options = get_unique_sorted('payment_method')

# --- MODIFIED SECTION ---
# No need for safe_default_filter here, as session state is already initialized
# and the widget will read from st.session_state[key] automatically.
client_filter = st.sidebar.multiselect(
    "اسم العميل",
    client_options,
    key="client_filter" # Streamlit will use st.session_state.client_filter
)

payment_status_filter = st.sidebar.multiselect(
    "حالة الدفع",
    payment_status_options,
    key="payment_status_filter" # Streamlit will use st.session_state.payment_status_filter
)

payment_method_filter = st.sidebar.multiselect(
    "طريقة الدفع",
    payment_method_options,
    key="payment_method_filter" # Streamlit will use st.session_state.payment_method_filter
)
# --- END MODIFIED SECTION ---

# Date filters
issue_date_col = detected_cols.get('issue_date')
if issue_date_col and issue_date_col in df.columns and not df[issue_date_col].empty:
    min_issue_date = df[issue_date_col].min().date()
    max_issue_date = df[issue_date_col].max().date()
    issue_date_range = st.sidebar.date_input(
        "تاريخ الفاتورة (النطاق)",
        value=(st.session_state.issue_date_range[0], st.session_state.issue_date_range[1]),
        min_value=min_issue_date,
        max_value=max_issue_date,
        key="issue_date_range"
    )
else:
    issue_date_range = (None, None)

due_date_col = detected_cols.get('due_date')
if due_date_col and due_date_col in df.columns and not df[due_date_col].empty:
    min_due_date = df[due_date_col].min().date()
    max_due_date = df[due_date_col].max().date()
    due_date_range = st.sidebar.date_input(
        "تاريخ الاستحقاق (النطاق)",
        value=(st.session_state.due_date_range[0], st.session_state.due_date_range[1]),
        min_value=min_due_date,
        max_value=max_due_date,
        key="due_date_range"
    )
else:
    due_date_range = (None, None)

# Delay days slider
delay_days_col = detected_cols.get('delay_days')
if delay_days_col and delay_days_col in df.columns and not df[delay_days_col].empty:
    delay_days_min_val = int(df[delay_days_col].min())
    delay_days_max_val = int(df[delay_days_col].max())
    delay_days_range = st.sidebar.slider(
        "عدد أيام التأخير",
        delay_days_min_val,
        delay_days_max_val,
        value=st.session_state.delay_days_range,
        key="delay_days_range"
    )
else:
    delay_days_range = (0, 0)


# Filter df with selected filters
filtered_df = df.copy()

if has_col('client') and client_filter:
    filtered_df = filtered_df[filtered_df[detected_cols['client']].isin(client_filter)]

if has_col('payment_status') and payment_status_filter:
    filtered_df = filtered_df[filtered_df[detected_cols['payment_status']].isin(payment_status_filter)]

if has_col('payment_method') and payment_method_filter:
    filtered_df = filtered_df[filtered_df[detected_cols['payment_method']].isin(payment_method_filter)]

if has_col('issue_date') and issue_date_range[0] is not None:
    filtered_df = filtered_df[
        (filtered_df[detected_cols['issue_date']].dt.date >= issue_date_range[0]) &
        (filtered_df[detected_cols['issue_date']].dt.date <= issue_date_range[1])
    ]

if has_col('due_date') and due_date_range[0] is not None:
    filtered_df = filtered_df[
        (filtered_df[detected_cols['due_date']].dt.date >= due_date_range[0]) &
        (filtered_df[detected_cols['due_date']].dt.date <= due_date_range[1])
    ]

if has_col('delay_days'):
    filtered_df = filtered_df[
        (filtered_df[detected_cols['delay_days']] >= delay_days_range[0]) &
        (filtered_df[detected_cols['delay_days']] <= delay_days_range[1])
    ]

# --- Main Dashboard Layout ---
# Added the Mojaz.App logo here
st.markdown(
    "<h1 style='text-align: center; font-size: 52px; color: #E76F51; margin-bottom: 0;'>Mojaz.App</h1>",
    unsafe_allow_html=True
)
# Centered main dashboard title
st.markdown(
    "<h1 style='text-align: center; color: #2c3e50;'>لوحة تحكم إدارة الفواتير 📊</h1>",
    unsafe_allow_html=True
)
st.markdown("---") # Horizontal line for visual separation

if filtered_df.empty:
    st.warning("⚠️ لا توجد بيانات تطابق الفلاتر المختارة.")
else:
    # Removed PDF Export Button and its logic

    # Show raw data toggle - Centered the checkbox label
    st.markdown(
        "<div style='text-align: center;'>",
        unsafe_allow_html=True
    )
    show_raw_data = st.checkbox("📋 إظهار البيانات الخام", value=False, key="show_raw_data_checkbox")
    st.markdown("</div>", unsafe_allow_html=True)

    if show_raw_data:
        st.subheader("البيانات الخام") # Subheader for the raw data table
        st.dataframe(filtered_df)
        st.markdown("---")

    # === KPIs - show 6 colorful KPIs or less if missing columns ===
    # Centered KPI section header
    st.markdown(
        "<h2 style='text-align: center; color: #2c3e50;'>المؤشرات الرئيسية للأداء (KPIs)</h2>",
        unsafe_allow_html=True
    )
    def render_kpi(value, label, color):
        return f"""
        <div class="kpi-box" style="background-color:{color}15; border-left:6px solid {color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{value}</div>
        </div>
        """

    kpis = []
    # KPI 1: Total Invoice Amount
    if has_col('invoice_amount'):
        total_invoices_amount = filtered_df[detected_cols['invoice_amount']].sum()
        kpis.append((f"{total_invoices_amount:,.0f} ﷼", "إجمالي مبلغ الفواتير", COLORS["primary"]))

    # KPI 2: Total Paid Amount
    total_paid_amount = 0 # Initialize for calculation below
    if has_col('paid_amount'):
        total_paid_amount = filtered_df[detected_cols['paid_amount']].sum()
        kpis.append((f"{total_paid_amount:,.0f} ﷼", "إجمالي المبلغ المدفوع", COLORS["green"]))

    # KPI 3: Total Outstanding
    if has_col('invoice_amount') and has_col('paid_amount'):
        total_outstanding = total_invoices_amount - total_paid_amount
        kpis.append((f"{total_outstanding:,.0f} ﷼", "إجمالي المتبقي", COLORS["crimson"]))

    # KPI 4: Paid Invoices Count
    if has_col('payment_status'):
        paid_invoices_count = filtered_df[filtered_df[detected_cols['payment_status']] == 'مدفوع'].shape[0]
        kpis.append((f"{paid_invoices_count}", "عدد الفواتير المدفوعة بالكامل", COLORS["accent"]))

    # KPI 5: Late Invoices Count
    if has_col('delay_days'):
        late_invoices_count = filtered_df[filtered_df[detected_cols['delay_days']] > 0].shape[0]
        kpis.append((f"{late_invoices_count}", "عدد الفواتير المتأخرة", COLORS["purple"]))

    # KPI 6: Average Delay Days
    if has_col('delay_days'):
        avg_delay_days = filtered_df.loc[filtered_df[detected_cols['delay_days']] > 0, detected_cols['delay_days']].mean()
        # Handle NaN if no overdue invoices
        avg_delay_days_str = f"{avg_delay_days:,.0f} يوم" if not pd.isna(avg_delay_days) else "0 يوم"
        kpis.append((avg_delay_days_str, "متوسط أيام التأخير", COLORS["secondary"]))

    cols = st.columns(6)
    for i, col in enumerate(cols):
        if i < len(kpis):
            val, lbl, clr = kpis[i]
            col.markdown(render_kpi(val, lbl, clr), unsafe_allow_html=True)
        else:
            # Render empty KPI boxes if less than 6 KPIs are available
            col.markdown(f"""
                <div class="kpi-box" style="background-color:#eee; border-left:6px solid #ccc;">
                    <div class="kpi-label"></div>
                    <div class="kpi-value"></div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # === Charts ===
    # Centered Charts section header
    st.markdown(
        "<h2 style='text-align: center; color: #2c3e50;'>الرسوم البيانية</h2>",
        unsafe_allow_html=True
    )

    # Create two rows for charts, with 3 columns each
    chart_row1_col1, chart_row1_col2, chart_row1_col3 = st.columns(3)
    chart_row2_col1, chart_row2_col2, chart_row2_col3 = st.columns(3)
    chart_row3_col1, chart_row3_col2, chart_row3_col3 = st.columns(3) # For 9 charts total

    # Helper to get col name or None
    def c(key):
        return detected_cols.get(key)

    # Chart 1: Invoice Amount by Client (Bar Chart)
    with chart_row1_col1:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>مبلغ الفاتورة حسب العميل</h3>",
            unsafe_allow_html=True
        )
        if has_col('client') and has_col('invoice_amount'):
            client_invoice_amount = filtered_df.groupby(c('client'))[c('invoice_amount')].sum().reset_index()
            fig1 = px.bar(client_invoice_amount, x=c('client'), y=c('invoice_amount'),
                          title='إجمالي مبلغ الفاتورة لكل عميل',
                          labels={c('client'): 'اسم العميل', c('invoice_amount'): 'مبلغ الفاتورة (ر.س)'},
                          color=c('invoice_amount'),
                          color_continuous_scale=px.colors.sequential.Plasma,
                          template="plotly_white")
            fig1.update_layout(title_x=0.5) # Center Plotly chart title
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("البيانات غير كافية لإنشاء مخطط مبلغ الفاتورة حسب العميل.")

# ... (previous code) ...

    # Chart 2: Payment Status Distribution (Pie Chart)
    with chart_row1_col2:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>توزيع حالة الدفع</h3>",
            unsafe_allow_html=True
        )
        if has_col('payment_status'):
            payment_status_counts = filtered_df[c('payment_status')].value_counts().reset_index()
            payment_status_counts.columns = ['Payment_Status', 'Count']
            fig2 = px.pie(payment_status_counts, values='Count', names='Payment_Status',
                          title='توزيع الفواتير حسب حالة الدفع',
                          hole=0.3,
                          color_discrete_sequence=px.colors.sequential.RdBu,
                          template="plotly_white")
            fig2.update_layout(
                title_x=0.5, # Center Plotly chart title
                # --- START OF FIX ---
                # Position the legend at the bottom center
                legend=dict(
                    orientation="h", # Horizontal orientation
                    yanchor="bottom", # Anchor legend to the bottom of the chart
                    y=-0.2, # Adjust this value to control space below the chart
                    xanchor="center", # Center horizontally
                    x=0.5 # Center horizontally
                )
                # --- END OF FIX ---
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("البيانات غير كافية لإنشاء مخطط توزيع حالة الدفع.")

# ... (rest of the code) ...

    # Chart 3: Invoice Amount over Time (Monthly Line Chart)
    with chart_row1_col3:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>مبلغ الفاتورة بمرور الوقت (شهرياً)</h3>",
            unsafe_allow_html=True
        )
        if has_col('issue_date') and has_col('invoice_amount'):
            df_for_chart = filtered_df.copy()
            df_for_chart['Invoice_Month_Year'] = df_for_chart[c('issue_date')].dt.to_period('M').astype(str)
            monthly_invoice_amount = df_for_chart.groupby('Invoice_Month_Year')[c('invoice_amount')].sum().reset_index()
            fig3 = px.line(monthly_invoice_amount, x='Invoice_Month_Year', y=c('invoice_amount'),
                           title='إجمالي مبلغ الفواتير شهرياً',
                           labels={'Invoice_Month_Year': 'الشهر والسنة', c('invoice_amount'): 'مبلغ الفاتورة (ر.س)'},
                           markers=True,
                           line_shape="spline",
                           template="plotly_white")
            fig3.update_layout(title_x=0.5) # Center Plotly chart title
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("البيانات غير كافية لإنشاء مخطط مبلغ الفاتورة بمرور الوقت.")

    # Chart 4: Outstanding Amount by Client (Bar Chart)
    with chart_row2_col1:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>المبلغ المستحق حسب العميل</h3>",
            unsafe_allow_html=True
        )
        if has_col('client') and 'Outstanding_Amount_SAR' in filtered_df.columns:
            client_outstanding_amount = filtered_df.groupby(c('client'))['Outstanding_Amount_SAR'].sum().reset_index()
            fig4 = px.bar(client_outstanding_amount, x=c('client'), y='Outstanding_Amount_SAR',
                          title='إجمالي المبلغ المستحق لكل عميل',
                          labels={c('client'): 'اسم العميل', 'Outstanding_Amount_SAR': 'المبلغ المستحق (ر.س)'},
                          color='Outstanding_Amount_SAR',
                          color_continuous_scale=px.colors.sequential.Viridis,
                          template="plotly_white")
            fig4.update_layout(title_x=0.5) # Center Plotly chart title
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("البيانات غير كافية لإنشاء مخطط المبلغ المستحق حسب العميل.")

# ... (previous code) ...

    # Chart 5: Payment Method Distribution (Pie Chart)
    with chart_row2_col2:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>توزيع طريقة الدفع</h3>",
            unsafe_allow_html=True
        )
        if has_col('payment_method'):
            payment_method_counts = filtered_df[c('payment_method')].value_counts().reset_index()
            payment_method_counts.columns = ['Payment_Method', 'Count']
            fig5 = px.pie(payment_method_counts, values='Count', names='Payment_Method',
                          title='توزيع الفواتير حسب طريقة الدفع',
                          hole=0.3,
                          color_discrete_sequence=px.colors.sequential.Aggrnyl,
                          template="plotly_white")
            fig5.update_layout(
                title_x=0.5, # Center Plotly chart title
                # --- START OF FIX ---
                # Position the legend at the bottom center
                legend=dict(
                    orientation="h", # Horizontal orientation
                    yanchor="bottom", # Anchor legend to the bottom of the chart
                    y=-0.2, # Adjust this value to control space below the chart
                    xanchor="center", # Center horizontally
                    x=0.5 # Center horizontally
                )
                # --- END OF FIX ---
            )
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("البيانات غير كافية لإنشاء مخطط توزيع طريقة الدفع.")

# ... (rest of the code) ...

    # Chart 6: Days Overdue Distribution (Histogram for overdue invoices only)
    with chart_row2_col3:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>توزيع أيام التأخير</h3>",
            unsafe_allow_html=True
        )
        if has_col('delay_days'):
            overdue_invoices_df = filtered_df[
                ((filtered_df[c('payment_status')] == 'متأخر') |
                 (filtered_df[c('payment_status')] == 'مدفوع جزئياً')) &
                (filtered_df[c('delay_days')] > 0)
            ].copy()
            if not overdue_invoices_df.empty:
                fig6 = px.histogram(overdue_invoices_df, x=c('delay_days'),
                                     title='توزيع أيام التأخير للفواتير المتأخرة',
                                     labels={c('delay_days'): 'عدد أيام التأخير'},
                                     nbins=15,
                                     color_discrete_sequence=['#FF6347'],
                                     template="plotly_white")
                fig6.update_layout(title_x=0.5) # Center Plotly chart title
                st.plotly_chart(fig6, use_container_width=True)
            else:
                st.info("لا توجد فواتير متأخرة لعرض توزيع أيام التأخير.")
        else:
            st.info("البيانات غير كافية لإنشاء مخطط توزيع أيام التأخير.")

    # Chart 7: Invoice Count per Month (bar)
    with chart_row3_col1:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>عدد الفواتير شهرياً</h3>",
            unsafe_allow_html=True
        )
        if has_col('issue_date'):
            df_for_chart = filtered_df.copy()
            df_for_chart['Issue_Month'] = df_for_chart[c('issue_date')].dt.to_period('M').astype(str)
            invoice_count = df_for_chart.groupby('Issue_Month').size().reset_index(name='Count')
            fig7 = px.bar(invoice_count, x='Issue_Month', y='Count',
                          title='عدد الفواتير شهرياً',
                          labels={'Issue_Month': 'الشهر والسنة', 'Count': 'عدد الفواتير'},
                          color_discrete_sequence=[COLORS['purple']],
                          template="plotly_white")
            fig7.update_layout(title_x=0.5) # Center Plotly chart title
            st.plotly_chart(fig7, use_container_width=True)
        else:
            st.info("البيانات غير كافية لإنشاء مخطط عدد الفواتير شهرياً.")

    # Chart 8: Paid Amount Trend (line)
    with chart_row3_col2:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>اتجاه المبالغ المدفوعة شهرياً</h3>",
            unsafe_allow_html=True
        )
        if has_col('payment_date') and has_col('paid_amount'):
            df_for_chart = filtered_df.copy()
            df_for_chart['Pay_Month'] = df_for_chart[c('payment_date')].dt.to_period('M').astype(str)
            paid_monthly = df_for_chart.groupby('Pay_Month')[c('paid_amount')].sum().reset_index()
            fig8 = px.line(paid_monthly, x='Pay_Month', y=c('paid_amount'),
                           title='اتجاه المبالغ المدفوعة شهرياً',
                           labels={'Pay_Month': 'الشهر والسنة', c('paid_amount'): 'المبلغ المدفوع (ر.س)'},
                           markers=True,
                           line_shape="spline",
                           color_discrete_sequence=[COLORS['primary']],
                           template="plotly_white")
            fig8.update_layout(title_x=0.5) # Center Plotly chart title
            st.plotly_chart(fig8, use_container_width=True)
        else:
            st.info("البيانات غير كافية لإنشاء مخطط اتجاه المبالغ المدفوعة.")

    # Chart 9: Outstanding by Payment Method (bar)
    with chart_row3_col3:
        # Centered subheader
        st.markdown(
            "<h3 style='text-align: center;'>المبالغ المتبقية حسب طريقة الدفع</h3>",
            unsafe_allow_html=True
        )
        if has_col('invoice_amount') and has_col('paid_amount') and has_col('payment_method'):
            df_for_chart = filtered_df.copy()
            df_for_chart['outstanding'] = df_for_chart[c('invoice_amount')] - df_for_chart[c('paid_amount')]
            outstanding_by_method = df_for_chart.groupby(c('payment_method'))['outstanding'].sum().reset_index()
            fig9 = px.bar(outstanding_by_method, x=c('payment_method'), y='outstanding',
                          title='المبالغ المتبقية حسب طريقة الدفع',
                          labels={c('payment_method'): 'طريقة الدفع', 'outstanding': 'المبلغ المتبقي (ر.س)'},
                          color='outstanding',
                          color_continuous_scale=px.colors.sequential.Aggrnyl,
                          template="plotly_white")
            fig9.update_layout(title_x=0.5) # Center Plotly chart title
            st.plotly_chart(fig9, use_container_width=True)
        else:
            st.info("ال بيانات غير كافية لإنشاء مخطط المبالغ المتبقية حسب طريقة الدفع.")

st.markdown("---") # Horizontal line for visual separation

st.markdown("<div style='text-align: center;'>Mojaz.App تم إنشاء هذه اللوحة التفاعلية عبر منصة تطبيق موجز لذكاء الاعمال</div>", unsafe_allow_html=True)
