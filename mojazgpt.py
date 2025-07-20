import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import io

# --- Configuration for the AI Service ---
# IMPORTANT: Replace "AIzaSyAFrAMGH3zTbX4RS11s7HNDx8mdLDTxXx4" with your actual API key if this is not it.
# For production or shared apps, NEVER hardcode your API key directly in the script.
# Use Streamlit's secrets.toml or environment variables instead for security.
API_KEY = "AIzaSyAFrAMGH3zTbX4RS11s7HNDx8mdLDTxXx4" # Your Google Gemini API Key

try:
    # Configure the AI library with your API key
    genai.configure(api_key=API_KEY)
    # Initialize the AI model for general chat and data analysis
    model = genai.GenerativeModel('gemini-2.5-flash') 
except Exception as e:
    st.error(f"حدث خطأ أثناء تهيئة خدمة الذكاء الاصطناعي: {e}. يرجى التأكد من أن مفتاح API الخاص بك صحيح وصالح. (Error initializing AI service: {e}. Please ensure your API key is correct and valid.)")
    st.stop() 

# --- Streamlit App Setup ---
st.set_page_config(page_title="MojazGPT - مساعدك الذكي", page_icon="✨", layout="wide")
st.title("✨ MojazGPT: مساعدك الذكي للمحادثة وتحليل البيانات")
st.markdown("مرحباً بك! أنا مساعدك الذكي. يمكنني الدردشة معك وتحليل البيانات من ملفات Excel أو CSV التي تحملها. (Welcome! I'm your smart assistant. I can chat with you and analyze data from Excel or CSV files you upload.)")

# Initialize chat history and uploaded data in session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if 'uploaded_data_df' not in st.session_state:
    st.session_state.uploaded_data_df = None

# --- Data Upload Section (in sidebar for cleaner main layout) ---
st.sidebar.header("تحميل البيانات (Data Upload)")
uploaded_file = st.sidebar.file_uploader("تحميل ملف Excel أو CSV (Upload your Excel أو CSV file)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Determine file type and read
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0) 
                try:
                    df = pd.read_csv(uploaded_file, encoding='cp1256') # Windows-1256 for Arabic
                except Exception:
                    uploaded_file.seek(0) 
                    df = pd.read_csv(uploaded_file, encoding='latin1') # Another common one
        else: # Assumes .xlsx
            df = pd.read_excel(uploaded_file)
        
        st.session_state.uploaded_data_df = df
        
        st.sidebar.success("تم تحميل الملف بنجاح! (File uploaded successfully!)")
        st.sidebar.markdown("**أول 5 صفوف من البيانات:**")
        st.sidebar.dataframe(df.head()) # Show a preview

        # Add a clear data button
        if st.sidebar.button("مسح البيانات المحملة (Clear Uploaded Data)"):
            st.session_state.uploaded_data_df = None
            st.session_state.messages = [] # Clear chat history when data is cleared
            st.rerun() # Rerun to clear the display
            
    except Exception as e:
        st.sidebar.error(f"خطأ في قراءة الملف: {e}. يرجى التأكد من أن الملف سليم وأن التنسيق صحيح. (Error reading file: {e}. Please ensure the file is valid and correctly formatted.)")
        st.session_state.uploaded_data_df = None # Clear potentially corrupted data
else:
    st.sidebar.info("الرجاء تحميل ملف Excel أو CSV أولاً لبدء تحليل البيانات. (Please upload an Excel أو CSV file first to start data analysis.)")
    # Show loaded data preview and clear button even if uploader is empty, if data is present
    if st.session_state.uploaded_data_df is not None:
        st.sidebar.markdown("**البيانات المحملة حاليًا:**")
        st.sidebar.dataframe(st.session_state.uploaded_data_df.head())
        if st.sidebar.button("مسح البيانات المحملة (Clear Uploaded Data)"):
            st.session_state.uploaded_data_df = None
            st.session_state.messages = []
            st.rerun()

# --- Chat Interface Section ---

# Display existing messages in chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Directly display content as markdown
        st.markdown(message["content"])

# User input and AI response logic
user_prompt = st.chat_input("كيف يمكنني مساعدتك اليوم؟ (How can I help you today?)")

