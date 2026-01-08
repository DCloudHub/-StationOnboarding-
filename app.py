import json
import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import datetime
import traceback
import hashlib
import time

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# ---------- Streamlit config ----------

st.set_page_config(
    page_title="Station Location Tracker",
    page_icon="📍",
    layout="centered"
)

st.title("📍 Station Location Registration")
st.markdown("---")

# ---------- Constants ----------

MAX_FILE_MB = 10
SUPPORTED_EXTENSIONS = (".csv", ".xls", ".xlsx")

# ---------- Session state ----------

if "last_import_hash" not in st.session_state:
    st.session_state.last_import_hash = None

# ---------- Helper functions ----------

def get_gsheet_client():
    """
    Create a gspread client from a service account stored in st.secrets["gcp_service_account"].
    The secret may be a dict/object (preferred) or a JSON string.
    """
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Missing Google service account in Streamlit secrets (gcp_service_account).")

    service_account = st.secrets["gcp_service_account"]
    if isinstance(service_account, str):
        try:
            service_account = json.loads(service_account)
        except Exception as exc:
            raise RuntimeError("Invalid JSON in gcp_service_account secret.") from exc

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(service_account, scopes=scopes)
    return gspread.authorize(creds)

def extract_spreadsheet_id(value: str) -> str:
    """
    Accept either a full Google Sheets URL or just the spreadsheet ID.
    Returns empty string when input is falsy.
    """
    if not value:
        return ""
    value = value.strip()
    if "docs.google.com" in value and "/d/" in value:
        return value.split("/d/")[1].split("/")[0]
    return value

def append_dataframe_to_sheet(client, spreadsheet_id, df, worksheet_name="Sheet1"):
    """
    Append DataFrame rows to worksheet. If worksheet does not exist it is created.
    If sheet is empty, headers are written first.
    """
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        # gspread expects integers for rows/cols
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=20)

    existing = ws.get_all_values()
    rows = df.values.tolist()

    if not existing:
        # Prepend header row
        ws.append_rows([df.columns.tolist()] + rows, value_input_option="USER_ENTERED")
    else:
        ws.append_rows(rows, value_input_option="USER_ENTERED")

def hash_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()

@st.cache_data(show_spinner=False)
def load_dataframe_cached(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Load bytes into a pandas DataFrame.
    Uses filename extension when available; otherwise tries CSV then Excel as fallback.
    """
    bio = BytesIO(file_bytes)
    name_lower = (filename or "").lower()

    # Try to use extension if present
    try:
        if name_lower.endswith(".csv"):
            return pd.read_csv(bio)
        if name_lower.endswith((".xls", ".xlsx")):
            return pd.read_excel(bio)
    except Exception:
        # Fall through to more forgiving attempts below
        pass

    # Fallback attempts
    bio.seek(0)
    try:
        return pd.read_csv(bio)
    except Exception:
        bio.seek(0)
        return pd.read_excel(bio)

def normalize_and_validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize incoming DataFrame to columns: Name, Station, Timestamp.
    Accepts case-insensitive column names for Name/Station/Timestamp.
    Raises ValueError if Name or Station columns are missing.
    """
    lower_cols = {c.lower(): c for c in df.columns}
    if "name" not in lower_cols or "station" not in lower_cols:
        raise ValueError(f"Required columns missing. Found: {list(df.columns)}")

    df = df.rename(columns={
        lower_cols["name"]: "Name",
        lower_cols["station"]: "Station",
    })

    # Normalize Timestamp if present case-insensitively
    if "timestamp" in lower_cols:
        df = df.rename(columns={lower_cols["timestamp"]: "Timestamp"})

    if "Timestamp" not in df.columns:
        df["Timestamp"] = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")

    # Ensure only the expected columns are returned in a stable order
    return df[["Name", "Station", "Timestamp"]]

# ---------- Registration form ----------

with st.form("registration"):
    name = st.text_input("Client Name")
    station = st.selectbox("Station", ["Central", "North", "South", "West"])
    spreadsheet_input = st.text_input("Google Sheet URL or ID (optional)")
    worksheet_name_input = st.text_input("Worksheet name", value="Sheet1")
    submitted = st.form_submit_button("Register")

if submitted:
    if not name:
        st.error("Please enter a name")
    else:
        st.success(f"✅ {name} registered at {station}")
        spreadsheet_id = extract_spreadsheet_id(spreadsheet_input or st.secrets.get("spreadsheet_id", ""))
        if spreadsheet_id:
            try:
                client = get_gsheet_client()
                df = pd.DataFrame([{
                    "Name": name,
                    "Station": station,
                    "Timestamp": datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
                }])
                append_dataframe_to_sheet(client, spreadsheet_id, df, worksheet_name_input)
                st.info("Saved to Google Sheet.")
            except Exception as e:
                st.error(f"Failed to save: {e}")
                st.text_area("Traceback", traceback.format_exc(), height=200)

st.markdown("---")

# ---------- Import section ----------

st.header("📥 Import registrations from file URL")

file_url = st.text_input("CSV / XLS / XLSX public file URL")
spreadsheet_input2 = st.text_input("Destination Google Sheet URL or ID")
worksheet_name = st.text_input("Destination worksheet", value="Sheet1")

if st.button("Preview file"):
    if not file_url:
        st.error("Please provide a file URL to preview.")
    else:
        try:
            r = requests.get(file_url, timeout=30)
            r.raise_for_status()

            size_mb = len(r.content) / (1024 * 1024)
            if size_mb > MAX_FILE_MB:
                st.error(f"File too large ({size_mb:.1f} MB). Limit is {MAX_FILE_MB} MB.")
                st.stop()

            df_preview = load_dataframe_cached(r.content, file_url)
            st.subheader("Preview (first 20 rows)")
            st.dataframe(df_preview.head(20))
            st.caption(f"Rows: {len(df_preview)} | Columns: {list(df_preview.columns)}")

        except Exception as e:
            st.error(f"Preview failed: {e}")
            st.text_area("Traceback", traceback.format_exc(), height=200)

if st.button("Import to Google Sheet"):
    if not file_url:
        st.error("Please provide a file URL to import.")
    else:
        try:
            with st.spinner("Downloading and processing file..."):
                r = requests.get(file_url, timeout=30)
                r.raise_for_status()

            file_hash = hash_bytes(r.content)
            if file_hash == st.session_state.last_import_hash:
                st.warning("This file has already been imported in this session.")
                st.stop()

            df = load_dataframe_cached(r.content, file_url)
            df = normalize_and_validate(df)

            spreadsheet_id = extract_spreadsheet_id(spreadsheet_input2 or st.secrets.get("spreadsheet_id", ""))
            if not spreadsheet_id:
                st.error("No destination Google Sheet provided.")
                st.stop()

            progress = st.progress(0)
            client = get_gsheet_client()
            time.sleep(0.3)
            progress.progress(50)

            append_dataframe_to_sheet(client, spreadsheet_id, df, worksheet_name)
            progress.progress(100)

            st.session_state.last_import_hash = file_hash
            st.success(f"Imported {len(df)} rows successfully.")

        except Exception as e:
            st.error(f"Import failed: {e}")
            st.text_area("Traceback", traceback.format_exc(), height=300)

st.markdown("---")
st.caption(
    "Notes:\n"
    "- CSV, XLS, XLSX supported\n"
    "- Max file size: 10 MB\n"
    "- Sheet must be shared with the service account email\n"
    "- Duplicate imports are prevented per session"
)
