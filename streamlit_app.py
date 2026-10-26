import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import google.generativeai as genai
import os
from dotenv import load_dotenv
import base64

st.set_page_config(
    page_title="AI SQL Query Helper",
    page_icon="logo.png",
    layout="wide"
)

# =========================
# PROFESSIONAL UI STYLING
# =========================

st.markdown("""
<style>

/* Main background */
.stApp {
    background-color: #F7F9FC;
}

/* Main content spacing */
.block-container {
    padding-top: 1.5rem;
    padding-left: 3rem;
    padding-right: 3rem;
    max-width: 1500px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #EEF5FF;
    border-right: 1px solid #D8E6F7;
}

section[data-testid="stSidebar"] > div {
    padding-top: 2rem;
}

/* Sidebar text */
section[data-testid="stSidebar"] p {
    font-size: 15px;
    color: #173A70;
}

/* Main headings */
h1 {
    color: #102A56 !important;
    font-weight: 700 !important;
}

h2, h3 {
    color: #173A70 !important;
}

/* Normal text */
.stMarkdown p {
    color: #52627A;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background-color: white;
    border: 1px solid #D9E5F5;
    border-radius: 14px;
    padding: 15px;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid #D9E5F5;
    border-radius: 12px;
    overflow: hidden;
}

/* Text input */
div[data-baseweb="input"] {
    border-radius: 10px;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button {
    border-radius: 9px;
    font-weight: 600;
    border: none;
}

/* Success message */
div[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #DCE7F5;
    border-radius: 12px;
    padding: 12px;
}

/* Expanders */
details {
    border: 1px solid #DCE7F5 !important;
    border-radius: 12px !important;
    background-color: white;
}

/* Code block */
[data-testid="stCodeBlock"] {
    border-radius: 12px;
}

/* Horizontal line */
hr {
    border-color: #DCE7F5;
}

</style>
""", unsafe_allow_html=True)

# Simple login screen
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

logo_path = os.path.join(os.path.dirname(__file__), "SQL_Helper Query", "logo.png")

if not st.session_state.logged_in:

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.write("")
        st.write("")
        with open(logo_path, "rb") as f:
            logo = base64.b64encode(f.read()).decode()

        st.markdown(
            f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{logo}" width="230">
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            "<h1 style='text-align: center;'>AI SQL Query Helper</h1>",
            unsafe_allow_html=True
        )

        username = st.text_input("Username", placeholder="Enter Username")
        password = st.text_input("Password", type="password", placeholder="Enter Password")

        st.markdown("""
        <style>
        .stButton > button {
            background-color: #1976D2 !important;
            color: white !important;
            width: 180px !important;
            display: block !important;
            margin: 0 auto !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px !important;
            font-weight: bold !important;
        }

        .stButton > button:hover {
            background-color: #1259A5 !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button("Login", use_container_width=True):
            if username == "mansi" and password == "mansi123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Incorrect username or password")

    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")

# Logo
with open(r"C:\Users\mp338\OneDrive\Desktop\SQL_Helper Query\SQL_Helper Query\sql_logo.png", "rb") as f:
    logo = base64.b64encode(f.read()).decode()

# Logo + Title in SAME line
st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:5px; margin-top:20px;">
        <img src="data:image/png;base64,{logo}" width="120">
        <h1 style="margin:0;">AI SQL Query Helper</h1>
    </div>
    """,
    unsafe_allow_html=True
)

st.write("Upload any dataset, or connect to a MySQL database, and ask questions about it in plain English")

# =========================
# DATA SOURCE SELECTION
# =========================

st.subheader("Data source")
data_source = st.radio("Choose source", ["Upload file", "MySQL database"])

all_schemas = []
engine = None
full_schema = ""
proceed = False

