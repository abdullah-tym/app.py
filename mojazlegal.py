import streamlit as st
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import tempfile
import pandas as pd

# Set page config at the very beginning
st.set_page_config(page_title="Mojaz Platform", layout="centered", initial_sidebar_state="collapsed")

# Custom CSS for Arabic font, spacing, and colors
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo&display=swap');

body, .block-container {
    font-family: 'Cairo', Tahoma, sans-serif !important;
    direction: rtl;
}

h1, h2, h3, h4 {
    color: #0d3b66;
    font-weight: 700;
    margin-bottom: 0.3em;
}

.stButton > button {
    background-color: #f4d35e;
    color: #0d3b66;
    font-weight: 700;
    border-radius: 8px;
    padding: 8px 20px;
    margin-top: 10px;
    transition: background-color 0.3s ease;
}
.stButton > button:hover {
    background-color: #ee964b;
    color: white;
}

section[data-testid="stForm"] {
    background-color: #f9f9f9;
    padding: 15px 20px;
    border-radius: 12px;
    margin-bottom: 25px;
}

div[data-testid="stMarkdownContainer"] p {
    margin-bottom: 0.5em;
}

.signature-container, .stamp-container {
    background-color: #e1e7f0;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 20px;
}

.label-bold {
    font-weight: 700;
    margin-bottom: 5px;
}

input[type="text"], input[type="number"], textarea, select {
    direction: rtl;
}

</style>
""", unsafe_allow_html=True)


# Create columns for centering the main content
# The middle column will contain your app, and side columns will be empty space
col_left, col_main, col_right = st.columns([1, 32, 1]) # Adjust ratios as needed for more/less empty space

with col_main: # All your main application content goes inside this 'with' block
    st.title("🧑‍⚖️ Mojaz Platform - 🧑‍⚖️ منصة موجز - لإدارة العقود وعمليات المحاماة")

    tab1, tab2 = st.tabs(["📄 MojazContracts", "⚖️ MojazLegalCRM"])

    with tab1:
        st.subheader("📄 مولد العقود القانونية")
        # --- Insert full MojazContracts code here ---

        st.title("📝 مولد العقود القانونية - MojazContracts")

        def reshape(text):
            return get_display(arabic_reshaper.reshape(text))

        contract_type = st.selectbox("اختر نوع العقد", [
            "عقد عمل",
            "عقد إيجار",
            "عقد وكالة",
            "عقد بيع",
            "عقد عدم إفشاء (NDA)"
        ])

        with st.form("contract_form"):
            st.subheader("📌 بيانات الأطراف")
            col1, col2 = st.columns(2)
            with col1:
                party1 = st.text_input("اسم الطرف الأول")
                party2 = st.text_input("اسم الطرف الثاني")
                date = st.date_input("تاريخ العقد", datetime.today()).strftime("%Y-%m-%d")
            with col2:
                st.write(" ")  # Just for spacing alignment

            extra = {}

            if contract_type == "عقد عمل":
                st.markdown("### تفاصيل عقد العمل")
                col1, col2 = st.columns(2)
                with col1:
                    extra["cr_number"] = st.text_input("السجل التجاري للطرف الأول")
                    extra["id_number"] = st.text_input("رقم هوية الطرف الثاني")
                    extra["salary"] = st.number_input("الراتب الشهري", 0.0)
                    extra["housing_allowance"] = st.checkbox("يشمل بدل سكن؟")
                    if extra["housing_allowance"]:
                        extra["housing_percentage"] = st.slider("نسبة بدل السكن", 10, 50, 25)
                    extra["non_compete"] = st.checkbox("إضافة شرط عدم المنافسة")
                    if extra["non_compete"]:
                        extra["non_compete_city"] = st.text_input("المدينة")
                with col2:
                    extra["address"] = st.text_input("عنوان الطرف الأول")
                    extra["job_title"] = st.text_input("المسمى الوظيفي")
                    extra["duration"] = st.number_input("مدة العقد (بالأشهر)", 1)
                    extra["start_date"] = st.date_input("تاريخ بدء العمل", datetime.today()).strftime("%Y-%m-%d")
                    extra["penalty_clause"] = st.checkbox("إضافة شرط جزائي")
                    if extra["penalty_clause"]:
                        extra["penalty_amount"] = st.number_input("قيمة الشرط الجزائي", 0.0)
                    extra["termination_clause"] = st.checkbox("إمكانية فسخ العقد بإشعار")

            elif contract_type == "عقد إيجار":
                extra["property_address"] = st.text_input("عنوان العقار")
                extra["duration"] = st.number_input("مدة الإيجار (أشهر)", 1)
                extra["rent"] = st.number_input("قيمة الإيجار الشهري", 0.0)
                extra["deposit"] = st.number_input("قيمة التأمين (إن وجد)", 0.0)
                extra["maintenance"] = st.checkbox("هل المؤجر مسؤول عن الصيانة؟")

            elif contract_type == "عقد وكالة":
                extra["agency_scope"] = st.text_area("نطاق الوكالة")
                extra["duration"] = st.number_input("مدة الوكالة (أشهر)", 1)

            elif contract_type == "عقد بيع":
                extra["item_description"] = st.text_area("وصف الأصل")
                extra["price"] = st.number_input("قيمة البيع", 0.0)
                extra["delivery_date"] = st.date_input("تاريخ التسليم", datetime.today()).strftime("%Y-%m-%d")

            elif contract_type == "عقد عدم إفشاء (NDA)":
                extra["duration"] = st.number_input("مدة الالتزام (أشهر)", 1)
                extra["scope"] = st.text_area("طبيعة المعلومات المشمولة")

            st.subheader("✍️ التوقيع")
            st.markdown('<div class="signature-container">', unsafe_allow_html=True)
            canvas_result = st_canvas(
                fill_color="#000000",
                stroke_width=2,
                stroke_color="#000000",
                background_color="#ffffff",
                height=150,
                drawing_mode="freedraw",
                key="canvas",
            )
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("📎 ختم الشركة")
            st.markdown('<div class="stamp-container">', unsafe_allow_html=True)
            stamp_file = st.file_uploader("رفع صورة الختم (PNG)", type=["png"])
            st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("📤 إرسال العقد")
            send_whatsapp = st.checkbox("إرسال عبر واتساب")
            whatsapp_number = st.text_input("رقم الجوال (بدون +966)") if send_whatsapp else None

            send_email = st.checkbox("إرسال عبر الإيميل")
            email_address = st.text_input("البريد الإلكتروني") if send_email else None

            submitted = st.form_submit_button("📄 توليد العقد")

        if submitted:
            if contract_type == "عقد عمل":
                text = f"""\
