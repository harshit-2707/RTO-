import streamlit as st
import plotly.express as px
import pandas as pd
from rto_data_processor import RTODataProcessor

st.set_page_config(page_title="RTO Intelligence", layout="wide")
st.title("🎯 RTO Analysis Dashboard")

processor = RTODataProcessor()

# Sidebar for file upload to handle live data
uploaded_file = st.sidebar.file_uploader("Upload Orders CSV", type="csv")

if uploaded_file:
    df = processor.process_data(pd.read_csv(uploaded_file))
    
    # 1. METRICS
    total_rev = df['Order Amount'].sum()
    lost_rev = df[df['Is RTO']]['Order Amount'].sum()
    scam_potential = df[df['Is Scam Customer']]['Order Amount'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"₹{total_rev:,.0f}")
    col2.metric("RTO Loss", f"₹{lost_rev:,.0f}", f"-{(lost_rev/total_rev*100):.1f}%", delta_color="inverse")
    col3.metric("Net Savings Potential", f"₹{scam_potential:,.0f}")

    # 2. TOXIC PINCODES
    st.subheader("📍 High-Risk Pincodes (By Ratio)")
    toxic = processor.get_toxic_pincodes(5).reset_index()
    st.plotly_chart(px.bar(toxic, x='Pincode', y='RTO_Ratio', color='RTO_Ratio'))

    # 3. REVENUE TRENDS
    st.subheader("📅 Monthly Revenue vs RTO Loss")
    df['Month'] = df['Created at'].dt.strftime('%Y-%m')
    monthly = df.groupby('Month')['Order Amount'].sum().reset_index()
    st.plotly_chart(px.line(monthly, x='Month', y='Order Amount'))

    # 4. BLACKLIST
    st.subheader("🚨 Scam Customer Blacklist")
    st.dataframe(df[df['Is Scam Customer']][['Email', 'Order Amount']].drop_duplicates())

else:
    st.info("Upload your CSV file to see the live analysis.")
