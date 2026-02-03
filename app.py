import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="E-Commerce Dashboard (Superstore)", layout="wide")

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="latin1")
    # Notebook'taki dönüşüm
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], errors="coerce")
    df = df.dropna(subset=["Order Date"])
    return df

# ---------- Header ----------
st.title("📊 E-Commerce (Superstore) Streamlit Dashboard")
st.caption("Filters + KPIs + Trends + Product/Region/Category analysis")

# ---------- Load ----------
DATA_PATH = "data/superstore.csv"
df = load_data(DATA_PATH)

# ---------- Sidebar Filters ----------
st.sidebar.header("🔎 Filters")

min_date = df["Order Date"].min().date()
max_date = df["Order Date"].max().date()
date_range = st.sidebar.date_input("Order Date range", (min_date, max_date))
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

def multiselect_filter(label, col):
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

# ---------- KPIs (Notebook'taki metrikler) ----------
total_sales = float(dff["Sales"].sum()) if "Sales" in dff.columns else 0.0
total_profit = float(dff["Profit"].sum()) if "Profit" in dff.columns else 0.0
total_orders = int(dff["Order ID"].nunique()) if "Order ID" in dff.columns else 0
avg_discount = float(dff["Discount"].mean()) if "Discount" in dff.columns else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Total Sales", f"${total_sales:,.0f}")
c2.metric("📈 Total Profit", f"${total_profit:,.0f}")
c3.metric("🧾 Orders", f"{total_orders:,}")
c4.metric("🏷️ Avg Discount", f"{avg_discount:.2%}")

st.divider()

# ---------- Row 1: Sales over time / Monthly Profit ----------
left, right = st.columns(2)

with left:
    st.subheader("Sales Over Time")
    sales_daily = (dff.groupby(dff["Order Date"].dt.date)["Sales"]
               .sum()
               .reset_index()
               .rename(columns={"Order Date": "Date"}))

sales_daily["Date"] = pd.to_datetime(sales_daily["Date"])

fig = px.line(sales_daily, x="Date", y="Sales", markers=True)

    fig.update_layout(xaxis_title="Date", yaxis_title="Sales")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Monthly Profit Trend")
    # Notebook: resample ME
    profit_month = (dff.set_index("Order Date")["Profit"].resample("M").sum().reset_index())
    fig = px.line(profit_month, x="Order Date", y="Profit", markers=True)
    fig.update_layout(xaxis_title="Month", yaxis_title="Profit")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Row 2: Category Sales / Profit by Category ----------
left, right = st.columns(2)

with left:
    st.subheader("Sales by Category")
    cat_sales = dff.groupby("Category")["Sales"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(cat_sales, x="Category", y="Sales")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Profit by Category")
    cat_profit = dff.groupby("Category")["Profit"].sum().sort_values(ascending=True).reset_index()
    fig = px.bar(cat_profit, x="Category", y="Profit")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Row 3: Region Sales/Profit + Discount vs Profit ----------
left, right = st.columns(2)

with left:
    st.subheader("Sales vs Profit by Region")
    region_agg = (dff.groupby("Region")[["Sales", "Profit"]].sum().reset_index()
                  .sort_values("Sales", ascending=False))
    fig = px.bar(region_agg, x="Region", y=["Sales", "Profit"], barmode="group")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Discount vs Profit")
    if "Discount" in dff.columns and "Profit" in dff.columns:
        fig = px.scatter(dff, x="Discount", y="Profit", hover_data=["Category", "Sub-Category"] if "Sub-Category" in dff.columns else None)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Discount/Profit columns not found in dataset.")

st.divider()

# ---------- Row 4: Top Products ----------
st.subheader("Top 10 Products (Sales / Profit)")
l, r = st.columns(2)

top_sales = (dff.groupby("Product Name")["Sales"].sum().sort_values(ascending=False).head(10).reset_index())
top_profit = (dff.groupby("Product Name")["Profit"].sum().sort_values(ascending=False).head(10).reset_index())

with l:
    fig = px.bar(top_sales.sort_values("Sales"), x="Sales", y="Product Name", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

with r:
    fig = px.bar(top_profit.sort_values("Profit"), x="Profit", y="Product Name", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Optional: Map ----------
if all(col in dff.columns for col in ["State", "Sales"]):
    st.subheader("Sales by State (heat-style)")
    state_sales = dff.groupby("State")["Sales"].sum().reset_index().sort_values("Sales", ascending=False)
    st.dataframe(state_sales, use_container_width=True, height=260)

# ---------- Data preview ----------
with st.expander("See filtered data"):
    st.dataframe(dff, use_container_width=True)
