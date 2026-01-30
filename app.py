import streamlit as st
import pandas as pd
from datetime import timedelta

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(
    page_title="Leave Normalization Tool",
    layout="wide"
)

st.title("📋 Leave Normalization Tool")
st.caption(
    "Converts mixed-session leave records into clean, payroll-safe rows "
    "(0.5 day or aggregated full days)"
)

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
if file.name.endswith(".csv"):
    df = pd.read_csv(file)
else:
    df = pd.read_excel(file)

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

missing_cols = [c for c in required_columns if c not in df.columns]
if missing_cols:
    st.error(f"❌ Missing required columns: {missing_cols}")
    st.stop()

# --------------------------------------------------
# Normalization Logic
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

    # --------------------------------------------------
    # CASE 1: Pure full-day leave (NO conversion)
    # --------------------------------------------------
    if (
        days.is_integer()
        and from_sess == "First Session"
        and to_sess == "Second Session"
    ):
        output_rows.append([
            emp,
            start,
            end,
            from_sess,
            to_sess,
            int(days),
            applied_on,
            remarks,
            status
        ])
        continue

    # --------------------------------------------------
    # CASE 2: Half-day involved → convert
    # --------------------------------------------------
    full_start = start
    full_end = end

    # Start half day
    if from_sess == "Second Session":
        output_rows.append([
            emp,
            start,
            start,
            "Second Session",
            "Second Session",
            0.5,
            applied_on,
            remarks,
            status
        ])
        full_start = start + timedelta(days=1)

    # End half day
    if to_sess == "First Session":
        output_rows.append([
            emp,
            end,
            end,
            "First Session",
            "First Session",
            0.5,
            applied_on,
            remarks,
            status
        ])
        full_end = end - timedelta(days=1)

    # Middle full days (AGGREGATED)
    if full_start <= full_end:
        full_days = (full_end - full_start).days + 1
        if full_days > 0:
            output_rows.append([
                emp,
                full_start,
                full_end,
                "First Session",
                "Second Session",
                full_days,
                applied_on,
                remarks,
                status
            ])

# --------------------------------------------------
# Output dataframe
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
).sort_values(
    ["EmployeeCode", "AppliedFrom"]
)

st.subheader("✅ Normalized Output")
st.dataframe(result, use_container_width=True)

# --------------------------------------------------
# Download
# --------------------------------------------------
csv_data = result.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Converted CSV",
    data=csv_data,
    file_name="normalized_leave_data.csv",
    mime="text/csv"
)
