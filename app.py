import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
import os
import tempfile
import json
import uuid
from dotenv import load_dotenv
import pymongo
import mongomock
import plotly.express as px

def split_sql_statements(sql_text):
    """Split a SQL script into individual statements, handling quotes and comments."""
    statements = []
    current_statement = []
    in_single_quote = False
    in_double_quote = False
    in_comment_line = False
    in_block_comment = False

    i = 0
    n = len(sql_text)
    while i < n:
        char = sql_text[i]

        # Handle line comment '--'
        if not in_single_quote and not in_double_quote and not in_block_comment and i + 1 < n and sql_text[i:i+2] == '--':
            in_comment_line = True
            i += 2
            continue

        # Handle line comment '#' (MySQL style)
        if not in_single_quote and not in_double_quote and not in_block_comment and char == '#':
            in_comment_line = True
            i += 1
            continue

        # Handle block comment '/*'
        if not in_single_quote and not in_double_quote and not in_comment_line and i + 1 < n and sql_text[i:i+2] == '/*':
            in_block_comment = True
            i += 2
            continue

        # End of line comment
        if in_comment_line and char == '\n':
            in_comment_line = False
            current_statement.append(char)
            i += 1
            continue

        # End of block comment '*/'
        if in_block_comment and i + 1 < n and sql_text[i:i+2] == '*/':
            in_block_comment = False
            i += 2
            continue

        # If we are inside comments, skip the char
        if in_comment_line or in_block_comment:
            i += 1
            continue

        # Track quote state
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        # Statement terminator
        if char == ';' and not in_single_quote and not in_double_quote:
            stmt = "".join(current_statement).strip()
            if stmt:
                statements.append(stmt)
            current_statement = []
        else:
            current_statement.append(char)

        i += 1

    stmt = "".join(current_statement).strip()
    if stmt:
        statements.append(stmt)

    return statements