عقد عمل
بتاريخ {date}, تم الاتفاق بين:
الطرف الأول: {party1}، سجل تجاري {extra.get('cr_number', '')}، العنوان: {extra.get('address', '')}
الطرف الثاني: {party2}، هوية: {extra.get('id_number', '')}
الوظيفة: {extra.get('job_title', '')}, الراتب: {extra.get('salary', 0)} ريال، المدة: {extra.get('duration', 1)} شهرًا تبدأ في {extra.get('start_date', '')}.
"""
                if extra.get("housing_allowance"):
                    text += f"\nيشمل بدل سكن بنسبة {extra.get('housing_percentage', 0)}%."
                text += "\nالسرية مطلوبة."
                if extra.get("non_compete"):
                    text += f"\nعدم المنافسة داخل {extra.get('non_compete_city', '')} لمدة 6 أشهر."
                if extra.get("penalty_clause"):
                    text += f"\nالشرط الجزائي: {extra.get('penalty_amount', 0)} ريال."
                if extra.get("termination_clause"):
                    text += "\nفسخ العقد بإشعار كتابي قبل 30 يومًا."
                text += "\nخاضع لنظام العمل السعودي."

            elif contract_type == "عقد إيجار":
                text = f"عقد إيجار\nبتاريخ {date}, بين {party1} و {party2}. العقار: {extra.get('property_address', '')}, لمدة {extra.get('duration', 1)} شهرًا، إيجار شهري {extra.get('rent', 0)} ريال."
                text += "\nالصيانة على المؤجر." if extra.get("maintenance") else "\nالصيانة على المستأجر."

            elif contract_type == "عقد وكالة":
                text = f"عقد وكالة\nبتاريخ {date}, الموكل: {party1}, الوكيل: {party2}, المدة: {extra.get('duration', 1)} شهرًا. النطاق: {extra.get('agency_scope', '')}"

            elif contract_type == "عقد بيع":
                text = f"عقد بيع\nبتاريخ {date}, البائع: {party1}, المشتري: {party2}, الأصل: {extra.get('item_description', '')}, السعر: {extra.get('price', 0)}، التسليم: {extra.get('delivery_date', '')}"

            elif contract_type == "عقد عدم إفشاء (NDA)":
                text = f"عقد NDA\nبتاريخ {date}, بين {party1} و {party2}, لمدة {extra.get('duration', 1)} شهرًا. يشمل المعلومات: {extra.get('scope', '')}"

            reshaped = reshape(text)
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font("Arabic", "", "Amiri-Regular.ttf", uni=True)
            pdf.set_font("Arabic", size=14)

            for line in reshaped.split("\n"):
                pdf.cell(200, 10, txt=line.strip(), ln=True, align="R")

            # Add signature image temporarily
            if canvas_result.image_data is not None:
                sig = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGB")
                sig = sig.resize((100, 40))
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
                    sig.save(tmp_sig.name)
                    pdf.image(tmp_sig.name, x=100, y=240, w=60)

            # Add stamp image temporarily
            if stamp_file is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_stamp:
                    tmp_stamp.write(stamp_file.read())
                    tmp_stamp.flush()
                    pdf.image(tmp_stamp.name, x=10, y=240, w=40)

            pdf_bytes = pdf.output(dest="S").encode("latin-1")

            st.success("✅ تم إنشاء العقد بنجاح")
            st.download_button("📥 تحميل PDF", data=pdf_bytes, file_name=f"{contract_type}.pdf", mime="application/pdf")

            if send_whatsapp and whatsapp_number:
                wa_text = f"تم إنشاء عقد {contract_type} بين {party1} و {party2} بتاريخ {date}"
                wa_url = f"https://wa.me/966{whatsapp_number}?text={wa_text}"
                st.markdown(f"[📲 إرسال عبر واتساب]({wa_url})")

            if send_email and email_address:
                st.info(f"📧 العقد جاهز للإرسال إلى: {email_address} — (يتطلب تكامل خارجي لاحقًا)")

    with tab2:
        st.subheader("⚖️ نظام إدارة القضايا والعملاء")
        # --- Custom CSS for nicer fonts and spacing ---
        st.markdown(
            """
            <style>
            /* Set font family */
            body, .block-container {
                font-family: 'Cairo', Tahoma, sans-serif;
                direction: rtl;
            }
            /* Sidebar */
            .css-1d391kg {
                background-color: #0d3b66;
                color: white;
            }
            /* Sidebar headings */
            .css-1v0mbdj {
                font-weight: bold;
                font-size: 18px;
                margin-bottom: 15px;
                margin-top: 15px;
                color: #f4d35e;
            }
            /* Buttons */
            div.stButton > button:first-child {
                background-color: #f4d35e;
                color: #0d3b66;
                font-weight: bold;
                border-radius: 8px;
                padding: 8px 20px;
                margin-top: 10px;
            }
            div.stButton > button:first-child:hover {
                background-color: #ee964b;
                color: white;
            }
            /* Dataframe styling */
            .stDataFrame > div {
                border-radius: 12px;
                border: 1px solid #0d3b66;
            }
            /* Section headers */
            h1, h2, h3, h4 {
                color: #0d3b66;
                font-weight: 700;
            }
            /* KPI boxes */
            .kpi-box {
                background-color: #f4d35e;
                padding: 15px 20px;
                border-radius: 12px;
                color: #0d3b66;
                font-weight: 700;
                text-align: center;
                margin-bottom: 20px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


        def reshape(text):
            return get_display(arabic_reshaper.reshape(text))

        if "clients" not in st.session_state:
            st.session_state.clients = pd.DataFrame(columns=["client_id", "name", "phone", "email", "notes"])
        if "cases" not in st.session_state:
            st.session_state.cases = pd.DataFrame(columns=["case_id", "client_id", "case_name", "case_type", "status", "court_date", "notes"])
        if "invoices" not in st.session_state:
            st.session_state.invoices = pd.DataFrame(columns=["invoice_id", "client_id", "case_id", "amount", "paid", "date"])

        def next_id(df, col):
            if df.empty:
                return 1
            return df[col].max() + 1

        show_menu = st.checkbox("إظهار القائمة الجانبية")

        if show_menu:
            menu = st.sidebar.radio("القائمة", [
                "👥 العملاء",
                "⚖️ القضايا",
                "⏰ التذكيرات",
                "📄 العقود",
                "💰 الفواتير"
            ])
        else:
            menu = None

        if menu is None:
            st.info("يرجى تفعيل القائمة الجانبية لاختيار صفحة.")
        else:
            # Map sidebar choices back to keys without emojis
            menu_map = {
                "👥 العملاء": "clients",
                "⚖️ القضايا": "cases",
                "⏰ التذكيرات": "reminders",
                "📄 العقود": "contracts",
                "💰 الفواتير": "invoices"
            }
            page = menu_map[menu]

            # ------- CLIENTS PAGE -------
            if page == "clients":
                st.header("👥 إدارة العملاء")
                with st.form("add_client"):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        client_name = st.text_input("اسم العميل")
                        client_notes = st.text_area("ملاحظات")
                    with col2:
                        client_phone = st.text_input("رقم الهاتف")
                        client_email = st.text_input("البريد الإلكتروني")
                    submitted = st.form_submit_button("حفظ العميل")
                    if submitted:
                        cid = next_id(st.session_state.clients, "client_id")
                        st.session_state.clients.loc[len(st.session_state.clients)] = [cid, client_name, client_phone, client_email, client_notes]
                        st.success(f"تم إضافة العميل {client_name}")

                st.subheader("قائمة العملاء")
                st.dataframe(st.session_state.clients)

            # ------- CASES PAGE -------
            elif page == "cases":
                st.header("⚖️ إدارة القضايا")
                with st.form("add_case"):
                    client_list = st.session_state.clients["client_id"].astype(str) + " - " + st.session_state.clients["name"]
                    client_choice = st.selectbox("اختر العميل", client_list)
                    client_id = int(client_choice.split(" - ")[0]) if client_choice else None
                    case_name = st.text_input("اسم القضية")
                    case_type = st.selectbox("نوع القضية", ["جنائي", "مدني", "تجاري", "إداري"])
                    status = st.selectbox("الحالة", ["جديدة", "مستمرة", "مغلقة"])
                    court_date = st.date_input("تاريخ الجلسة")
                    case_notes = st.text_area("ملاحظات")
                    submitted = st.form_submit_button("حفظ القضية")
                    if submitted and client_id is not None:
                        cid = next_id(st.session_state.cases, "case_id")
                        st.session_state.cases.loc[len(st.session_state.cases)] = [cid, client_id, case_name, case_type, status, court_date.strftime("%Y-%m-%d"), case_notes]
                        st.success(f"تم إضافة القضية {case_name}")

                st.subheader("قائمة القضايا")
                merged_cases = st.session_state.cases.merge(st.session_state.clients[["client_id", "name"]], on="client_id", how="left")
                merged_cases = merged_cases.rename(columns={"name": "اسم العميل"})
                st.dataframe(merged_cases)

            # ------- REMINDERS PAGE -------
            elif page == "reminders":
                st.header("⏰ التذكيرات")
                st.info("الميزة قيد التطوير...")

            # ------- CONTRACTS PAGE -------
            elif page == "contracts":
                st.header("📄 العقود")
                st.info("لإنشاء العقود، انتقل إلى تبويب 'MojazContracts' في الأعلى.")

            # ------- INVOICES PAGE -------
            elif page == "invoices":
                st.header("💰 الفواتير")
                st.info("الميزة قيد التطوير...")
