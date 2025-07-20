import streamlit as st
import pandas as pd
import qrcode
import base64
from fpdf import FPDF
from datetime import datetime
from io import BytesIO
from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display
import os

# --- Config ---
VAT_RATE = 0.15
CURRENCY = "SAR"
FONT_PATH = "Amiri-Regular.ttf" # Ensure this font file is in the same directory as your script

# --- Arabic Text Helpers ---
reshaper = ArabicReshaper({'delete_harakat': False, 'support_ligatures': True})

def get_arabic_display_pdf(text):
    """Reshapes and reorders Arabic text for proper display in FPDF and direct Streamlit widget labels."""
    if text:
        return get_display(reshaper.reshape(text))
    return ""

def get_tlv_data(seller_name, vat_number, invoice_total, vat_total, timestamp):
    def to_bytes(val):
        # If val is already bytes or bytearray, convert to bytes directly
        if isinstance(val, (bytes, bytearray)):
            return bytes(val)
        # Otherwise, convert to string then encode to bytes
        return str(val).encode('utf-8')
    
    seller_name_bytes = to_bytes(seller_name)
    vat_number_bytes = to_bytes(vat_number)
    timestamp_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
    timestamp_bytes = to_bytes(timestamp_str)
    invoice_total_bytes = to_bytes(f"{invoice_total:.2f}")
    vat_total_bytes = to_bytes(f"{vat_total:.2f}")

    tlv_values = [
        (1, seller_name_bytes),
        (2, vat_number_bytes),
        (3, timestamp_bytes),
        (4, invoice_total_bytes),
        (5, vat_total_bytes)
    ]

    tlv_string = b''
    for tag, value in tlv_values:
        tlv_string += tag.to_bytes(1, 'big')
        tlv_string += len(value).to_bytes(1, 'big')
        tlv_string += value

    return base64.b64encode(tlv_string).decode('utf-8')


