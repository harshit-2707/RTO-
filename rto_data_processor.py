import pandas as pd
import numpy as np
import os
import glob

class RTODataProcessor:
    """Refactored logic for RTO Analysis and Scam Detection"""
    
    MIN_PINCODE_VOLUME = 20  # Prevents volume bias in pincode ranking
    SCAM_THRESHOLD = 2       # Flag customers with > 2 RTOs
    
    def __init__(self, data_folder='./'):
        self.data_folder = data_folder
        self.processed_data = None
        self.scam_customers = set()
        
    def load_data(self):
        """Loads and combines all orders_*.csv files"""
        csv_files = glob.glob(os.path.join(self.data_folder, 'orders_*.csv'))
        if not csv_files:
            return pd.read_csv('processed_data.csv') if os.path.exists('processed_data.csv') else pd.DataFrame()
        return pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)

    def _determine_delivery_status(self, row):
        """Logic: COD Verified overrides Unverified; Prepaid skips tags"""
        tags = [t.strip() for t in str(row.get('Tags', '')).split(',')]
        f_status = str(row.get('Financial Status', '')).lower()
        
        if 'RTO' in tags or 'Undelivered' in tags:
            return 'Failed Delivery'
        
        if f_status == 'paid' or 'ONLINE' in tags:
            return 'Shipped'
            
        if 'COD' in tags:
            # If 'Verified' is present, 'Unverified' is ignored
            if 'Verified' in tags:
                return 'Shipped'
            if 'Unverified' in tags:
                return 'Unverified'
                
        return 'Shipped'

    def process_data(self, df):
        """Prepares data for the dashboard"""
        df = df.copy()
        df['Email'] = df['Email'].fillna('Unknown')
        df['Created at'] = pd.to_datetime(df['Created at'], errors='coerce')
        df['Order Amount'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        df['Pincode'] = df['Shipping Zip'].astype(str)
        df['Day of Week'] = df['Created at'].dt.day_name()
        
        df['Delivery Status'] = df.apply(self._determine_delivery_status, axis=1)
        df['Is RTO'] = df['Delivery Status'] == 'Failed Delivery'
        
        # Scam Logic
        rto_counts = df[df['Is RTO']].groupby('Email').size()
        self.scam_customers = set(rto_counts[rto_counts > self.SCAM_THRESHOLD].index)
        df['Is Scam Customer'] = df['Email'].isin(self.scam_customers)
        
        self.processed_data = df
        return df

    def get_toxic_pincodes(self, top_n=5):
        """Ranks pincodes by RTO-to-Delivered ratio"""
        df = self.processed_data
        stats = df.groupby('Pincode').agg({'Is RTO': 'sum', 'Email': 'count'})
        stats.columns = ['RTO_Count', 'Total_Orders']
        stats = stats[stats['Total_Orders'] >= self.MIN_PINCODE_VOLUME]
        stats['RTO_Ratio'] = (stats['RTO_Count'] / stats['Total_Orders']) * 100
        return stats.sort_values('RTO_Ratio', ascending=False).head(top_n)
