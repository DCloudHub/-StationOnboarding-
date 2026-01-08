import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import datetime
import traceback

# Google Sheets auth
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Station Location Tracker",
    page_icon="📍",
    layout="centered"
)

st.title("📍 Station Location Registration")
st.markdown("---")

# ---------- Helper functions ----------

def get_gsheet_client():
    """
    Create a gspread client using service account info stored in streamlit secrets.
    The secret should be a dict-like structure named "gcp_service_account".
    """
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            "Google service account JSON not found in Streamlit secrets as 'gcp_service_account'. "
            "See app instructions to add it."
        )

    service_account_info = st.secrets["gcp_service_account"]
    # service_account_info should be a dict; streamlit will parse TOML into a dict if provided correctly.
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def extract_spreadsheet_id(value: str) -> str:
    """
    Accept spreadsheet URL or ID and return the spreadsheet id.
    """
    if not value:
        return ""
    # common URL format: https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/...
    if "docs.google.com" in value and "/d/" in value:
        parts = value.split("/d/")
        if len(parts) > 1:
            id_part = parts[1].split("/")[0]
            return id_part
    # otherwise assume it's an ID already
    return value.strip()

def append_dataframe_to_sheet(client, spreadsheet_id: str, df: pd.DataFrame, worksheet_name="Sheet1"):
    """
    Append dataframe rows to the given worksheet. If worksheet is empty it will write headers first.
    """
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows="1000", cols="20")
    existing = ws.get_all_values()

    rows = df.values.tolist()
    # If sheet is empty, write headers first
    if not existing:
        header = [df.columns.tolist()]
        ws.append_rows(header + rows, value_input_option="USER_ENTERED")
    else:
        ws.append_rows(rows, value_input_option="USER_ENTERED")

# ---------- Registration form (existing) ----------

with st.form("registration"):
    name = st.text_input("Client Name")
    station = st.selectbox("Station", ["Central", "North", "South", "West"])
    spreadsheet_input = st.text_input(
        "Google Sheet URL or ID (optional — store in secrets or paste here to enable saving)",
        value=""
    )
    worksheet_name_input = st.text_input("Worksheet name (default 'Sheet1')", value="Sheet1")

    if st.form_submit_button("Register"):
        if name:
            st.success(f"✅ {name} registered at {station} Station!")
            st.balloons()

            # If a spreadsheet is provided (either in secrets or pasted), try to append the single registration
            spreadsheet_id = extract_spreadsheet_id(spreadsheet_input or st.secrets.get("spreadsheet_id", ""))
            if spreadsheet_id:
                try:
                    client = get_gsheet_client()
                    ts = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
                    df = pd.DataFrame([{"Name": name, "Station": station, "Timestamp": ts}])
                    append_dataframe_to_sheet(client, spreadsheet_id, df, worksheet_name=worksheet_name_input or "Sheet1")
                    st.info("Saved registration to Google Sheet.")
                except Exception as e:
                    st.error(f"Failed to save to Google Sheet: {e}")
                    st.debug(traceback.format_exc())
        else:
            st.error("Please enter a name")

st.info("Share this app link to collect locations automatically.")
st.markdown("---")

# ---------- Import from XLS/XLSX URL ----------

st.header("Import registrations from an XLS/XLSX file link")

st.markdown(
    "Paste a public URL to an .xls/.xlsx file (HTTP/HTTPS). The file should have columns with names like "
    "`Name` and `Station`. A `Timestamp` column will be added automatically if absent."
)

xls_url = st.text_input("XLS/XLSX file URL")
spreadsheet_input2 = st.text_input(
    "Destination Google Sheet URL or ID",
    value=""
)
worksheet_name = st.text_input("Destination worksheet name", value="Sheet1")

if st.button("Import to Google Sheet"):
    if not xls_url:
        st.error("Please provide an XLS/XLSX file URL")
    else:
        try:
            r = requests.get(xls_url, timeout=30)
            r.raise_for_status()
            content = BytesIO(r.content)
            # pandas will choose engine; for .xls you may need 'xlrd' installed, for .xlsx 'openpyxl'
            df = pd.read_excel(content)
            if df.empty:
                st.warning("The spreadsheet you uploaded contains no rows.")
            else:
                # Normalize columns to expected names (case-insensitive)
                col_map = {c: c for c in df.columns}
                # Ensure Name and Station columns exist
                lower_cols = {c.lower(): c for c in df.columns}
                if "name" not in lower_cols or "station" not in lower_cols:
                    st.warning(
                        "Imported file does not contain both 'Name' and 'Station' columns (case-insensitive). "
                        f"Found columns: {list(df.columns)}"
                    )
                else:
                    # Rename to canonical column names
                    df = df.rename(columns={lower_cols["name"]: "Name", lower_cols["station"]: "Station"})
                    # Add Timestamp if not present
                    if "Timestamp" not in df.columns:
                        ts_now = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
                        df["Timestamp"] = ts_now
                    # Prepare destination spreadsheet id
                    spreadsheet_id = extract_spreadsheet_id(spreadsheet_input2 or st.secrets.get("spreadsheet_id", ""))
                    if not spreadsheet_id:
                        st.error("No destination spreadsheet provided. Either paste it above or set 'spreadsheet_id' in Streamlit secrets.")
                    else:
                        client = get_gsheet_client()
                        append_dataframe_to_sheet(client, spreadsheet_id, df, worksheet_name=worksheet_name or "Sheet1")
                        st.success(f"Imported {len(df)} rows to Google Sheet.")
        except Exception as e:
            st.error(f"Failed to import file: {e}")
            st.debug(traceback.format_exc())

st.markdown("---")
st.markdown(
    "Notes:\n"
    "- For .xls files you may need the `xlrd` package (old versions) installed. For .xlsx you need `openpyxl`.\n"
    "- Make sure the Google Sheet is shared with the service account email of your credentials so it can write to it."
)
