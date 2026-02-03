import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="E-Commerce Dashboard (Superstore)", layout="wide")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="latin1")

    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
        df = df.dropna(subset=["Order Date"])

    if "Ship Date" in df.columns:
        df["Ship Date"] = pd.to_datetime(df["Ship Date"], errors="coerce")

    return df


# ---------- Header ----------
st.title("📊 E-Commerce (Superstore) Streamlit Dashboard")
st.caption("Filters + KPIs + Trends + Product/Region/Category analysis")

# ---------- Load ----------
DATA_PATH = "data/superstore.csv"
df = load_data(DATA_PATH)

required_cols = ["Order Date", "Sales", "Profit"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing required columns in CSV: {missing}")
    st.stop()

# ---------- Sidebar Filters ----------
st.sidebar.header("🔎 Filters")

min_date = df["Order Date"].min().date()
max_date = df["Order Date"].max().date()

date_range = st.sidebar.date_input("Order Date range", (min_date, max_date))
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date


def multiselect_filter(label: str, col: str):
    if col not in df.columns:
        return []
    opts = sorted([x for x in df[col].dropna().unique()])
    return st.sidebar.multiselect(label, opts, default=opts)


regions = multiselect_filter("Region", "Region") if "Region" in df.columns else []
categories = multiselect_filter("Category", "Category") if "Category" in df.columns else []
segments = multiselect_filter("Segment", "Segment") if "Segment" in df.columns else []
ship_modes = multiselect_filter("Ship Mode", "Ship Mode") if "Ship Mode" in df.columns else []

dff = df[
    (df["Order Date"].dt.date >= start_date) &
    (df["Order Date"].dt.date <= end_date)
].copy()

if "Region" in dff.columns and regions:
    dff = dff[dff["Region"].isin(regions)]
if "Category" in dff.columns and categories:
    dff = dff[dff["Category"].isin(categories)]
if "Segment" in dff.columns and segments:
    dff = dff[dff["Segment"].isin(segments)]
if "Ship Mode" in dff.columns and ship_modes:
    dff = dff[dff["Ship Mode"].isin(ship_modes)]

# ---------- KPIs ----------
total_sales = float(dff["Sales"].sum())
total_profit = float(dff["Profit"].sum())
total_orders = int(dff["Order ID"].nunique()) if "Order ID" in dff.columns else 0
avg_discount = float(dff["Discount"].mean()) if "Discount" in dff.columns else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Total Sales", f"${total_sales:,.0f}")
c2.metric("📈 Total Profit", f"${total_profit:,.0f}")
c3.metric("🧾 Orders", f"{total_orders:,}")
c4.metric("🏷️ Avg Discount", f"{avg_discount:.2%}")

st.divider()

# ---------- Row 1 ----------
left, right = st.columns(2)

with left:
    st.subheader("Sales Over Time")

    sales_daily = (
        dff.groupby(dff["Order Date"].dt.date)["Sales"]
        .sum()
        .reset_index()
        .rename(columns={"Order Date": "Date"})
    )
    sales_daily["Date"] = pd.to_datetime(sales_daily["Date"])

    fig = px.line(sales_daily, x="Date", y="Sales", markers=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Sales")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Monthly Profit Trend")

    profit_month = (
        dff.set_index("Order Date")["Profit"]
        .resample("M")
        .sum()
        .reset_index()
    )

    # Stabilize column names
    profit_month.columns = ["Date", "Profit"]
    profit_month["Date"] = pd.to_datetime(profit_month["Date"])

    fig = px.line(profit_month, x="Date", y="Profit", markers=True)
    fig.update_layout(xaxis_title="Month", yaxis_title="Profit")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Row 2 ----------
left, right = st.columns(2)

with left:
    st.subheader("Sales by Category")
    if "Category" in dff.columns:
        cat_sales = (
            dff.groupby("Category")["Sales"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        fig = px.bar(cat_sales, x="Category", y="Sales")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Category column not found.")

with right:
    st.subheader("Profit by Category")
    if "Category" in dff.columns:
        cat_profit = (
            dff.groupby("Category")["Profit"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        fig = px.bar(cat_profit, x="Category", y="Profit")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Category column not found.")

st.divider()

# ---------- Row 3 ----------
left, right = st.columns(2)

with left:
    st.subheader("Sales vs Profit by Region")
    if "Region" in dff.columns:
        region_agg = (
            dff.groupby("Region")[["Sales", "Profit"]]
            .sum()
            .reset_index()
            .sort_values("Sales", ascending=False)
        )
        fig = px.bar(region_agg, x="Region", y=["Sales", "Profit"], barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Region column not found.")

with right:
    st.subheader("Discount vs Profit")
    if "Discount" in dff.columns and "Profit" in dff.columns:
        hover_cols = [c for c in ["Category", "Sub-Category", "Region", "Segment"] if c in dff.columns]
        fig = px.scatter(dff, x="Discount", y="Profit", hover_data=hover_cols if hover_cols else None)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Discount/Profit columns not found.")

st.divider()

# ---------- Row 4 ----------
st.subheader("Top 10 Products (Sales / Profit)")

if "Product Name" in dff.columns:
    l, r = st.columns(2)

    top_sales = (
        dff.groupby("Product Name")["Sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_profit = (
        dff.groupby("Product Name")["Profit"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    with l:
        fig = px.bar(top_sales.sort_values("Sales"), x="Sales", y="Product Name", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

    with r:
        fig = px.bar(top_profit.sort_values("Profit"), x="Profit", y="Product Name", orientation="h")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Product Name column not found.")

st.divider()

# ---------- Optional table ----------
if "State" in dff.columns:
    st.subheader("Sales by State (table)")
    state_sales = (
        dff.groupby("State")["Sales"]
        .sum()
        .reset_index()
        .sort_values("Sales", ascending=False)
    )
    st.dataframe(state_sales, use_container_width=True, height=260)

# ---------- Data preview ----------
with st.expander("See filtered data"):
    st.dataframe(dff, use_container_width=True)