# --- PDF class ---
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        if os.path.exists(FONT_PATH):
            self.add_font('Amiri', '', FONT_PATH, uni=True)
            self.set_font('Amiri', '', 12)
        else:
            self.set_font('Arial', '', 12)

    def header(self):
        self.set_font('Amiri' if os.path.exists(FONT_PATH) else 'Arial', '', 20)
        self.cell(0, 10, get_arabic_display_pdf("فاتورة ضريبية"), 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Amiri' if os.path.exists(FONT_PATH) else 'Arial', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_invoice_pdf(invoice_data, user_business_info, qr_img_base64):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font('Amiri' if os.path.exists(FONT_PATH) else 'Arial', '', 12)
    pdf.cell(0, 7, get_arabic_display_pdf(f"اسم العمل: {user_business_info.get('name', 'N/A')}"), 0, 1, 'R')
    pdf.cell(0, 7, get_arabic_display_pdf(f"الرقم الضريبي: {user_business_info.get('vat_number', 'N/A')}"), 0, 1, 'R')
    pdf.ln(5)

    pdf.cell(0, 7, get_arabic_display_pdf(f"اسم العميل: {invoice_data['client_name']}"), 0, 1, 'R')
    pdf.cell(0, 7, get_arabic_display_pdf(f"رقم الفاتورة: {invoice_data['invoice_number']}"), 0, 1, 'R')
    pdf.cell(0, 7, get_arabic_display_pdf(f"تاريخ الفاتورة: {invoice_data['invoice_date'].strftime('%Y-%m-%d')}"), 0, 1, 'R')
    pdf.ln(10)

    col_widths = [80, 30, 40, 40]
    headers = [
        get_arabic_display_pdf("الإجمالي (ريال)"),
        get_arabic_display_pdf("سعر الوحدة (ريال)"),
        get_arabic_display_pdf("الكمية"),
        get_arabic_display_pdf("الوصف")
    ]
    for i in range(len(headers)-1, -1, -1):
        pdf.cell(col_widths[i], 10, headers[i], 1, 0, 'C')
    pdf.ln()

    for item in invoice_data['items']:
        pdf.cell(col_widths[3], 8, get_arabic_display_pdf(item['description']), 1, 0, 'R')
        pdf.cell(col_widths[2], 8, str(item['quantity']), 1, 0, 'C')
        pdf.cell(col_widths[1], 8, f"{item['unit_price']:.2f}", 1, 0, 'C')
        pdf.cell(col_widths[0], 8, f"{item['total']:.2f}", 1, 0, 'C')
        pdf.ln()

    pdf.ln(10)
    pdf.cell(0, 7, get_arabic_display_pdf(f"المجموع الفرعي: {invoice_data['subtotal']:.2f} {CURRENCY}"), 0, 1, 'R')
    pdf.cell(0, 7, get_arabic_display_pdf(f"ضريبة القيمة المضافة (15%): {invoice_data['vat_amount']:.2f} {CURRENCY}"), 0, 1, 'R')
    pdf.cell(0, 7, get_arabic_display_pdf(f"المجموع الكلي: {invoice_data['total_with_vat']:.2f} {CURRENCY}"), 0, 1, 'R')
    pdf.ln(10)

    if qr_img_base64:
        try:
            qr_img_bytes = base64.b64decode(qr_img_base64)
            qr_img_io = BytesIO(qr_img_bytes)
            # Ensure QR code position is within bounds, adjusting if necessary
            qr_x = pdf.w - 50 if pdf.w - 50 > 0 else 10 # Prevent negative x
            qr_y = pdf.h - 50 if pdf.h - 50 > 0 else 10 # Prevent negative y
            pdf.image(qr_img_io, x=qr_x, y=qr_y, w=30)
            pdf.text(qr_x, qr_y - 5, get_arabic_display_pdf("رمز الاستجابة السريعة (QR)"))
        except Exception as e:
            print(f"QR code embedding failed: {e}")

    return pdf.output(dest='S')

# --- Streamlit app ---

# Custom CSS for a sexy and fancy design
st.markdown("""
<style>
    /* General Styling */
    .stApp {
        background-color: #f0f2f6; /* Light gray background */
        color: #333333; /* Dark gray text */
        font-family: 'Amiri', 'Arial', sans-serif;
    }

    /* Sidebar Styling */
    .st-emotion-cache-1na6mxx { /* This targets the sidebar content */
        background-color: #1e3a8a; /* Dark blue */
        color: white;
        padding-top: 20px;
    }
    .st-emotion-cache-10o1aek { /* This targets the sidebar header text */
        color: white;
        font-size: 24px;
        text-align: center;
        margin-bottom: 30px;
        font-weight: bold;
    }
    .st-emotion-cache-1kyxyej { /* Radio button labels in sidebar */
        color: white !important;
        font-size: 18px;
        margin-bottom: 10px;
    }
    .st-emotion-cache-1kyxyej:hover {
        color: #e0f2f7 !important; /* Lighter blue on hover */
    }
    .st-emotion-cache-j7qwjs { /* Selected radio button in sidebar */
        background-color: #3b82f6; /* Medium blue */
        border-radius: 8px;
        padding: 8px 15px;
        margin: 5px 0;
    }

    /* Main Content Area */
    .st-emotion-cache-z5fcl4 { /* Main content area padding */
        padding-top: 30px;
        padding-bottom: 30px;
        padding-left: 5%;
        padding-right: 5%;
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6, .st-emotion-cache-1q3n90n { /* Added .st-emotion-cache-1q3n90n for st.header, st.subheader, st.title */
        color: #1e3a8a; /* Dark blue for headers */
        font-weight: bold;
        text-align: right; /* RTL alignment for headers */
        margin-bottom: 15px;
    }
    /* Specific adjustment for st.header, st.subheader, st.title which often render as span inside div */
    div[data-testid="stHeader"] > div > h1,
    div[data-testid="stSubheader"] > div > h2,
    div[data-testid="stTitle"] > div > h1 {
        text-align: right;
        direction: rtl; /* Ensure RTL */
    }


    /* Buttons */
    .stButton > button {
        background-color: #3b82f6; /* Medium blue */
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s ease;
        float: right; /* Align buttons to the right */
        margin-right: 10px; /* Spacing between buttons if multiple */
    }
    .stButton > button:hover {
        background-color: #1d4ed8; /* Darker blue on hover */
        color: white;
        border-color: #1d4ed8;
    }
    .stDownloadButton > button {
        background-color: #059669; /* Green for download */
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s ease;
        float: right;
        margin-right: 10px;
    }
    .stDownloadButton > button:hover {
        background-color: #047857; /* Darker green on hover */
        color: white;
        border-color: #047857;
    }

    /* Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > select,
    .stRadio > div > label > div {
        border-radius: 8px;
        border: 1px solid #d1d5db; /* Light gray border */
        padding: 8px 12px;
        text-align: right; /* RTL for text input */
        direction: rtl; /* Ensure RTL input */
    }
    .stTextInput > label,
    .stNumberInput > label,
    .stDateInput > label,
    .stSelectbox > label,
    .stRadio > label {
        text-align: right; /* Align labels to the right */
        width: 100%;
        display: block;
        color: #1e3a8a; /* Dark blue for labels */
        font-weight: bold;
        margin-bottom: 5px;
    }

    /* Form specific styling */
    .stForm {
        background-color: white;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); /* Soft shadow */
    }
    .stForm .stButton > button {
        width: auto; /* Allow submit button to size itself */
        margin-top: 20px;
    }

    /* Dataframe Styling */
    .stDataFrame {
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        overflow: hidden; /* Ensures border-radius applies to corners */
    }

    /* Info/Success/Warning/Error messages */
    .st-emotion-cache-vdgyx8 { /* Target for success messages */
        background-color: #d1fae5; /* Light green */
        color: #065f46; /* Dark green */
        border-color: #34d399;
        border-radius: 8px;
        padding: 15px;
        text-align: right;
    }
    .st-emotion-cache-10trblm { /* Target for info messages */
        background-color: #e0f2f7; /* Light blue */
        color: #0c4a6e; /* Dark blue */
        border-color: #7dd3fc;
        border-radius: 8px;
        padding: 15px;
        text-align: right;
    }
    .st-emotion-cache-t3w09j { /* Target for error messages */
        background-color: #fee2e2; /* Light red */
        color: #991b1b; /* Dark red */
        border-color: #ef4444;
        border-radius: 8px;
        padding: 15px;
        text-align: right;
    }

    /* Card-like display for dashboard metrics */
    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        text-align: center;
        margin-bottom: 20px;
        border-top: 4px solid #3b82f6; /* Highlight border */
    }
    div[data-testid="stMetric"] label div {
        font-size: 18px;
        color: #1e3a8a;
        font-weight: bold;
    }
    div[data-testid="stMetric"] div[data-testid="stMarkdownContainer"] p {
        font-size: 28px !important;
        font-weight: bold;
        color: #059669; /* Green for monetary values */
    }

    /* Custom styling for invoice item rows in 'create invoice' */
    .invoice-item-row {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
    }
    .invoice-item-row .stTextInput, .invoice-item-row .stNumberInput {
        margin-bottom: 0 !important; /* Remove default margin */
    }
    .invoice-item-row .stButton {
        margin-top: 0 !important;
    }
    .invoice-item-row .stButton > button {
        float: none; /* Override float for row alignment */
        margin-right: 0;
    }
    /* Markdown for total summary */
    .st-emotion-cache-1k46j0x { /* This is a common class for markdown blocks */
        direction: rtl; 
        text-align: right; 
        margin-top: 20px; 
        padding: 10px; 
        background-color: #f8f9fa; 
        border-radius: 8px; 
        border: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)


st.set_page_config(layout="wide", page_title="نظام الفواتير السعودي")

if 'invoices' not in st.session_state:
    st.session_state.invoices = []
if 'user_business_info' not in st.session_state:
    st.session_state.user_business_info = {
        'name': 'اسم شركتك',
        'vat_number': '300000000000003'
    }
if 'invoice_items' not in st.session_state:
    st.session_state.invoice_items = [{'description': '', 'quantity': 1, 'unit_price': 0.0}]

if not os.path.exists(FONT_PATH):
    st.warning(f"Font file {FONT_PATH} missing. Arabic PDF text may not render correctly.")

def main():
    st.sidebar.title("القائمة الرئيسية")
    menu = ["إنشاء فاتورة جديدة", "لوحة التحكم بالفواتير", "إعدادات المستخدم"]
    choice = st.sidebar.radio("اختر", menu)

    if choice == "إنشاء فاتورة جديدة":
        create_invoice_page()
    elif choice == "لوحة التحكم بالفواتير":
        dashboard_page()
    else:
        settings_page()

def create_invoice_page():
    st.header("إنشاء فاتورة جديدة")

    # Invoice items inputs
    st.subheader("بنود الفاتورة")

    for i, item in enumerate(st.session_state.invoice_items):
        cols = st.columns([4, 1, 2, 1])
        with cols[0]:
            item['description'] = st.text_input(f"الوصف #{i+1}", value=item['description'], key=f"desc_{i}")
        with cols[1]:
            item['quantity'] = st.number_input(f"الكمية #{i+1}", min_value=1, value=item['quantity'], key=f"qty_{i}")
        with cols[2]:
            item['unit_price'] = st.number_input(f"سعر الوحدة #{i+1}", min_value=0.0, value=item['unit_price'], key=f"price_{i}")
        with cols[3]:
            if st.button(f"حذف #{i+1}", key=f"delete_{i}"):
                st.session_state.invoice_items.pop(i)
                st.rerun()

    if st.button("إضافة بند جديد"):
        st.session_state.invoice_items.append({'description': '', 'quantity': 1, 'unit_price': 0.0})
        st.rerun()

    with st.form("invoice_form"):
        client_name = st.text_input("اسم العميل")
        invoice_number = st.text_input("رقم الفاتورة", value=f"INV-{len(st.session_state.invoices)+1:04d}")
        invoice_date = st.date_input("تاريخ الفاتورة", value=datetime.today())

        subtotal = sum(item['quantity'] * item['unit_price'] for item in st.session_state.invoice_items)
        vat_amount = subtotal * VAT_RATE
        total_with_vat = subtotal + vat_amount

        # Changed to markdown for direct styling from CSS, retaining original Arabic logic
        st.markdown(f"**الإجمالي الفرعي:** {subtotal:.2f} {CURRENCY}")
        st.markdown(f"**ضريبة القيمة المضافة (15%):** {vat_amount:.2f} {CURRENCY}")
        st.markdown(f"## المجموع الكلي: {total_with_vat:.2f} {CURRENCY}")


        submitted = st.form_submit_button("إنشاء الفاتورة")

        if submitted:
            if not client_name or not invoice_number or not st.session_state.invoice_items:
                st.error("الرجاء ملء جميع الحقول المطلوبة وإضافة بنود الفاتورة.")
                return

            invoice_items_calculated = []
            for item in st.session_state.invoice_items:
                invoice_items_calculated.append({
                    **item,
                    'total': item['quantity'] * item['unit_price']
                })

            invoice_timestamp = datetime.now()
            seller_name_for_qr = st.session_state.user_business_info.get('name', 'Seller Name')
            vat_number_for_qr = st.session_state.user_business_info.get('vat_number', '300000000000003')

            qr_data_string = get_tlv_data(
                seller_name_for_qr,
                vat_number_for_qr,
                total_with_vat,
                vat_amount,
                invoice_timestamp
            )

            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                               box_size=5, border=4)
            qr.add_data(qr_data_string)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")

            buffered = BytesIO()
            qr_img.save(buffered, format="PNG")
            qr_img_base64 = base64.b64encode(buffered.getvalue()).decode()

            invoice_data = {
                'client_name': client_name,
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,
                'items': invoice_items_calculated,
                'subtotal': subtotal,
                'vat_amount': vat_amount,
                'total_with_vat': total_with_vat,
                'qr_code_data': qr_data_string,
                'status': 'Unpaid',
                'timestamp': invoice_timestamp
            }

            st.session_state.invoices.append(invoice_data)
            st.success("تم إنشاء الفاتورة بنجاح!")

            pdf_bytes = generate_invoice_pdf(invoice_data, st.session_state.user_business_info, qr_img_base64)

            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.pdf_file_name = f"invoice_{invoice_number}.pdf"

            st.session_state.invoice_items = [{'description': '', 'quantity': 1, 'unit_price': 0.0}]

            st.session_state.pdf_ready = True
            st.session_state.pdf_data = bytes(pdf_bytes)
            st.session_state.pdf_filename = f"invoice_{invoice_number}.pdf"

    if st.session_state.get("pdf_ready"):
        st.download_button(
            label="تحميل الفاتورة PDF",
            data=st.session_state.pdf_data,
            file_name=st.session_state.pdf_filename,
            mime="application/pdf"
        )
        st.session_state.pdf_ready = False  # Reset so button only shows after submission



def dashboard_page():
    st.header("لوحة التحكم بالفواتير")

    if not st.session_state.invoices:
        st.info("لا توجد فواتير لعرضها بعد. ابدأ بإنشاء فاتورة جديدة!")
        return

    df = pd.DataFrame(st.session_state.invoices)
    total_sales = df['total_with_vat'].sum()
    total_vat_collected = df['vat_amount'].sum()
    unpaid_amounts = df[df['status'] == 'Unpaid']['total_with_vat'].sum()

    # Changed to st.metric for fancy display based on CSS
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="إجمالي المبيعات", value=f"{total_sales:.2f} {CURRENCY}")
    with col2:
        st.metric(label="إجمالي ضريبة القيمة المضافة المحصلة", value=f"{total_vat_collected:.2f} {CURRENCY}")
    with col3:
        st.metric(label="المبالغ غير المدفوعة", value=f"{unpaid_amounts:.2f} {CURRENCY}")
    
    st.markdown("---")

    search = st.text_input("البحث برقم الفاتورة أو اسم العميل")
    filtered_df = df

    if search:
        search = search.lower()
        filtered_df = df[
            df['invoice_number'].str.lower().str.contains(search) |
            df['client_name'].str.lower().str.contains(search)
        ]

    st.dataframe(filtered_df[['invoice_number', 'client_name', 'invoice_date', 'total_with_vat', 'status']])

def settings_page():
    st.header("إعدادات المستخدم")

    business_name = st.text_input("اسم العمل", value=st.session_state.user_business_info.get('name', ''))
    vat_number = st.text_input("الرقم الضريبي", value=st.session_state.user_business_info.get('vat_number', ''))

    if st.button("حفظ الإعدادات"):
        st.session_state.user_business_info['name'] = business_name
        st.session_state.user_business_info['vat_number'] = vat_number
        st.success("تم حفظ الإعدادات بنجاح!")

if __name__ == "__main__":
    if 'pdf_ready' not in st.session_state:
        st.session_state.pdf_ready = False
    main()