if data_source == "Upload file":
    uploaded_files = st.file_uploader("Upload your CSV, Excel, or SQL file(s)", type=["csv", "xlsx", "xls", "sql"], accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:

            if uploaded_file.name.endswith(".sql"):
                sql_script = uploaded_file.read().decode("utf-8")
                statements = [s.strip() for s in sql_script.split(";") if s.strip()]

                engine_root = create_engine(
                    f"mysql+mysqlconnector://root:{quote_plus(os.getenv('MYSQL_PASSWORD'))}@localhost/sales_db"
                )
                with engine_root.connect() as conn:
                    for stmt in statements:
                        try:
                            conn.execute(text(stmt))
                        except Exception as e:
                            st.warning(f"Skipped one statement in {uploaded_file.name}: {e}")
                    conn.commit()

                st.success(f"Uploaded and executed: {uploaded_file.name}")

                with engine_root.connect() as conn:
                    tables_in_file = conn.execute(text("SHOW TABLES FROM sales_db")).fetchall()

                for (tbl,) in tables_in_file:
                    with engine_root.connect() as conn:
                        schema_rows = conn.execute(text(f"DESCRIBE sales_db.`{tbl}`")).fetchall()
                    schema_text = f"Table: {tbl}\nColumns: " + ", ".join([f"{row[0]} ({row[1]})" for row in schema_rows])
                    all_schemas.append(schema_text)

                engine = engine_root
                continue

            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            for col in df.columns:
                if "date" in col.lower():
                    try:
                        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass

            st.success(f"Uploaded: {uploaded_file.name}")
            st.dataframe(df.head())

            with st.expander(f"Data Profile: {uploaded_file.name}"):
                pcol1, pcol2, pcol3 = st.columns(3)
                pcol1.metric("Rows", df.shape[0])
                pcol2.metric("Columns", df.shape[1])
                pcol3.metric("Missing Values", int(df.isnull().sum().sum()))

                st.write("Column Data Types:")
                st.dataframe(df.dtypes.astype(str).reset_index().rename(columns={"index": "Column", 0: "Data Type"}))

                numeric_cols = df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    st.write("Basic Statistics (numeric columns):")
                    st.dataframe(df[numeric_cols].describe())

            table_name = uploaded_file.name.rsplit(".", 1)[0].replace(" ", "_").lower()

            password = quote_plus(os.getenv("MYSQL_PASSWORD"))
            engine = create_engine(f"mysql+mysqlconnector://root:{password}@localhost/sales_db")
            df.to_sql(table_name, engine, if_exists="replace", index=False)

            schema = pd.io.sql.get_schema(df, table_name)
            all_schemas.append(schema)

        if engine is not None:
            full_schema = "\n\n".join(all_schemas)
            proceed = True

else:
    st.write("Connect to your existing MySQL database")
    db_host = st.text_input("Host", value="localhost")
    db_user = st.text_input("Username", value="root")
    db_pass = st.text_input("Password", type="password")

    if st.button("Show databases"):
        try:
            db_password_q = quote_plus(db_pass)
            server_engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password_q}@{db_host}/")
            with server_engine.connect() as conn:
                db_list = [row[0] for row in conn.execute(text("SHOW DATABASES")).fetchall()]
            st.session_state.available_databases = db_list
            st.session_state.server_host = db_host
            st.session_state.server_user = db_user
            st.session_state.server_pass = db_pass
        except Exception as e:
            st.error(f"Could not connect to server: {e}")

    if "available_databases" in st.session_state:
        db_name = st.selectbox("Database name", st.session_state.available_databases)

        if st.button("Connect"):
            try:
                db_password_q = quote_plus(db_pass)
                db_engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password_q}@{db_host}/{db_name}")

                with db_engine.connect() as conn:
                    tables = conn.execute(text(f"SHOW TABLES FROM {db_name}")).fetchall()

                db_schemas = []
                for (tbl,) in tables:
                    with db_engine.connect() as conn:
                        schema_rows = conn.execute(text(f"DESCRIBE {db_name}.`{tbl}`")).fetchall()
                    schema_text = f"Table: {tbl}\nColumns: " + ", ".join([f"{row[0]} ({row[1]})" for row in schema_rows])
                    db_schemas.append(schema_text)

                st.session_state.db_engine = db_engine
                st.session_state.db_schemas = db_schemas
                st.session_state.db_name_connected = db_name
                st.success(f"Connected to database: {db_name} ({len(tables)} tables found)")
            except Exception as e:
                st.error(f"Could not connect: {e}")

    if "db_engine" in st.session_state:
        engine = st.session_state.db_engine
        all_schemas = st.session_state.db_schemas
        full_schema = "\n\n".join(all_schemas)
        proceed = True

