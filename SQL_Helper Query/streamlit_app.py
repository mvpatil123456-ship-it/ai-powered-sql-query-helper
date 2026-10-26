import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import google.generativeai as genai
import os
from dotenv import load_dotenv

st.set_page_config(
    page_title="AI SQL Query Helper",
    page_icon="logo.png",
    layout="wide"
)

# Simple login screen
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.image("logo.png", width=180)
    st.title("AI SQL Query Helper — Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
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

st.title("AI SQL Query Helper")
st.write("Upload any dataset and ask questions about it in plain English")

uploaded_files = st.file_uploader("Upload your CSV or Excel file(s)", type=["csv", "xlsx", "xls"], accept_multiple_files=True)

if uploaded_files:
    all_schemas = []
    for uploaded_file in uploaded_files:
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
            col1, col2, col3 = st.columns(3)
            col1.metric("Rows", df.shape[0])
            col2.metric("Columns", df.shape[1])
            col3.metric("Missing Values", int(df.isnull().sum().sum()))

            st.write("Column Data Types:")
            st.dataframe(df.dtypes.astype(str).reset_index().rename(columns={"index": "Column", 0: "Data Type"}))

            numeric_cols = df.select_dtypes(include="number").columns
            if len(numeric_cols) > 0:
                st.write("Basic Statistics (numeric columns):")
                st.dataframe(df[numeric_cols].describe())

        table_name = uploaded_file.name.replace(".csv", "").replace(" ", "_").lower()

        password = quote_plus("mansipatil123")
        engine = create_engine(f"mysql+mysqlconnector://root:{password}@localhost/sales_db")
        df.to_sql(table_name, engine, if_exists="replace", index=False)

        schema = pd.io.sql.get_schema(df, table_name)
        all_schemas.append(schema)

    full_schema = "\n\n".join(all_schemas)

    st.subheader("Ask a question about your data")
    user_question = st.text_input("Type your question in English")

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
        with st.spinner("Explaining the query..."):
            explain_prompt = f"""
            Explain in one or two simple sentences what this SQL query does, for someone who doesn't know SQL.
            Do not repeat the SQL syntax, just explain what data it retrieves and how.

            SQL Query: {generated_sql}
            """
            explanation_response = model.generate_content(explain_prompt)
            st.info(f"**What this query does:** {explanation_response.text.strip()}")

        try:
            result_df = pd.read_sql(generated_sql, engine)
            st.write("Result:")
            st.dataframe(result_df)

            # KPI Summary Cards: Total, Average, Maximum, Minimum for each numeric column
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

            # Auto-select the most appropriate chart based on the data
            if result_df.shape[1] == 2:
                col1, col2 = result_df.columns
                if pd.api.types.is_numeric_dtype(result_df[col2]) and not pd.api.types.is_numeric_dtype(result_df[col1]):
                    is_date_col = "date" in col1.lower()
                    num_categories = result_df[col1].nunique()

                    if is_date_col:
                        st.write("Trend Chart:")
                        st.line_chart(result_df.set_index(col1))
                    elif num_categories <= 5:
                        st.write("Pie Chart:")
                        fig, ax = plt.subplots()
                        ax.pie(result_df[col2], labels=result_df[col1], autopct="%1.1f%%")
                        ax.axis("equal")
                        st.pyplot(fig)
                    else:
                        st.write("Bar Chart:")
                        st.bar_chart(result_df.set_index(col1))

                        # AI-generated insight about the result
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

            csv_data = result_df.to_csv(index=False).encode("utf-8")

            excel_buffer = io.BytesIO()
            result_df.to_excel(excel_buffer, index=False, engine="openpyxl")
            excel_data = excel_buffer.getvalue()

            sql_data = generated_sql.encode("utf-8")

            download_col1, download_col2, download_col3 = st.columns(3)
            with download_col1:
                st.download_button(
                    label="Download as CSV",
                    data=csv_data,
                    file_name="query_result.csv",
                    mime="text/csv"
                )
            with download_col2:
                st.download_button(
                    label="Download as Excel",
                    data=excel_data,
                    file_name="query_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with download_col3:
                st.download_button(
                    label="Download SQL Query",
                    data=sql_data,
                    file_name="query.sql",
                    mime="text/plain"
                )
        except Exception as e:
            st.error(f"Error running query: {e}")

if st.session_state.history:
    st.sidebar.subheader("Recent Questions")
    for q in reversed(st.session_state.history):
        st.sidebar.write(f"- {q}")