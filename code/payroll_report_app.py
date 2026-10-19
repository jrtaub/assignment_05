"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
# --- The page ---------------------------------------------------------------------
#
# No scaffolding. Every function this page needs already exists in the payroll
# package, and every widget it needs you used in Assignments 03 and 04 — plus two
# new ones, st.date_input and st.bar_chart. README Step 8 has the exact widgets,
# keys and labels; the tests in tests/test_pipeline.py -k app check them.
#
# The shape, in words:
#
#   title and a sentence of instructions
#   roster   <- load_employees()                           (fixed; not uploaded)
#   uploads  <- st.file_uploader, key="exports", accept_multiple_files=True
#               (an empty list until files are chosen)
#   if there are uploads:
#       history <- build_history([load_export(u) for u in uploads], roster)
#       st.warning naming any employeeid with no department (not on the roster);
#           the reports below use only the rows that matched
#       st.selectbox, key="department": "All" plus each department
#       st.date_input, key="dates": a (start, end) range, defaulting to the first
#           and last pay_date — compare against pay_date.dt.date to filter
#       the selection as a subheader
#       four st.metric cards in st.columns(4): Weeks, Employees, Total hours,
#           Total gross pay — counts are .nunique(), totals are .sum()
#       st.bar_chart of pay_by_month(selected), with month as the x axis
#       st.dataframe of summarize_employees(selected)
#       st.dataframe of hours_grid(selected), then of missed_weeks(that grid)
#       st.download_button, key="download": pay_by_month(...).to_csv(index=False)
#
# What the page does NOT do: cleaning, grouping, pivoting. If you find yourself
# writing a groupby or a pivot_table here, that logic belongs in the package.
import streamlit as st
import pandas as pd

from payroll import (
    load_employees,
    load_export,
    build_history,
    summarize_employees,
    hours_grid,
    missed_weeks,
    pay_by_month,
)

st.title("Salt City Coffee — Quarterly Payroll Report")
st.subheader("Upload the weekly payroll exports for the period you want to review - old spreadsheet weeks and new app weeks can be mixed. The roster is loaded automatically.")
st.write("Select department and data range to explore payroll data for the quarter.")

roster = load_employees()

uploads = st.file_uploader(
    "Upload weekly payroll exports",
    accept_multiple_files=True,
    key="exports"
)

if not uploads:
    st.info("Upload weekly payroll exports to view the report.")
    st.stop()

exports = [load_export(upload) for upload in uploads]
history = build_history(exports, roster)

roster_ids = set(roster["employee_id"])
uploaded_ids = set(history["employee_id"])

unmatched_ids = uploaded_ids - roster_ids



if unmatched_ids:
    original_ids = history[
        history["employee_id"].isin(unmatched_ids)
    ]["employeeid"].unique()

    st.warning(
        f"Unknown employee IDs found: {', '.join(sorted(original_ids))}"
    )

matched = history[history["employee_id"].isin(roster_ids)]

departments = ["All"] + sorted(matched["department"].unique())
selected_department = st.selectbox("Select Department", departments, key="department")

min_date = matched["pay_date"].min().date()
max_date = matched["pay_date"].max().date()

date_range = st.date_input(
    "Select date range",
    value=(min_date, max_date),
    key="dates"
)
start_date, end_date = date_range

selected = matched.copy()

if selected_department != "All":
    selected = selected[selected["department"] == selected_department]

selected = selected[
    (selected["pay_date"].dt.date >= start_date) &
    (selected["pay_date"].dt.date <= end_date)
]

st.subheader(f"Payroll data: {selected_department}, from {start_date} to {end_date}")

weeks = selected["week_ending"].nunique()
employees_count = selected["employee_id"].nunique()
total_hours = selected["hours_worked"].sum()
total_pay = selected["gross_pay"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Weeks", weeks)
col2.metric("Employees", employees_count)
col3.metric("Total hours", f"{total_hours:,.2f}")
col4.metric("Total gross pay", f"${total_pay:,.2f}")

pay_by_month_df = pay_by_month(selected)
st.bar_chart(pay_by_month_df.set_index("month"))

st.header("Employees")
st.dataframe(summarize_employees(selected), hide_index=True)

st.header("Hours by week")
st.write("0 means the employee was not paid that week.")
grid = hours_grid(selected)
st.dataframe(grid, hide_index=True)

st.header("Missed weeks")
missed = missed_weeks(grid)
st.dataframe(missed, hide_index=True)

csv_data = pay_by_month_df.to_csv(index=False)
st.download_button(
    label="Download pay by month CSV",
    data=csv_data,
    file_name="pay_by_month.csv",
    mime="text/csv",
    key="download"
)