if user_prompt:
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        with st.spinner("المساعد الذكي يفكر... (The smart assistant is thinking...)"):
            ai_response_content = ""
            message_placeholder = st.empty()

            system_instruction = (
                "أنت MojazGPT، مساعد دردشة عربي مدعوم بالذكاء الاصطناعي. "
                "أجب دائمًا بنفس لغة سؤال المستخدم (العربية أو الإنجليزية). "
                "إذا كان لا يمكن الإجابة على سؤال، اذكر ذلك بوضوح. "
                "حافظ على نبرة عربية في المقام الأول، ولكن انتقل بسلاسة إلى الإنجليزية إذا سأل المستخدم بالإنجليزية.\n\n"
                "Your role is to act as an AI-powered Arabic chat assistant. "
                "Respond in the same language as the user's question. "
                "If a question cannot be answered, state that clearly. "
                "Maintain an Arabic-first tone, but seamlessly switch to English if the user asks in English.\n\n"
            )
            
            # Prepare conversation history for the Gemini model
            conversation_history_for_ai = []
            
            # Add system instruction
            conversation_history_for_ai.append({"role": "user", "parts": [{"text": system_instruction}]})

            # Add data context if a DataFrame is uploaded
            if st.session_state.uploaded_data_df is not None:
                df_info = io.StringIO()
                st.session_state.uploaded_data_df.info(buf=df_info)
                df_info_str = df_info.getvalue()
                
                data_context = (
                    "لقد قام المستخدم بتحميل ملف بيانات. إليك معلومات حول هيكل البيانات وأول 5 صفوف:\n"
                    "```\n"
                    f"Column Info:\n{df_info_str}\n\n"
                    f"First 5 rows:\n{st.session_state.uploaded_data_df.head().to_markdown(index=False)}\n"
                    "```\n"
                    "يرجى استخدام هذه المعلومات للإجابة على الأسئلة المتعلقة بالبيانات. "
                    "إذا طُلب منك إجراء تحليل أو حسابات، فاذكر الخطوات التي ستتبعها أو النتائج التي يمكن استخلاصها بناءً على هذا الهيكل. "
                    "لا تحاول تنفيذ أي كود Python، فقط قدم الإجابات النصية أو التفسيرات بناءً على فهمك للبيانات.\n\n"
                    "The user has uploaded a data file. Here's information about the data structure and the first 5 rows:\n"
                    "```\n"
                    f"Column Info:\n{df_info_str}\n\n"
                    f"First 5 rows:\n{st.session_state.uploaded_data_df.head().to_markdown(index=False)}\n"
                    "```\n"
                    "Please use this information to answer data-related questions. "
                    "If asked to perform analysis or calculations, describe the steps you would take or the insights that can be drawn based on this structure. "
                    "Do not attempt to execute any Python code; just provide textual answers or explanations based on your understanding of the data."
                )
                conversation_history_for_ai.append({"role": "user", "parts": [{"text": data_context}]})

            # Add previous chat messages to the conversation history
            for msg in st.session_state.messages[:-1]: 
                genai_role = 'user' if msg["role"] == 'user' else 'model'
                conversation_history_for_ai.append(
                    {"role": genai_role, "parts": [{"text": msg["content"]}]}
                )
            
            # Add the current user prompt
            conversation_history_for_ai.append({"role": "user", "parts": [{"text": user_prompt}]})

            try:
                response = model.generate_content(conversation_history_for_ai, stream=True)
                for chunk in response:
                    if chunk.text:
                        ai_response_content += chunk.text
                        message_placeholder.markdown(ai_response_content + "▌")
                message_placeholder.markdown(ai_response_content) # Ensure final markdown without cursor
            except Exception as e:
                ai_response_content = f"حدث خطأ أثناء التواصل مع المساعد الذكي: {e}. أعتذر، لم أتمكن من معالجة طلبك الآن. يرجى المحاولة مرة أخرى لاحقًا. � (An error occurred while contacting the smart assistant: {e}. I apologize, I couldn't process your request right now. Please try again later.)"
                st.error(ai_response_content)
                print(f"General chat error details: {e}") 
            
            st.session_state.messages.append({"role": "assistant", "content": ai_response_content})

