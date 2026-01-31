import streamlit as st
import pandas as pd
from datetime import timedelta
import calendar
import re

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(page_title="Leave Normalization Tool", layout="wide")
st.title("📋 Leave Normalization Tool")
st.caption("Upload RAW HR leave export – app auto-cleans & normalizes")

# --------------------------------------------------
# File upload
# --------------------------------------------------
file = st.file_uploader(
    "Upload RAW Leave Data (CSV or Excel)",
    type=["csv", "xlsx"]
)

if not file:
    st.info("⬆️ Upload a CSV or Excel file to start")
    st.stop()

# --------------------------------------------------
# Read file
# --------------------------------------------------
if file.name.endswith(".csv"):
    raw_df = pd.read_csv(file)
else:
    raw_df = pd.read_excel(file, engine="openpyxl")

# --------------------------------------------------
# RAW DATA FILTER + VIEW
# --------------------------------------------------
st.subheader("🔍 Filter – Raw Uploaded Data")

raw_emp = st.multiselect(
    "EmployeeCode (Raw)",
    options=sorted(raw_df["EmployeeCode"].dropna().unique())
)

raw_status = st.multiselect(
    "Status (Raw)",
    options=sorted(raw_df["Status"].dropna().unique())
)

filtered_raw_df = raw_df.copy()

if raw_emp:
    filtered_raw_df = filtered_raw_df[filtered_raw_df["EmployeeCode"].isin(raw_emp)]

if raw_status:
    filtered_raw_df = filtered_raw_df[filtered_raw_df["Status"].isin(raw_status)]

st.subheader("📥 H-Factor Raw Data")
st.dataframe(filtered_raw_df, use_container_width=True)

# --------------------------------------------------
# Detect month from file name
# --------------------------------------------------
month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
file_name = file.name.lower()

detected_month = None
for name, num in month_map.items():
    if re.search(name, file_name):
        detected_month = num
        break

if not detected_month:
    st.error("❌ Month name not found in file name (e.g. January, Feb)")
    st.stop()

st.success(f"📆 Detected Month: {calendar.month_name[detected_month]}")

# --------------------------------------------------
# Required column mapping
# --------------------------------------------------
COLUMN_MAP = {
    "EmployeeCode": "EmployeeCode",
    "LeaveType": "LeaveType",          # ✅ ADD THIS
    "AppliedFrom": "AppliedFrom",
    "AppliedTill": "AppliedTill",
    "FromSession": "FromSession",
    "ToSession": "ToSession",
    "NrOfDays": "NumberOfDays",
    "AppliedOn": "AppliedOn",
    "ApplierRemarks": "ApplierRemarks",
    "Status": "Status",
}


missing = [c for c in COLUMN_MAP if c not in raw_df.columns]
if missing:
    st.error(f"❌ Missing required columns in RAW data: {missing}")
    st.stop()

# --------------------------------------------------
# Clean + refine data
# --------------------------------------------------
df = raw_df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)

df["FromSession"] = df["FromSession"].str.strip().str.title()
df["ToSession"] = df["ToSession"].str.strip().str.title()

