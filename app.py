import streamlit as st
import pandas as pd
from datetime import timedelta

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(page_title="Leave Normalization Tool", layout="wide")

st.title("📋 Leave Normalization Tool")
st.caption("Normalize leave data into payroll-safe format")

# --------------------------------------------------
# File upload
# --------------------------------------------------
file = st.file_uploader(
    "Upload Leave Data (CSV or Excel)",
    type=["csv", "xlsx"]
)

if not file:
    st.info("⬆️ Upload a CSV or Excel file to start")
    st.stop()

# --------------------------------------------------
# Read file
# --------------------------------------------------
try:
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine="openpyxl")
except ImportError:
    st.error(
        "Excel upload requires `openpyxl`. "
        "Add it to requirements.txt or upload CSV."
    )
    st.stop()

st.subheader("📥 Uploaded Data")
st.dataframe(df, use_container_width=True)

# --------------------------------------------------
# Validation
# --------------------------------------------------
required_columns = [
    "EmployeeCode",
    "AppliedFrom",
    "AppliedTill",
    "FromSession",
    "ToSession",
    "NumberOfDays",
    "AppliedOn",
    "ApplierRemarks",
]

missing = [c for c in required_columns if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# --------------------------------------------------
# Normalize Leave Logic
# --------------------------------------------------
output_rows = []

for _, row in df.iterrows():
    emp = row["EmployeeCode"]
    start = pd.to_datetime(row["AppliedFrom"])
    end = pd.to_datetime(row["AppliedTill"])
    from_sess = row["FromSession"]
    to_sess = row["ToSession"]
    days = float(row["NumberOfDays"])
    applied_on = row["AppliedOn"]
    remarks = row["ApplierRemarks"]
    status = row.get("Status", "Approved")

    # ---------- Case 1: Pure full-day leave ----------
    if (
        days.is_integer()
        and from_sess == "First Session"
        and to_sess == "Second Session"
    ):
        output_rows.append([
            emp, start, end,
            from_sess, to_sess,
            int(days),
            applied_on, remarks, status
        ])
        continue

    # ---------- Case 2: Half-day involved ----------
    full_start = start
    full_end = end

    # Start half
    if from_sess == "Second Session":
        output_rows.append([
            emp, start, start,
            "Second Session", "Second Session",
            0.5, applied_on, remarks, status
        ])
        full_start = start + timedelta(days=1)

    # End half
    if to_sess == "First Session":
        output_rows.append([
            emp, end, end,
            "First Session", "First Session",
            0.5, applied_on, remarks, status
        ])
        full_end = end - timedelta(days=1)

    # Middle full days (aggregated)
    if full_start <= full_end:
        full_days = (full_end - full_start).days + 1
        if full_days > 0:
            output_rows.append([
                emp, full_start, full_end,
                "First Session", "Second Session",
                full_days, applied_on, remarks, status
            ])

# --------------------------------------------------
# Normalized Output
# --------------------------------------------------
result = pd.DataFrame(
    output_rows,
    columns=[
        "EmployeeCode",
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

st.subheader("✅ Normalized Output")
st.dataframe(result, use_container_width=True)

# --------------------------------------------------
# Download Normalized Output
# --------------------------------------------------
normalized_csv = result.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Normalized Leave Data",
    data=normalized_csv,
    file_name="normalized_leave_data.csv",
    mime="text/csv"
)

# --------------------------------------------------
# HR / Payroll Table
# --------------------------------------------------
def map_session(from_sess, to_sess):
    if from_sess == "First Session" and to_sess == "First Session":
        return 1   # First half
    if from_sess == "Second Session" and to_sess == "Second Session":
        return 2   # Second half
    if from_sess == "First Session" and to_sess == "Second Session":
        return 0   # Full day
    return None

payroll_df = pd.DataFrame({
    "Employee ID": result["EmployeeCode"],
    "Leave Type": "Leave",
    "Unit": "Day",
    "From": result["AppliedFrom"],
    "To": result["AppliedTill"],
    "Session": [
        map_session(f, t)
        for f, t in zip(result["FromSession"], result["ToSession"])
    ],
    "Start Time": "",
    "Days/Hours Taken": result["NumberOfDays"],
    "Reason for leave": result["ApplierRemarks"],
})

st.subheader("📄 HR / Payroll Format")
st.dataframe(payroll_df, use_container_width=True)

# --------------------------------------------------
# Download HR / Payroll Output
# --------------------------------------------------
payroll_csv = payroll_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download HR / Payroll Leave Data",
    data=payroll_csv,
    file_name="hr_payroll_leave_data.csv",
    mime="text/csv"
)