# =========================
# QUESTION + ANSWER FLOW
# =========================

if proceed:

    if st.session_state.get("suggestions_schema") != full_schema:
        try:
            with st.spinner("Preparing suggested questions..."):
                suggest_prompt = f"""
                Given these table schemas:
                {full_schema}

                Suggest exactly 5 simple English questions a business user could ask about this data.
                Prefer questions that involve grouping, totals, averages, counts, or comparisons across categories
                (e.g. "total X for each Y", "average X by Y", "how many records per Y") rather than questions
                that just list individual records — so the results are good for charts and summary metrics.
                If there is a date-related column in the schema, include at least one question that shows a trend
                over time using that date column (e.g. "show X over time by [date column]").
                Return ONLY the 5 questions, one per line, no numbering, no extra text.
                """
                suggestions_response = model.generate_content(suggest_prompt)
                st.session_state.suggested_questions = [q.strip() for q in suggestions_response.text.strip().split("\n") if q.strip()]
        except Exception as e:
            st.warning("Could not generate suggested questions right now (AI usage limit may be reached). You can still type your own question below.")
            st.session_state.suggested_questions = []
        st.session_state.suggestions_schema = full_schema

    suggested_questions = st.session_state.get("suggested_questions", [])

    def set_question(q):
        st.session_state.user_question_input = q

    if suggested_questions:
        st.write("Try asking:")
        suggestion_cols = st.columns(len(suggested_questions))
        for i, sq in enumerate(suggested_questions):
            suggestion_cols[i].button(sq, key=f"suggestion_{i}", on_click=set_question, args=(sq,))

    st.subheader("Ask a question about your data")
    user_question = st.text_input("Type your question in English", key="user_question_input")

    if user_question:
        prompt = f"""
        You are a MySQL expert. Given these table schemas:
        {full_schema}

        Convert this question into a single valid MySQL SELECT query.
        Only return the SQL query, nothing else. No explanation, no markdown.
        If the question cannot be answered using this data (e.g. it's unrelated, like asking about weather or general knowledge), respond with exactly: NOT_RELEVANT

        Question: {user_question}
        """

        try:
            with st.spinner("Thinking... generating SQL query"):
                response = model.generate_content(prompt)
            generated_sql = response.text.strip()
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                st.error("The AI has reached its daily free usage limit. Please try again after some time (usually resets within a day).")
            else:
                st.error("Something went wrong while generating the query. Please try again.")
            st.stop()

        if not generated_sql or generated_sql.strip().upper() == "NOT_RELEVANT":
            st.toast("This question doesn't seem related to your uploaded data", icon="⚠️")
            st.warning("Please ask a question that can be answered using your dataset's columns.")
            st.stop()

        if not generated_sql.strip().upper().startswith("SELECT"):
            st.error("Only SELECT queries are allowed for safety. This query was blocked.")
            st.stop()

        st.session_state.history.append(user_question)
        if len(st.session_state.history) > 5:
            st.session_state.history = st.session_state.history[-5:]

        st.write("Generated SQL Query:")
        st.code(generated_sql, language="sql")

        try:
            with st.spinner("Explaining the query..."):
                explain_prompt = f"""
                Explain in one or two simple sentences what this SQL query does, for someone who doesn't know SQL.
                Do not repeat the SQL syntax, just explain what data it retrieves and how.

                SQL Query: {generated_sql}
                """
                explanation_response = model.generate_content(explain_prompt)
                st.info(f"**What this query does:** {explanation_response.text.strip()}")
        except Exception as e:
            st.info("Explanation unavailable right now (AI usage limit may be reached).")
            
            result_df = pd.read_sql(generated_sql, engine)
            st.write("Result:")
            st.dataframe(result_df)

            numeric_result_cols = result_df.select_dtypes(include="number").columns
            if len(numeric_result_cols) > 0:
                def format_indian_number(num):
                    if abs(num) >= 10000000:
                        return f"{num/10000000:.2f} Cr"
                    elif abs(num) >= 100000:
                        return f"{num/100000:.2f} L"
                    elif abs(num) >= 1000:
                        return f"{num/1000:.2f} K"
                    else:
                        return f"{num:,.0f}"

                for col in numeric_result_cols:
                    clean_label = col.replace("SUM(", "").replace("AVG(", "").replace("COUNT(", "").replace(")", "").replace("_", " ").title()
                    st.write(f"Key Metrics — {clean_label}:")

                    total_value = result_df[col].sum()
                    avg_value = result_df[col].mean()
                    max_value = result_df[col].max()
                    min_value = result_df[col].min()

                    kpi_data = [
                        ("Total", total_value),
                        ("Average", avg_value),
                        ("Maximum", max_value),
                        ("Minimum", min_value)
                    ]

                    kpi_cols = st.columns(4)
                    for i, (label, value) in enumerate(kpi_data):
                        with kpi_cols[i]:
                            st.markdown(
                                f"""
                                <div style="
                                    border: 2px solid #87CEEB;
                                    border-radius: 10px;
                                    background-color: #E0F7FA;
                                    padding: 15px;
                                    text-align: center;
                                ">
                                    <div style="font-size: 14px; color: #333;">{label}</div>
                                    <div style="font-size: 22px; font-weight: bold; color: #000;">{format_indian_number(value)}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

            if result_df.shape[1] == 2:
                chart_col1, chart_col2 = result_df.columns
                if pd.api.types.is_numeric_dtype(result_df[chart_col2]) and not pd.api.types.is_numeric_dtype(result_df[chart_col1]):
                    is_date_col = "date" in chart_col1.lower()
                    num_categories = result_df[chart_col1].nunique()

                    if is_date_col:
                        st.write("Trend Chart:")
                        st.line_chart(result_df.set_index(chart_col1))
                    elif num_categories <= 5:
                        st.write("Pie Chart:")
                        fig, ax = plt.subplots()
                        ax.pie(result_df[chart_col2], labels=result_df[chart_col1], autopct="%1.1f%%")
                        ax.axis("equal")
                        st.pyplot(fig)
                    else:
                        st.write("Bar Chart:")
                        st.bar_chart(result_df.set_index(chart_col1))

            try:
                with st.spinner("Generating insight..."):
                    insight_prompt = f"""
                    Look at this query result data and give one short, simple insight or observation about it,
                    in one sentence, as if explaining to a business person with no technical background.
                    Do not repeat raw numbers unnecessarily, focus on the meaning/pattern.

                    Question asked: {user_question}
                    Result data: {result_df.to_string(index=False)}
                    """
                    insight_response = model.generate_content(insight_prompt)
                    st.success(f"**Insight:** {insight_response.text.strip()}")
            except Exception as e:
                st.info("Insight unavailable right now (AI usage limit may be reached).")

            csv_data = result_df.to_csv(index=False).encode("utf-8")

            excel_buffer = io.BytesIO()
            result_df.to_excel(excel_buffer, index=False, engine="openpyxl")
            excel_data = excel_buffer.getvalue()

            sql_data = generated_sql.encode("utf-8")

            download_co