for col in ["AppliedFrom", "AppliedTill", "AppliedOn"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")

if df[["AppliedFrom", "AppliedTill"]].isnull().any().any():
    st.error("❌ Invalid dates found in AppliedFrom / AppliedTill")
    st.stop()

# --------------------------------------------------
# Filter data by detected month
# --------------------------------------------------
df = df[
    (df["AppliedFrom"].dt.month == detected_month) &
    df["Status"] = df["Status"].astype(str)
]

if df.empty:
    st.warning("⚠️ No leave records found for detected month")
    st.stop()

# --------------------------------------------------
# MONTH DATA FILTER + VIEW
# --------------------------------------------------
st.subheader("🔍 Filter – Month Leave Data")

m_emp = st.multiselect(
    "EmployeeCode (Month)",
    options=sorted(df["EmployeeCode"].unique())
)

m_status = st.multiselect(
    "Status (Month)",
    options=sorted(df["Status"].unique())
)

filtered_month_df = df.copy()

if m_emp:
    filtered_month_df = filtered_month_df[filtered_month_df["EmployeeCode"].isin(m_emp)]

if m_status:
    filtered_month_df = filtered_month_df[filtered_month_df["Status"].isin(m_status)]

st.subheader("📆 Month-filtered Leave Data")
st.dataframe(filtered_month_df, use_container_width=True)

# --------------------------------------------------
# Normalize Leave Logic
# --------------------------------------------------
output_rows = []

for _, row in filtered_month_df.iterrows():
    emp = row["EmployeeCode"]
    leave_type = row["LeaveType"]   
    start = row["AppliedFrom"]
    end = row["AppliedTill"]
    from_sess = row["FromSession"]
    to_sess = row["ToSession"]
    applied_on = row["AppliedOn"]
    remarks = row["ApplierRemarks"]
    status = row["Status"]

    # Full day
    if from_sess == "First Session" and to_sess == "Second Session":
        days = (end - start).days + 1
        output_rows.append([
            emp,leave_type, start, end, from_sess, to_sess,
            days, applied_on, remarks, status
        ])
        continue

    full_start = start
    full_end = end

    if from_sess == "Second Session":
        output_rows.append([
            emp, start, start,
            "Second Session", "Second Session",
            0.5, applied_on, remarks, status
        ])
        full_start = start + timedelta(days=1)

    if to_sess == "First Session":
        output_rows.append([
            emp, end, end,
            "First Session", "First Session",
            0.5, applied_on, remarks, status
        ])
        full_end = end - timedelta(days=1)

    if full_start <= full_end:
        days = (full_end - full_start).days + 1
        if days > 0:
            output_rows.append([
                emp, full_start, full_end,
                "First Session", "Second Session",
                days, applied_on, remarks, status
            ])

# --------------------------------------------------
# Normalized Output + FILTER + DOWNLOAD
# --------------------------------------------------
result = pd.DataFrame(
    output_rows,
    columns=[
    "EmployeeCode",
    "LeaveType",          # ✅ ADD
    "AppliedFrom",
    "AppliedTill",
    "FromSession",
    "ToSession",
    "NumberOfDays",
    "AppliedOn",
    "ApplierRemarks",
    "Status"
]

).sort_values(["EmployeeCode", "AppliedFrom"])

st.subheader("🔍 Filter – Normalized Leave")

n_emp = st.multiselect(
    "EmployeeCode (Normalized)",
    options=sorted(result["EmployeeCode"].unique())
)

filtered_result = result.copy()
if n_emp:
    filtered_result = filtered_result[filtered_result["EmployeeCode"].isin(n_emp)]

st.subheader("✅ Normalized Leave Output (0.5 leave splited)")
st.dataframe(filtered_result, use_container_width=True)

st.download_button(
    "⬇️ Download Normalized Leave CSV",
    filtered_result.to_csv(index=False).encode("utf-8"),
    "normalized_leave.csv",
    "text/csv"
)

# --------------------------------------------------
# Payroll / Zoho Table + FILTER + DOWNLOAD
# --------------------------------------------------
SESSION_MAP = {
    ("First Session", "First Session"): 1,
    ("Second Session", "Second Session"): 2,
    ("First Session", "Second Session"): 0,
}

payroll_df = pd.DataFrame({
    "Employee ID": filtered_result["EmployeeCode"],
    "Leave Type": filtered_result["LeaveType"],   # ✅ FROM RAW DATA
    "Unit": "Day",
    "From": filtered_result["AppliedFrom"],
    "To": filtered_result["AppliedTill"],
    "Session": [
        SESSION_MAP.get((f, t))
        for f, t in zip(filtered_result["FromSession"], filtered_result["ToSession"])
    ],
    "Start Time": "",
    "Days/Hours Taken": filtered_result["NumberOfDays"],
    "Reason for leave": filtered_result["ApplierRemarks"],
})


st.subheader("🔍 Filter – Zoho Payroll Data")

p_emp = st.multiselect(
    "Employee ID (Payroll)",
    options=sorted(payroll_df["Employee ID"].unique())
)

filtered_payroll = payroll_df.copy()
if p_emp:
    filtered_payroll = filtered_payroll[filtered_payroll["Employee ID"].isin(p_emp)]

st.subheader("📄 Zoho Formatted Data")
st.dataframe(filtered_payroll, use_container_width=True)

st.download_button(
    "⬇️ Download Payroll CSV",
    filtered_payroll.to_csv(index=False).encode("utf-8"),
    "payroll_leave.csv",
    "text/csv"
)