# Page configuration
st.set_page_config(
    page_title="EasifAI - Text-to-SQL Explorer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Inject premium black/violet CSS design system
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
    /* ==============================
       RESET & BASE
    ============================== */
    html, body {
        font-family: 'Inter', system-ui, sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #08080d;
        color: #c9c9d9;
    }
    [data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {
        visibility: hidden !important;
        display: none !important;
    }
    footer {
        visibility: hidden !important;
        display: none !important;
    }
    [data-testid="stSidebar"] {
        background: #0d0d14 !important;
        border-right: 1px solid #1e1a2e;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px;
    }

    /* ==============================
       SIDEBAR ELEMENTS
    ============================== */
    .sidebar-brand {
        font-size: 1.1rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 0.75rem 0 1.25rem 0;
        border-bottom: 1px solid #1e1a2e;
        margin-bottom: 1.5rem;
    }
    .sidebar-brand span {
        color: #8b5cf6;
    }
    .sidebar-section-label {
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #4a4a6a;
        margin-bottom: 0.6rem;
        margin-top: 1.6rem;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 100px;
        font-size: 0.78rem;
        font-weight: 500;
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
    }
    .status-pill.active {
        background: rgba(139, 92, 246, 0.12);
        color: #a78bfa;
        border: 1px solid rgba(139, 92, 246, 0.25);
    }
    .status-pill.inactive {
        background: rgba(255, 255, 255, 0.04);
        color: #5a5a7a;
        border: 1px solid #1e1a2e;
    }

    /* ==============================
       PAGE HEADER
    ============================== */
    .page-header {
        padding: 0.5rem 0 1.75rem 0;
        border-bottom: 1px solid #1a1a28;
        margin-bottom: 2rem;
    }
    .page-header h1 {
        font-size: 1.9rem;
        font-weight: 700;
        color: #f0f0ff;
        letter-spacing: -0.02em;
        margin: 0 0 0.35rem 0;
    }
    .page-header h1 span {
        color: #8b5cf6;
    }
    .page-header p {
        font-size: 0.9rem;
        color: #4a4a6a;
        margin: 0;
        font-weight: 400;
    }

    /* ==============================
       SECTION HEADERS
    ============================== */
    .section-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #8b5cf6;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-label::after {
        content: "";
        flex: 1;
        height: 1px;
        background: #1a1a28;
    }

    /* ==============================
       QUERY INPUT PANEL
    ============================== */
    .query-panel {
        background: #0d0d18;
        border: 1px solid #1e1a2e;
        border-radius: 10px;
        padding: 1.4rem 1.5rem 1.2rem;
        margin-bottom: 1.5rem;
    }
    .query-panel:focus-within {
        border-color: #8b5cf6;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.08);
    }

    /* ==============================
       SUGGESTION CHIPS
    ============================== */
    .suggest-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 1.25rem;
    }

    /* ==============================
       RESULTS PANEL
    ============================== */
    .result-card {
        background: #0d0d18;
        border: 1px solid #1e1a2e;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .result-card-title {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #8b5cf6;
        margin-bottom: 1rem;
    }

    /* ==============================
       EXPLANATION BLOCK
    ============================== */
    .explanation-block {
        background: #0d0d18;
        border: 1px solid #1e1a2e;
        border-left: 3px solid #8b5cf6;
        border-radius: 0 8px 8px 0;
        padding: 1.1rem 1.4rem;
        font-size: 0.92rem;
        line-height: 1.7;
        color: #b0b0c8;
    }

    /* ==============================
       STAT PILLS
    ============================== */
    .stat-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 0.75rem;
    }
    .stat-pill {
        background: #131320;
        border: 1px solid #1e1a2e;
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 0.78rem;
        color: #6a6a8a;
    }
    .stat-pill strong {
        color: #a78bfa;
    }

    /* ==============================
       TABLE / SCHEMA TAGS
    ============================== */
    .table-name-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        font-weight: 600;
        color: #a78bfa;
        margin-bottom: 0.6rem;
    }
    .col-tag {
        display: inline-block;
        background: #131320;
        border: 1px solid #1e1a2e;
        border-radius: 4px;
        padding: 2px 9px;
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        color: #8080a8;
        margin: 2px 3px 2px 0;
    }
    .col-tag.pk {
        border-color: rgba(139, 92, 246, 0.3);
        color: #c4b5fd;
    }

    /* ==============================
       HISTORY ENTRY
    ============================== */
    .history-question {
        font-size: 0.9rem;
        font-weight: 500;
        color: #d0d0e8;
    }

    /* ==============================
       STREAMLIT OVERRIDES
    ============================== */
    /* Tabs */
    [data-testid="stTabs"] button {
        font-size: 0.82rem;
        font-weight: 500;
        color: #4a4a6a;
        letter-spacing: 0.03em;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #a78bfa;
        border-bottom-color: #8b5cf6 !important;
    }
    /* Inputs */
    [data-testid="stTextInput"] input {
        background: #08080d;
        border: 1px solid #1e1a2e;
        color: #e0e0f0;
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        border-radius: 6px;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #8b5cf6;
        box-shadow: 0 0 0 2px rgba(139,92,246,0.15);
    }
    /* Primary button */
    [data-testid="baseButton-primary"] {
        background: #8b5cf6 !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.02em !important;
        color: #fff !important;
        transition: background 0.15s;
    }
    [data-testid="baseButton-primary"]:hover {
        background: #7c3aed !important;
    }
    /* Secondary button */
    [data-testid="baseButton-secondary"] {
        background: #131320 !important;
        border: 1px solid #2a2040 !important;
        border-radius: 6px !important;
        font-size: 0.8rem !important;
        color: #8080a8 !important;
    }
    [data-testid="baseButton-secondary"]:hover {
        border-color: #8b5cf6 !important;
        color: #c4b5fd !important;
    }
    /* Expander */
    [data-testid="stExpander"] {
        background: #0d0d18;
        border: 1px solid #1e1a2e !important;
        border-radius: 8px !important;
    }
    /* Sidebar selectbox */
    [data-testid="stSelectbox"] > div > div {
        background: #0d0d18 !important;
        border-color: #1e1a2e !important;
        color: #c0c0d8 !important;
        font-size: 0.85rem !important;
    }
    /* Scrollbar */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #0d0d14; }
    ::-webkit-scrollbar-thumb { background: #2a2040; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #8b5cf6; }
    /* Divider */
    hr { border-color: #1a1a28 !important; }
    /* Download button */
    [data-testid="stDownloadButton"] button {
        background: transparent !important;
        border: 1px solid #2a2040 !important;
        border-radius: 6px !important;
        color: #8b5cf6 !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
    }
    [data-testid="stDownloadButton"] button:hover {
        background: rgba(139,92,246,0.08) !important;
        border-color: #8b5cf6 !important;
    }
    /* Code blocks */
    [data-testid="stCode"] {
        border: 1px solid #1e1a2e;
        border-radius: 8px;
    }
    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 1px solid #1e1a2e;
        border-radius: 8px;
        overflow: hidden;
    }
    /* Success / Error / Warning / Info */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        border: 1px solid #1e1a2e !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE SETUP -----------------
if "session_uuid" not in st.session_state:
    st.session_state.session_uuid = str(uuid.uuid4())
if "history" not in st.session_state:
    st.session_state.history = []
if "query_input" not in st.session_state:
    st.session_state.query_input = ""
if "query_to_run" not in st.session_state:
    st.session_state.query_to_run = None
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "last_sql" not in st.session_state:
    st.session_state.last_sql = ""
if "last_explanation" not in st.session_state:
    st.session_state.last_explanation = ""
if "error_msg" not in st.session_state:
    st.session_state.error_msg = ""
if "mongo_client" not in st.session_state:
    st.session_state.mongo_client = None
if "mongo_db_name" not in st.session_state:
    st.session_state.mongo_db_name = "test"

def set_question(q):
    st.session_state.query_input = q
    st.session_state.query_to_run = q

# ----------------- SIDEBAR -----------------
st.sidebar.markdown("""
<div class='sidebar-brand'>Easif<span>AI</span></div>
""", unsafe_allow_html=True)

# API key loaded silently from .env — not shown in UI
api_key = os.getenv("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# Model hardcoded — not shown in UI
selected_model = "gemini-2.5-flash"

st.sidebar.markdown('<div class="sidebar-section-label">Database Engine</div>', unsafe_allow_html=True)
db_engine = st.sidebar.selectbox(
    "Select Engine",
    options=["SQL (SQLite/CSV)", "NoSQL (MongoDB)"],
    index=0,
    key="db_engine_selectbox"
)

db_path = None

if db_engine == "SQL (SQLite/CSV)":
    st.sidebar.markdown('<div class="sidebar-section-label">Database File</div>', unsafe_allow_html=True)
    uploaded_files = st.sidebar.file_uploader(
        "Upload database (.db, .sqlite, .sql, .csv)", 
        type=["db", "sqlite", "sql", "csv"], 
        accept_multiple_files=True,
        key="sql_file_uploader"
    )

    if uploaded_files:
        temp_dir = tempfile.gettempdir()
        db_path = os.path.join(temp_dir, f"temp_db_{st.session_state.session_uuid}.db")
        
        # Safely clean up existing tables in temp db to start fresh
        try:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = [row[0] for row in cursor.fetchall()]
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS [{table}];")
                conn.commit()
                conn.close()
        except Exception:
            # Fallback to file deletion if open connections are not locking it
            try:
                os.remove(db_path)
            except Exception:
                pass

        # Process uploaded files
        has_sqlite = any(f.name.endswith(('.db', '.sqlite')) for f in uploaded_files)
        
        if has_sqlite:
            if len(uploaded_files) > 1:
                st.sidebar.error("Please upload only ONE SQLite database (.db/.sqlite) file at a time.")
                db_path = None
            else:
                # Direct SQLite database copy
                try:
                    with open(db_path, "wb") as f:
                        f.write(uploaded_files[0].getbuffer())
                    st.sidebar.markdown(f'<div class="status-pill active">● {uploaded_files[0].name}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.sidebar.error(f"Error loading SQLite database: {e}")
                    db_path = None
        else:
            conn = None
            try:
                conn = sqlite3.connect(db_path)
                csv_count = 0
                sql_count = 0

                # First, execute SQL scripts (skip unsupported non-SQLite commands silently)
                for f in uploaded_files:
                    if f.name.endswith('.sql'):
                        sql_text = f.read().decode('utf-8')
                        statements = split_sql_statements(sql_text)
                        skip_prefixes = [
                            'create database', 'use ', 'set ', 'alter database',
                            'lock tables', 'unlock tables', '/*!'
                        ]
                        for stmt in statements:
                            stmt_clean = stmt.strip()
                            if not stmt_clean:
                                continue
                            if any(stmt_clean.lower().startswith(p) for p in skip_prefixes):
                                continue
                            try:
                                conn.execute(stmt_clean)
                            except sqlite3.Error:
                                pass  # Silently skip incompatible statements
                        sql_count += 1

                # Load CSV files as tables
                for f in uploaded_files:
                    if f.name.endswith('.csv'):
                        df = pd.read_csv(f)
                        table_name = os.path.splitext(f.name)[0].strip().replace(" ", "_").replace("-", "_").lower()
                        df.to_sql(table_name, conn, if_exists="replace", index=False)
                        csv_count += 1

                conn.commit()

                # Count how many tables were actually created
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                table_count = cursor.fetchone()[0]

                st.sidebar.markdown(
                    f'<div class="status-pill active">● {table_count} table{"s" if table_count != 1 else ""} loaded</div>',
                    unsafe_allow_html=True
                )

            except Exception as e:
                st.sidebar.error(f"Error: {e}")
                db_path = None
            finally:
                if conn:
                    conn.close()
    else:
        st.sidebar.markdown('<div class="status-pill inactive">○ No file uploaded</div>', unsafe_allow_html=True)
        st.sidebar.caption("Supported formats: .db · .sqlite · .sql · .csv")

else:  # NoSQL (MongoDB)
    st.sidebar.markdown('<div class="sidebar-section-label">Connection Mode</div>', unsafe_allow_html=True)
    mongo_mode = st.sidebar.radio(
        "Mode", 
        ["Upload JSON Collections", "Live MongoDB Connection"],
        label_visibility="collapsed"
    )

    if mongo_mode == "Upload JSON Collections":
        uploaded_json_files = st.sidebar.file_uploader(
            "Upload JSON collection files", 
            type=["json"], 
            accept_multiple_files=True,
            key="mongo_json_uploader"
        )
        if uploaded_json_files:
            try:
                # Initialize mongomock client
                mock_client = mongomock.MongoClient()
                mongo_db = mock_client["test"]
                st.session_state.mongo_client = mock_client
                st.session_state.mongo_db_name = "test"
                
                loaded_collections = 0
                for f in uploaded_json_files:
                    content_str = f.read().decode('utf-8')
                    collection_name = os.path.splitext(f.name)[0].strip().replace(" ", "_").replace("-", "_").lower()
                    
                    try:
                        data = json.loads(content_str)
                        if isinstance(data, dict):
                            data = [data]
                    except json.JSONDecodeError:
                        data = []
                        for line in content_str.strip().split("\n"):
                            if line.strip():
                                try:
                                    data.append(json.loads(line))
                                except json.JSONDecodeError:
                                    pass
                    
                    if data:
                        mongo_db[collection_name].drop()
                        mongo_db[collection_name].insert_many(data)
                        loaded_collections += 1
                
                st.sidebar.markdown(
                    f'<div class="status-pill active">● {loaded_collections} collection{"s" if loaded_collections != 1 else ""} loaded</div>',
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.sidebar.error(f"Error loading JSON data: {e}")
                st.session_state.mongo_client = None
        else:
            st.session_state.mongo_client = None
            st.sidebar.markdown('<div class="status-pill inactive">○ No JSON files uploaded</div>', unsafe_allow_html=True)
            st.sidebar.caption("Upload JSON files (e.g. products.json) to simulate collections in-memory.")

    else:  # Live MongoDB Connection
        mongo_uri = st.sidebar.text_input(
            "Connection URI", 
            value="mongodb://localhost:27017",
            placeholder="mongodb://username:password@host:port"
        )
        
        default_db_name = "test"
        if mongo_uri:
            try:
                from pymongo.uri_parser import parse_uri
                parsed = parse_uri(mongo_uri)
                if parsed.get("database"):
                    default_db_name = parsed["database"]
            except Exception:
                pass
        
        mongo_db_name_input = st.sidebar.text_input("Database Name", value=default_db_name)
        
        if st.sidebar.button("Connect to MongoDB"):
            try:
                with st.spinner("Connecting..."):
                    client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
                    client.server_info()
                    st.session_state.mongo_client = client
                    st.session_state.mongo_db_name = mongo_db_name_input
                    st.sidebar.success("Connected successfully!")
            except Exception as e:
                st.sidebar.error(f"Connection failed: {e}")
                st.session_state.mongo_client = None
        
        if st.session_state.mongo_client is not None and not isinstance(st.session_state.mongo_client, mongomock.MongoClient):
            st.sidebar.markdown(
                f'<div class="status-pill active">● Connected to {st.session_state.mongo_db_name}</div>',
                unsafe_allow_html=True
            )
        else:
            st.sidebar.markdown('<div class="status-pill inactive">○ Disconnected</div>', unsafe_allow_html=True)


# Helper functions to extract database schema
def get_db_schema_details(db_file):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Query tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = {}
        for table in tables:
            # Columns metadata
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            
            # Create statement SQL
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
            create_sql_res = cursor.fetchone()
            create_sql = create_sql_res[0] if create_sql_res else ""
            
            # Fetch sample records
            try:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
                sample_rows = cursor.fetchall()
                col_names = [col[1] for col in columns]
                samples = [dict(zip(col_names, row)) for row in sample_rows]
            except Exception:
                samples = []
                
            schema_info[table] = {
                "columns": [{"name": col[1], "type": col[2], "notnull": col[3], "pk": col[5]} for col in columns],
                "create_sql": create_sql,
                "samples": samples
            }
        conn.close()
        return schema_info
    except Exception as e:
        st.sidebar.error(f"Error reading database: {e}")
        return {}

def get_mongo_schema_details(client, db_name):
    try:
        db = client[db_name]
        collections = db.list_collection_names()
        schema_info = {}
        for coll_name in collections:
            if coll_name.startswith("system."):
                continue
            coll = db[coll_name]
            doc_count = coll.count_documents({})
            samples = list(coll.find().limit(3))
            
            cleaned_samples = []
            for s in samples:
                s_copy = dict(s)
                if "_id" in s_copy:
                    s_copy["_id"] = str(s_copy["_id"])
                cleaned_samples.append(s_copy)
            
            fields = {}
            for s in samples:
                for k, v in s.items():
                    if k == "_id":
                        fields[k] = {"name": k, "type": "ObjectId", "pk": True}
                    else:
                        fields[k] = {"name": k, "type": type(v).__name__, "pk": False}
            
            schema_info[coll_name] = {
                "columns": list(fields.values()),
                "document_count": doc_count,
                "samples": cleaned_samples,
                "create_sql": None
            }
        return schema_info
    except Exception as e:
        st.sidebar.error(f"Error reading MongoDB: {e}")
        return {}

# ----------------- SIDEBAR SCHEMA EXPLORER -----------------
schema_data = {}
if db_path:
    schema_data = get_db_schema_details(db_path)
elif st.session_state.mongo_client is not None:
    schema_data = get_mongo_schema_details(st.session_state.mongo_client, st.session_state.mongo_db_name)

if schema_data:
    st.sidebar.markdown("<h3 style='font-family:Space Grotesk; margin-top: 1rem;'>📊 Database Schema</h3>", unsafe_allow_html=True)
    for tbl_name, info in schema_data.items():
        with st.sidebar.expander(tbl_name, expanded=False):
            st.markdown(f'<div class="table-name-tag">{tbl_name}</div>', unsafe_allow_html=True)
            for col in info["columns"]:
                pk_class = " pk" if col["pk"] else ""
                pk_symbol = " ◆" if col["pk"] else ""
                st.markdown(f'<span class="col-tag{pk_class}">{col["name"]}&nbsp;<em style="color:#3a3a5a">{col["type"]}</em>{pk_symbol}</span>', unsafe_allow_html=True)
            
            # Show raw schema SQL or Document Count
            if db_engine == "NoSQL (MongoDB)":
                st.markdown(f"**Documents:** `{info.get('document_count', 0)}`")
            elif info.get("create_sql"):
                st.code(info["create_sql"], language="sql")
            
            # Show tiny sample data preview
            if info["samples"]:
                st.markdown("**Sample Data Preview:**")
                st.dataframe(pd.DataFrame(info["samples"]), use_container_width=True)

# ----------------- MAIN AREA -----------------
st.markdown("""
<div class="page-header">
    <h1>Easif<span>AI</span></h1>
</div>
""", unsafe_allow_html=True)

col_reset, _ = st.columns([1, 5])
with col_reset:
    if st.button("Clear history", help="Clears results and chat history"):
        st.session_state.history = []
        st.session_state.last_results = None
        st.session_state.last_query = ""
        st.session_state.last_sql = ""
        st.session_state.last_explanation = ""
        st.session_state.error_msg = ""
        st.rerun()

# Tabs
tab_workspace, tab_schema_details, tab_history = st.tabs([
    "Query",
    "Schema",
    "History"
])

# ----------------- TAB 1: WORKSPACE -----------------
with tab_workspace:
    # Suggested questions
    suggestions = []
    if db_engine == "SQL (SQLite/CSV)":
        if db_path and "students" in [t.lower() for t in schema_data.keys()]:
            suggestions = [
                "List all students with GPA above 3.5.",
                "Count students enrolled in MATH201.",
                "Names of students in 'Introduction to Computer Science'.",
                "Students and instructors who received an A grade."
            ]
    else:  # MongoDB
        if st.session_state.mongo_client is not None:
            collections = [t.lower() for t in schema_data.keys()]
            if any("product" in c for c in collections):
                suggestions = [
                    "Find all products with price greater than 100.",
                    "Show products in the 'Electronics' category.",
                    "List products sorted by stock in descending order.",
                    "Count how many products have stock less than 10."
                ]

    if suggestions:
        st.markdown('<div class="section-label">Suggested Questions</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, q in enumerate(suggestions):
            if cols[i % 2].button(q, key=f"sug_{i}"):
                st.session_state.query_to_run = q
                st.rerun()

    # Empty State or Welcome State
    if not db_path and db_engine == "SQL (SQLite/CSV)":
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1.5rem; background: #0d0d18; border: 1px dashed #1e1a2e; border-radius: 10px; margin-bottom: 1.5rem;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">📁</div>
            <h3 style="margin: 0 0 0.5rem 0; color: #f0f0ff;">No Database Loaded</h3>
            <p style="margin: 0; color: #4a4a6a; font-size: 0.9rem;">Upload a SQLite database, SQL script, or CSV files in the sidebar to get started.</p>
        </div>
        """, unsafe_allow_html=True)
    elif db_engine == "NoSQL (MongoDB)" and st.session_state.mongo_client is None:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1.5rem; background: #0d0d18; border: 1px dashed #1e1a2e; border-radius: 10px; margin-bottom: 1.5rem;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">🍃</div>
            <h3 style="margin: 0 0 0.5rem 0; color: #f0f0ff;">No MongoDB Connection</h3>
            <p style="margin: 0; color: #4a4a6a; font-size: 0.9rem;">Upload JSON collections or enter a connection URI in the sidebar to get started.</p>
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.last_results is None and not st.session_state.error_msg:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1.5rem; background: #0d0d18; border: 1px solid #1e1a2e; border-radius: 10px; margin-bottom: 1.5rem;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">⚡</div>
            <h3 style="margin: 0 0 0.5rem 0; color: #f0f0ff;">Database Ready</h3>
            <p style="margin: 0; color: #4a4a6a; font-size: 0.9rem;">Ask a question in the chat input below or select a suggested question to analyze your data.</p>
        </div>
        """, unsafe_allow_html=True)

    # Query input retrieval and execution logic
    query_to_run = None
    if st.session_state.get("query_to_run"):
        query_to_run = st.session_state.query_to_run
        st.session_state.query_to_run = None

    if query_to_run:
        user_query = query_to_run
        if not api_key:
            st.session_state.error_msg = "🔑 Please enter a Gemini API Key in the sidebar first."
        elif db_engine == "SQL (SQLite/CSV)" and not db_path:
            st.session_state.error_msg = "📁 Please upload a SQLite database (.db or .sqlite) file in the sidebar to query."
        elif db_engine == "NoSQL (MongoDB)" and st.session_state.mongo_client is None:
            st.session_state.error_msg = "📁 Please upload JSON collections or connect to a MongoDB connection URI in the sidebar to query."
        elif not user_query.strip():
            st.session_state.error_msg = "💬 Please enter a valid question."
        else:
            st.session_state.last_query = user_query
            st.session_state.error_msg = ""
            st.session_state.last_sql = ""
            st.session_state.last_results = None
            st.session_state.last_explanation = ""
            
            if db_engine == "SQL (SQLite/CSV)":
                with st.spinner("🧠 Translating question to SQL using Gemini Pro..."):
                    # 1. Format schema information for prompt context
                    schema_context = []
                    for table, info in schema_data.items():
                        schema_context.append(f"Table: {table}")
                        schema_context.append(f"SQL Schema: {info['create_sql']}")
                        if info['samples']:
                            schema_context.append(f"Sample Row: {json.dumps(info['samples'][0])}")
                        schema_context.append("")
                    
                    schema_text = "\n".join(schema_context)
                    
                    # 2. Query Gemini to generate SQL
                    prompt = f"""You are an expert database administrator and SQLite SQL generator.
Your job is to translate the user's natural language question into a valid, executable SQLite query based on the database schema provided below.

=== DATABASE SCHEMA ===
{schema_text}

=== INSTRUCTIONS ===
1. Generate a single valid SQLite query.
2. Return ONLY the raw SQL query. Do not wrap the SQL query in markdown blocks (e.g., do not use ```sql ... ```), do not use backticks, do not include any explanatory text, and do not write anything else. Just the plain SQL code.
3. Ensure you only select columns that exist in the schema.
4. If the question cannot be answered by the database, output a single comment line starting with -- followed by the explanation, e.g., "-- Cannot answer: Column 'X' does not exist."

Question: {user_query}
SQL Query:"""

                    try:
                        # Initialize model
                        model = genai.GenerativeModel(selected_model)
                        response = model.generate_content(prompt)
                        generated_sql = response.text.strip()
                        
                        # Clean up formatting if the model didn't obey instructions
                        if generated_sql.startswith("```"):
                            lines = generated_sql.split("\n")
                            # Remove first line if it starts with ```
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            # Remove last line if it starts with ```
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            generated_sql = "\n".join(lines).strip()
                        
                        # Strip extra SQL specifier if present
                        if generated_sql.lower().startswith("sql"):
                            generated_sql = generated_sql[3:].strip()
                            
                        st.session_state.last_sql = generated_sql
                        
                    except Exception as e:
                        st.session_state.error_msg = f"Gemini API Error: {e}"

                # 3. Execute SQL Query
                if not st.session_state.error_msg:
                    if st.session_state.last_sql.startswith("--"):
                        st.session_state.error_msg = f"Could not answer: {st.session_state.last_sql[2:].strip()}"
                    else:
                        with st.spinner("⚡ Running SQL query..."):
                            try:
                                conn = sqlite3.connect(db_path)
                                # Run and load to dataframe
                                df = pd.read_sql_query(st.session_state.last_sql, conn)
                                st.session_state.last_results = df
                                conn.close()
                            except Exception as e:
                                st.session_state.error_msg = f"SQL Execution Error: {e}"
            else:
                with st.spinner("🧠 Translating question to MongoDB query using Gemini Pro..."):
                    # 1. Format schema info
                    schema_context = []
                    for table, info in schema_data.items():
                        schema_context.append(f"Collection: {table}")
                        schema_context.append(f"Document Count: {info.get('document_count', 0)}")
                        if info['samples']:
                            schema_context.append(f"Sample Document: {json.dumps(info['samples'][0])}")
                        schema_context.append("")
                    
                    schema_text = "\n".join(schema_context)
                    
                    # 2. Query Gemini to generate MQL
                    prompt = f"""You are an expert MongoDB database administrator and MQL (MongoDB Query Language) generator.
Your job is to translate the user's natural language question into a valid, executable MongoDB query JSON block based on the collection schemas provided below.

=== COLLECTION SCHEMAS ===
{schema_text}

=== INSTRUCTIONS ===
1. Generate a valid JSON object matching this structure:
{{
  "collection": "<collection_name>",
  "operation": "find" or "aggregate",
  "query": <query dictionary for find, or list of pipeline stages for aggregate>
}}
2. Return ONLY the raw JSON object. Do not wrap the JSON in markdown blocks (e.g., do not use ```json ... ```), do not use backticks, do not include any explanatory text, and do not write anything else. Just the plain JSON code.
3. Ensure you only query collections and fields that exist in the schemas.
4. If the question cannot be answered, output a single JSON field matching: {{"error": "Cannot answer: Column 'X' does not exist."}}

Question: {user_query}
MongoDB JSON Query:"""

                    try:
                        model = genai.GenerativeModel(selected_model)
                        response = model.generate_content(prompt)
                        generated_mql = response.text.strip()
                        
                        if generated_mql.startswith("```"):
                            lines = generated_mql.split("\n")
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            generated_mql = "\n".join(lines).strip()
                        
                        if generated_mql.lower().startswith("json"):
                            generated_mql = generated_mql[4:].strip()
                            
                        st.session_state.last_sql = generated_mql
                        
                    except Exception as e:
                        st.session_state.error_msg = f"Gemini API Error: {e}"

                # 3. Execute MongoDB Query
                if not st.session_state.error_msg:
                    with st.spinner("⚡ Running MongoDB query..."):
                        try:
                            mql_dict = json.loads(st.session_state.last_sql)
                            if "error" in mql_dict:
                                st.session_state.error_msg = mql_dict["error"]
                            else:
                                collection_name = mql_dict.get("collection")
                                operation = mql_dict.get("operation", "find")
                                query_data = mql_dict.get("query", {})
                                
                                if not collection_name:
                                    raise ValueError("Missing 'collection' field in the generated query.")
                                
                                mongo_db = st.session_state.mongo_client[st.session_state.mongo_db_name]
                                coll = mongo_db[collection_name]
                                
                                if operation == "find":
                                    if not isinstance(query_data, dict):
                                        query_data = {}
                                    cursor = coll.find(query_data)
                                    results = list(cursor)
                                elif operation == "aggregate":
                                    if not isinstance(query_data, list):
                                        query_data = [query_data] if query_data else []
                                    cursor = coll.aggregate(query_data)
                                    results = list(cursor)
                                else:
                                    raise ValueError(f"Unsupported MongoDB operation: {operation}")
                                
                                for doc in results:
                                    if "_id" in doc:
                                        doc["_id"] = str(doc["_id"])
                                
                                df = pd.DataFrame(results)
                                st.session_state.last_results = df
                        except Exception as e:
                            st.session_state.error_msg = f"MongoDB Execution Error: {e}"
            
            # 4. Generate Natural Language Explanation
            if not st.session_state.error_msg and st.session_state.last_results is not None:
                with st.spinner("✍️ Writing explanation..."):
                    results_json = st.session_state.last_results.head(10).to_json(orient='records')
                    
                    if db_engine == "SQL (SQLite/CSV)":
                        explanation_prompt = f"""You are a helpful data analyst.
Explain the results of a SQL query in simple, engaging, natural language.

User's Question: {user_query}
SQL Query Run: {st.session_state.last_sql}
Query Results (JSON, limit 10 rows): {results_json}

=== INSTRUCTIONS ===
1. Summarize the answer to the user's question clearly.
2. Discuss the numbers or records returned, pointing out any interesting insights or patterns.
3. Keep it concise, professional, and friendly.
4. Do not mention technical implementation details like SQL tables or join types unless they are directly relevant to the user's question.
"""
                    else:
                        explanation_prompt = f"""You are a helpful data analyst.
Explain the results of a MongoDB query in simple, engaging, natural language.

User's Question: {user_query}
MongoDB Query Run (JSON): {st.session_state.last_sql}
Query Results (JSON, limit 10 rows): {results_json}

=== INSTRUCTIONS ===
1. Summarize the answer to the user's question clearly.
2. Discuss the numbers or records returned, pointing out any interesting insights or patterns.
3. Keep it concise, professional, and friendly.
4. Do not mention technical implementation details like collections or aggregation pipeline stages unless they are directly relevant to the user's question.
"""
                    try:
                        model = genai.GenerativeModel(selected_model)
                        exp_response = model.generate_content(explanation_prompt)
                        st.session_state.last_explanation = exp_response.text.strip()
                        
                        # Add to history log
                        st.session_state.history.append({
                            "question": user_query,
                            "sql": st.session_state.last_sql,
                            "results": st.session_state.last_results,
                            "explanation": st.session_state.last_explanation
                        })
                    except Exception as e:
                        st.session_state.last_explanation = f"(Explanation generation failed: {e})"
                        st.session_state.history.append({
                            "question": user_query,
                            "sql": st.session_state.last_sql,
                            "results": st.session_state.last_results,
                            "explanation": "No explanation generated."
                        })

    # Render results
    if st.session_state.error_msg:
        st.error(st.session_state.error_msg)
        if st.session_state.last_sql:
            query_label = "Generated MongoDB Query" if db_engine == "NoSQL (MongoDB)" else "Generated SQL"
            query_lang = "json" if db_engine == "NoSQL (MongoDB)" else "sql"
            st.markdown(f'<div class="section-label">{query_label}</div>', unsafe_allow_html=True)
            st.code(st.session_state.last_sql, language=query_lang)

    elif st.session_state.last_results is not None:
        col_main, col_details = st.columns([3, 2])

        with col_main:
            st.markdown('<div class="section-label">Results</div>', unsafe_allow_html=True)
            if st.session_state.last_results.empty:
                st.info("Query ran successfully — no rows matched.")
            else:
                tab_table, tab_chart = st.tabs(["📋 Table View", "📊 Chart Visualisation"])
                
                with tab_table:
                    st.dataframe(st.session_state.last_results, use_container_width=True)
                    csv_data = st.session_state.last_results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Export CSV",
                        data=csv_data,
                        file_name="results.csv",
                        mime="text/csv"
                    )
                
                with tab_chart:
                    df = st.session_state.last_results
                    cols = df.columns.tolist()
                    if len(cols) < 2:
                        st.info("At least 2 columns are required to generate a visualization.")
                    else:
                        col_c1, col_c2, col_c3 = st.columns(3)
                        with col_c1:
                            chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Area", "Scatter", "Pie"], key="chart_type_select")
                        with col_c2:
                            x_axis = st.selectbox("X-Axis (Category/Time)", cols, key="chart_x_axis")
                        with col_c3:
                            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                            y_default = numeric_cols if numeric_cols else cols
                            y_axis = st.multiselect("Y-Axis (Values)", cols, default=y_default[:1], key="chart_y_axis")
                        
                        if not y_axis:
                            st.warning("Please select at least one Y-Axis column.")
                        else:
                            try:
                                if chart_type == "Bar":
                                    st.bar_chart(df, x=x_axis, y=y_axis)
                                elif chart_type == "Line":
                                    st.line_chart(df, x=x_axis, y=y_axis)
                                elif chart_type == "Area":
                                    st.area_chart(df, x=x_axis, y=y_axis)
                                elif chart_type == "Scatter":
                                    st.scatter_chart(df, x=x_axis, y=y_axis)
                                elif chart_type == "Pie":
                                    fig = px.pie(df, names=x_axis, values=y_axis[0])
                                    fig.update_layout(
                                        template="plotly_dark",
                                        paper_bgcolor="rgba(0,0,0,0)",
                                        plot_bgcolor="rgba(0,0,0,0)",
                                        font=dict(color="#c9c9d9"),
                                        margin=dict(t=20, b=20, l=20, r=20)
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                            except Exception as chart_err:
                                st.error(f"Error rendering chart: {chart_err}")

            st.markdown('<div class="section-label" style="margin-top:1.5rem">Explanation</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="explanation-block">{st.session_state.last_explanation}</div>', unsafe_allow_html=True)

        with col_details:
            query_label = "Generated MongoDB Query" if db_engine == "NoSQL (MongoDB)" else "Generated SQL"
            query_lang = "json" if db_engine == "NoSQL (MongoDB)" else "sql"
            st.markdown(f'<div class="section-label">{query_label}</div>', unsafe_allow_html=True)
            st.code(st.session_state.last_sql, language=query_lang)

            n_rows = len(st.session_state.last_results)
            n_cols = len(st.session_state.last_results.columns)
            st.markdown(f"""
<div class="stat-row">
    <div class="stat-pill"><strong>{n_rows}</strong> rows</div>
    <div class="stat-pill"><strong>{n_cols}</strong> columns</div>
    <div class="stat-pill"><strong>{selected_model}</strong></div>
</div>
""", unsafe_allow_html=True)

# Schema tab
with tab_schema_details:
    if not schema_data:
        st.info("Upload a database or connect to a data source to inspect its schema here.")
    else:
        st.markdown('<div class="section-label">Schema Definitions</div>', unsafe_allow_html=True)
        for idx, (tbl_name, info) in enumerate(schema_data.items()):
            with st.expander(tbl_name, expanded=(idx == 0)):
                col_t1, col_t2 = st.columns([1, 2])
                with col_t1:
                    st.markdown(f'<div class="table-name-tag">{tbl_name}</div>', unsafe_allow_html=True)
                    cols_df = pd.DataFrame(info["columns"])
                    if not cols_df.empty:
                        cols_df = cols_df.rename(columns={"name": "Column/Field", "type": "Type", "pk": "Primary Key"})
                        if "notnull" in cols_df.columns:
                            cols_df = cols_df.rename(columns={"notnull": "Not Null"})
                        cols_df = cols_df[[c for c in ["Column/Field", "Type", "Not Null", "Primary Key"] if c in cols_df.columns]]
                        st.table(cols_df)
                with col_t2:
                    if db_engine == "NoSQL (MongoDB)":
                        st.markdown(f"**Document Count:** `{info.get('document_count', 0)}`")
                    else:
                        st.code(info["create_sql"], language="sql")
                    if info["samples"]:
                        st.caption("Sample documents" if db_engine == "NoSQL (MongoDB)" else "Sample rows")
                        st.dataframe(pd.DataFrame(info["samples"]), use_container_width=True)

# History tab
with tab_history:
    if not st.session_state.history:
        st.info("No queries yet. Results will appear here after you run your first question.")
    else:
        st.markdown('<div class="section-label">Query History</div>', unsafe_allow_html=True)
        for idx, item in enumerate(reversed(st.session_state.history)):
            with st.expander(item['question'], expanded=(idx == 0)):
                col_h1, col_h2 = st.columns([1, 1])
                with col_h1:
                    is_json_query = item['sql'].strip().startswith("{")
                    h_lang = "json" if is_json_query else "sql"
                    st.caption("MongoDB Query" if is_json_query else "SQL")
                    st.code(item['sql'], language=h_lang)
                with col_h2:
                    st.caption("Explanation")
                    st.markdown(f'<div class="explanation-block" style="font-size:0.85rem">{item["explanation"]}</div>', unsafe_allow_html=True)
                st.caption("Preview")
                st.dataframe(item['results'].head(5), use_container_width=True)

# ----------------- GLOBAL CHAT INPUT -----------------
chat_query = st.chat_input("Ask a question about your database...")
if chat_query:
    st.session_state.query_to_run = chat_query
    st.rerun()
