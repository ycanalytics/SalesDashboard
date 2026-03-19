
import io
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="VFW Bar Sales Performance Dashboard", layout="wide")

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


@st.cache_data
def load_data(path: str = "Barsales.csv") -> pd.DataFrame:
    df = pd.read_csv(path)

    for col in ["Gross_sales", "Net_Sales"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Quantity"] = pd.to_numeric(df.get("Quantity"), errors="coerce")
    df["orderdate_year"] = pd.to_numeric(df.get("orderdate_year"), errors="coerce")
    df["orderdate"] = pd.to_datetime(df.get("orderdate"), format="%b-%y", errors="coerce")

    df["orderdate_month"] = df["orderdate"].dt.month_name()
    df["month_num"] = df["orderdate"].dt.month
    df["Category"] = df["Category"].astype(str).str.strip()
    df["year"] = df["orderdate_year"].fillna(df["orderdate"].dt.year)

    return df.dropna(
        subset=["Net_Sales", "Gross_sales", "Category", "orderdate", "month_num", "year"]
    ).copy()


def format_growth(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    arrow = "↑" if value >= 0 else "↓"
    return f"{value:+.1f}% {arrow}"


def build_insights(
    category_sales: pd.DataFrame,
    monthly_revenue: pd.DataFrame,
    growth_pct: float | None
) -> list[str]:
    insights = []

    if not category_sales.empty:
        top_category = category_sales.iloc[0]["Category"]
        lowest_category = category_sales.iloc[-1]["Category"]
        insights.append(f"**{top_category}** is the strongest revenue driver in the current view.")
        insights.append(f"**{lowest_category}** contributes the least revenue and is a candidate for bundles, menu repositioning, or low-risk promotional tests.")

    if not monthly_revenue.empty:
        peak_month = monthly_revenue.sort_values("Net_Sales", ascending=False).iloc[0]["orderdate_month"]
        insights.append(f"Revenue peaks in **{peak_month}**, which supports pre-peak staffing and inventory planning.")

    if growth_pct is not None and not pd.isna(growth_pct):
        if growth_pct > 0:
            insights.append(f"Revenue growth is **{growth_pct:.1f}%**, indicating positive year-over-year momentum.")
        elif growth_pct < 0:
            insights.append(f"Revenue growth is **{growth_pct:.1f}%**, signaling the need to review pricing, promotions, or product mix.")
        else:
            insights.append("Revenue is flat year over year, suggesting an opportunity to improve category strategy or customer conversion.")

    insights.append("Focus marketing on top-selling categories while testing targeted offers to lift lower-performing items.")
    return insights[:4]


def markdown_to_html(text: str) -> str:
    return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)


def format_insight(item: str) -> str:
    item = markdown_to_html(item)
    lower = item.lower()
    if "growth" in lower or "momentum" in lower or "peak" in lower:
        return f"<div style='color:#1b5e20;'>📈 {item}</div>"
    if "least" in lower or "review" in lower or "candidate" in lower:
        return f"<div style='color:#b45309;'>⚠️ {item}</div>"
    if "focus" in lower or "targeted" in lower:
        return f"<div style='color:#0d47a1;'>💡 {item}</div>"
    return f"<div style='color:#333333;'>• {item}</div>"


def generate_pdf_report(
    selected_year: int,
    selected_category: str,
    total_revenue: float,
    total_orders: int,
    avg_order_value: float,
    growth_pct: float | None,
    category_sales: pd.DataFrame,
    monthly_revenue: pd.DataFrame,
    insights: list[str],
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#173f73"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=16,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#294d7d"),
        spaceAfter=8,
        spaceBefore=10,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph("VFW Bar Sales Performance Dashboard", title_style))
    story.append(Paragraph(f"Prepared by YC Analytics | Exported view: {selected_year} | Category filter: {selected_category}", subtitle_style))

    kpi_table = Table(
        [
            ["Total Revenue", "Total Orders", "Avg Order Value", "Revenue Growth"],
            [
                f"${total_revenue:,.0f}",
                f"{total_orders:,}",
                f"${avg_order_value:,.2f}",
                "N/A" if growth_pct is None or pd.isna(growth_pct) else f"{growth_pct:+.1f}%",
            ],
        ],
        colWidths=[1.45 * inch, 1.35 * inch, 1.5 * inch, 1.35 * inch],
    )
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e92")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eef2f7")),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#173f73")),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cfd8e3")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbe3ee")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 0.16 * inch))

    story.append(Paragraph("Executive Summary", heading_style))
    for item in insights:
        clean = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", item)
        story.append(Paragraph(f"• {clean}", body_style))

    if not category_sales.empty:
        story.append(Paragraph("Category Performance", heading_style))
        cat_rows = [["Category", "Net Sales", "Share"]]
        cat_total = category_sales["Net_Sales"].sum()
        for _, row in category_sales.head(5).iterrows():
            share = (row["Net_Sales"] / cat_total * 100) if cat_total else 0
            cat_rows.append([str(row["Category"]), f"${row['Net_Sales']:,.0f}", f"{share:.1f}%"])
        cat_table = Table(cat_rows, colWidths=[3.2 * inch, 1.4 * inch, 1.0 * inch])
        cat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#294d7d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe3ee")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf2")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(cat_table)

    if not monthly_revenue.empty:
        story.append(Paragraph("Monthly Revenue Snapshot", heading_style))
        month_rows = [["Month", "Net Sales"]]
        for _, row in monthly_revenue.sort_values("Net_Sales", ascending=False).head(5).iterrows():
            month_rows.append([str(row["orderdate_month"]), f"${row['Net_Sales']:,.0f}"])
        month_table = Table(month_rows, colWidths=[3.2 * inch, 1.6 * inch])
        month_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#294d7d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe3ee")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5ebf2")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(month_table)

    story.append(Paragraph("Recommendation", heading_style))
    story.append(
        Paragraph(
            "Use this dashboard as a monthly operating review tool: prioritize high-contributing categories, "
            "plan inventory and labor around peak months, and test targeted promotions for low-contributing items. "
            "The PDF export gives stakeholders a portable summary for meetings, email updates, and board-ready reporting.",
            body_style,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


df = load_data()
df["year"] = df["year"].astype(int)

years = sorted(df["year"].dropna().astype(int).unique().tolist())
categories = sorted(df["Category"].dropna().unique().tolist())

st.markdown(
    """
    <style>
    .stApp {
        background-color: #eef2f7;
    }
    .dashboard-header {
        background: linear-gradient(90deg, #1f4e92, #3da5e7);
        padding: 20px 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }
    .dashboard-title {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 2px;
        letter-spacing: 0.4px;
    }
    .dashboard-subtitle {
        font-size: 1rem;
        opacity: 0.95;
    }
    .kpi-card {
        background: white;
        border: 1px solid #dbe3ee;
        border-radius: 12px;
        padding: 18px 16px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 6px;
    }
    .kpi-label {
        color: #294d7d;
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .kpi-value {
        color: #173f73;
        font-size: 2.2rem;
        font-weight: 900;
        line-height: 1.1;
    }
    .section-card {
        background: white;
        border: 1px solid #dbe3ee;
        border-radius: 12px;
        padding: 12px 14px 8px 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 16px;
    }
    .section-title {
        color: #294d7d;
        font-size: 1.3rem;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .insight-box {
        background: white;
        border: 1px solid #dbe3ee;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

header_left, header_right = st.columns([2.2, 2.3])

with header_left:
    logo_path = Path("logo.png")
    col_logo, col_title = st.columns([1.4, 4.6])

    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), width=200)

    with col_title:
        st.markdown(
            """
            <div class="dashboard-header">
                <div class="dashboard-title">VFW BAR SALES PERFORMANCE DASHBOARD</div>
                <div class="dashboard-subtitle">Prepared by YC Analytics</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with header_right:
    filter_cols = st.columns(3)
    with filter_cols[0]:
        st.markdown(
            '<div style="font-size:18px; font-weight:800; color:#294d7d; margin-bottom:6px;">Date Range</div>',
            unsafe_allow_html=True
        )
        selected_year = st.selectbox("Date Range", years, index=len(years) - 1, label_visibility="collapsed")
    with filter_cols[1]:
        st.markdown(
            '<div style="font-size:18px; font-weight:800; color:#294d7d; margin-bottom:6px;">Category</div>',
            unsafe_allow_html=True
        )
        selected_category = st.selectbox("Category", ["All"] + categories, label_visibility="collapsed")
    with filter_cols[2]:
        st.markdown(
            '<div style="font-size:18px; font-weight:800; color:#294d7d; margin-bottom:6px;">Location</div>',
            unsafe_allow_html=True
        )
        selected_location = st.selectbox("Location", ["All"], label_visibility="collapsed")

filtered_df = df[df["year"] == int(selected_year)].copy()
if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

prev_df = df[df["year"] == int(selected_year) - 1].copy()
if selected_category != "All":
    prev_df = prev_df[prev_df["Category"] == selected_category]

total_revenue = filtered_df["Net_Sales"].sum()
total_orders = int(len(filtered_df))
avg_order_value = total_revenue / total_orders if total_orders else 0
prev_revenue = prev_df["Net_Sales"].sum()
growth_pct = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">TOTAL REVENUE</div>
            <div class="kpi-value">${total_revenue:,.0f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">TOTAL ORDERS</div>
            <div class="kpi-value">{total_orders:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">AVG ORDER VALUE</div>
            <div class="kpi-value">${avg_order_value:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k4:
    growth_color = "#2e7d32" if growth_pct is None or growth_pct >= 0 else "#b42318"
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">REVENUE GROWTH</div>
            <div class="kpi-value" style="color:{growth_color};">{format_growth(growth_pct)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

monthly_revenue = (
    filtered_df.groupby(["month_num", "orderdate_month"], as_index=False)["Net_Sales"]
    .sum()
    .sort_values("month_num")
)
monthly_revenue["orderdate_month"] = pd.Categorical(
    monthly_revenue["orderdate_month"],
    categories=MONTH_ORDER,
    ordered=True,
)
monthly_revenue = monthly_revenue.sort_values("orderdate_month")

category_sales = (
    filtered_df.groupby("Category", as_index=False)["Net_Sales"]
    .sum()
    .sort_values("Net_Sales", ascending=False)
)

monthly_orders = (
    filtered_df.groupby(["month_num", "orderdate_month"], as_index=False)
    .size()
    .rename(columns={"size": "Order_Count"})
    .sort_values("month_num")
)
monthly_orders["orderdate_month"] = pd.Categorical(
    monthly_orders["orderdate_month"],
    categories=MONTH_ORDER,
    ordered=True,
)
monthly_orders = monthly_orders.sort_values("orderdate_month")

left, right = st.columns(2)

with left:
    st.markdown('<div class="section-card"><div class="section-title">Revenue Trend</div>', unsafe_allow_html=True)
    fig_trend = px.line(
        monthly_revenue,
        x="orderdate_month",
        y="Net_Sales",
        markers=True,
    )
    fig_trend.update_traces(fill="tozeroy")
    fig_trend.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="",
        yaxis_title="",
        yaxis_tickprefix="$",
        showlegend=False,
        font=dict(size=16),
    )
    fig_trend.update_xaxes(tickfont=dict(size=15))
    fig_trend.update_yaxes(tickfont=dict(size=15))
    st.plotly_chart(fig_trend, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card"><div class="section-title">Top Sales Categories</div>', unsafe_allow_html=True)
    fig_bar = px.bar(
        category_sales.head(5),
        x="Net_Sales",
        y="Category",
        orientation="h",
        text="Net_Sales",
    )
    fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', textfont=dict(size=15))
    fig_bar.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="",
        yaxis_title="",
        yaxis=dict(categoryorder="total ascending"),
        showlegend=False,
        font=dict(size=16),
    )
    fig_bar.update_xaxes(tickfont=dict(size=15))
    fig_bar.update_yaxes(tickfont=dict(size=15))
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

left2, right2 = st.columns(2)

with left2:
    st.markdown('<div class="section-card"><div class="section-title">Revenue Breakdown</div>', unsafe_allow_html=True)
    fig_pie = px.pie(
        category_sales,
        names="Category",
        values="Net_Sales",
        hole=0.35,
    )
    fig_pie.update_traces(textfont_size=15)
    fig_pie.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        legend_title_text="",
        font=dict(size=15),
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right2:
    st.markdown('<div class="section-card"><div class="section-title">Monthly Order Volume</div>', unsafe_allow_html=True)
    fig_orders = px.bar(
        monthly_orders,
        x="orderdate_month",
        y="Order_Count",
        text="Order_Count",
    )
    fig_orders.update_traces(textposition="outside", textfont=dict(size=14))
    fig_orders.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        font=dict(size=15),
    )
    fig_orders.update_xaxes(tickfont=dict(size=15))
    fig_orders.update_yaxes(tickfont=dict(size=15))
    st.plotly_chart(fig_orders, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section-card"><div class="section-title">Top 10 Category Performance</div>', unsafe_allow_html=True)
fig_top10 = px.bar(
    category_sales.head(10),
    x="Net_Sales",
    y="Category",
    orientation="h",
    text="Net_Sales",
)
fig_top10.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', textfont=dict(size=15))
fig_top10.update_layout(
    template="plotly_white",
    height=380,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="",
    yaxis_title="",
    yaxis=dict(categoryorder="total ascending"),
    showlegend=False,
    font=dict(size=16),
)
fig_top10.update_xaxes(tickfont=dict(size=15))
fig_top10.update_yaxes(tickfont=dict(size=15))
st.plotly_chart(fig_top10, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

insights = build_insights(category_sales, monthly_revenue, growth_pct)
st.markdown('<div class="insight-box">', unsafe_allow_html=True)
st.markdown(
    """
    <div style="font-size:22px; font-weight:900; color:#294d7d; margin-bottom:14px;">
        Executive Summary
    </div>
    """,
    unsafe_allow_html=True
)
for item in insights:
    formatted = format_insight(item)
    st.markdown(
        f"<div style='font-size:18px; margin-bottom:10px; line-height:1.7;'>{formatted}</div>",
        unsafe_allow_html=True
    )
st.markdown("</div>", unsafe_allow_html=True)

pdf_bytes = generate_pdf_report(
    selected_year=int(selected_year),
    selected_category=selected_category,
    total_revenue=total_revenue,
    total_orders=total_orders,
    avg_order_value=avg_order_value,
    growth_pct=growth_pct,
    category_sales=category_sales,
    monthly_revenue=monthly_revenue,
    insights=insights,
)

st.markdown("### Export")
st.download_button(
    label="Download client-ready PDF summary",
    data=pdf_bytes,
    file_name=f"vfw_dashboard_summary_{selected_year}_{selected_category.lower().replace(' ', '_').replace('/', '_')}.pdf",
    mime="application/pdf",
)
