import pandas as pd
import numpy as np
from datetime import datetime
from app import create_app, db
from models.customer import Customer
from models.transaction import Transaction
from models.analytics import CustomerSegmentMembership, CustomerSegment
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func

def get_data_and_rfm():
    """Mengambil data, menghitung RFM, dan menyertakan Nama Pelanggan."""
    print("🔍 Mengambil data transaksi dan pelanggan...")
    
    # Ambil data Transaksi + Nama Customer via Join
    # Gunakan SQL Query Aggregate langsung agar lebih cepat daripada loop Python
    query = db.session.query(
        Transaction.customer_id,
        Customer.name,
        func.count(Transaction.id).label('frequency'),
        func.sum(Transaction.total_amount).label('monetary'),
        func.max(Transaction.created_at).label('last_purchase_date')
    ).join(Customer, Transaction.customer_id == Customer.id)\
    .group_by(Transaction.customer_id, Customer.name).statement
    
    # Load ke Pandas via execute (lebih aman untuk versi Pandas/SQLAlchemy terbaru)
    result_proxy = db.session.execute(query)
    results = result_proxy.fetchall()
    
    if not results:
        print("❌ Tidak ada data transaksi. Tidak bisa melakukan analisis.")
        return None

    # Ambil nama kolom dari keys
    columns = list(result_proxy.keys())
    rfm_df = pd.DataFrame(results, columns=columns)

    # Hitung Recency
    current_date = pd.Timestamp.now()
    rfm_df['recency'] = (current_date - pd.to_datetime(rfm_df['last_purchase_date'])).dt.days
    
    print(f"✅ Data RFM berhasil dihitung untuk {len(rfm_df)} pelanggan.")
    return rfm_df

def process_segmentation(rfm_df, n_clusters=3):
    """Menjalankan K-Means, Sorting Cluster, dan Menyimpan ke DB."""
    print("🤖 Menjalankan algoritma K-Means...")
    
    # 1. Preprocessing
    X = rfm_df[['recency', 'frequency', 'monetary']]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 2. K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    rfm_df['cluster'] = kmeans.fit_predict(X_scaled)
    
    # 3. SORTING CLUSTER (PENTING!)
    # Kita urutkan cluster berdasarkan Monetary (Uang) dari Terbesar ke Terkecil.
    # Sehingga index 0 selalu VIP, index terakhir selalu Low Value.
    cluster_summary = rfm_df.groupby('cluster')['monetary'].mean().reset_index()
    cluster_summary = cluster_summary.sort_values('monetary', ascending=False).reset_index(drop=True)
    
    # Mapping ID Cluster Lama -> ID Cluster Baru yang Terurut
    cluster_map = {row['cluster']: i for i, row in cluster_summary.iterrows()}
    rfm_df['cluster_sorted'] = rfm_df['cluster'].map(cluster_map)
    
    # 4. Definisikan Nama Segmen berdasarkan Urutan (Rank)
    # Urutan: 0=Terbaik (VIP), 1=Menengah, 2=Bawah
    segment_definitions = [
        {'name': 'VIP / Platinum', 'color': '#28a745'},       # Cluster 0
        {'name': 'Gold / Loyal', 'color': '#007bff'},         # Cluster 1
        {'name': 'Silver / Occasional', 'color': '#ffc107'},  # Cluster 2
        {'name': 'Bronze / At Risk', 'color': '#dc3545'}      # Cluster 3 (jika ada)
    ]
    
    print("💾 Menyimpan hasil ke database...")
    
    # Reset Data Lama
    db.session.query(CustomerSegmentMembership).delete()
    # Opsional: Jika ingin reset definisi segmen juga
    # db.session.query(CustomerSegment).delete() 
    db.session.commit()
    
    # Dictionary untuk mapping cluster_sorted -> segment_id database
    cluster_to_segment_id = {}
    
    # 5. Buat/Update Segmen di Database
    for i in range(n_clusters):
        # Ambil statistik rata-rata untuk deskripsi
        stats = rfm_df[rfm_df['cluster_sorted'] == i][['recency', 'frequency', 'monetary']].mean()
        
        # Tentukan nama (jika i melebihi list, pakai nama generik)
        seg_def = segment_definitions[i] if i < len(segment_definitions) else {'name': f'Segment {i}', 'color': '#6c757d'}
        
        description = f"Rata-rata: Rp {stats['monetary']:,.0f}, {stats['frequency']:.1f}x Transaksi, Recency {stats['recency']:.0f} hari."
        
        # Cek apakah segmen sudah ada by name (untuk menghindari duplikat ID jika script dijalankan berulang)
        segment = CustomerSegment.query.filter_by(segment_name=seg_def['name']).first()
        if not segment:
            segment = CustomerSegment(segment_name=seg_def['name'], color=seg_def['color'])
            db.session.add(segment)
        
        segment.description = description
        segment.color = seg_def['color']
        db.session.flush() # Dapatkan ID
        
        cluster_to_segment_id[i] = segment.id # Simpan ID untuk mapping
        
        # Tambahkan nama segmen ke DataFrame untuk display nanti
        rfm_df.loc[rfm_df['cluster_sorted'] == i, 'segment_name'] = seg_def['name']

    # 6. Bulk Insert Membership
    memberships = []
    for _, row in rfm_df.iterrows():
        memberships.append({
            'customer_id': row['customer_id'],
            'segment_id': cluster_to_segment_id[row['cluster_sorted']],
            'assigned_at': datetime.now()
        })
    
    db.session.bulk_insert_mappings(CustomerSegmentMembership, memberships)
    db.session.commit()
    
    print("✅ Database diperbarui.")
    return rfm_df

def display_table(rfm_df):
    """Menampilkan tabel hasil yang rapi."""
    print("\n" + "="*100)
    print("📊 TABEL SEGMENTASI PELANGGAN (K-MEANS SORTED)")
    print("="*100)
    
    # Pilih kolom untuk ditampilkan
    output_df = rfm_df[['customer_id', 'name', 'recency', 'frequency', 'monetary', 'segment_name']].copy()
    
    # Rename kolom header
    output_df.columns = ['ID', 'Nama Pelanggan', 'Recency (Hari)', 'Frequency (x)', 'Monetary (Rp)', 'Segmen']
    
    # Format angka
    # Pandas display formatting
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:,.0f}'.format)
    
    # Print DataFrame
    print(output_df.sort_values('Monetary (Rp)', ascending=False).to_string(index=False))
    print("="*100)
    
    # Print Summary
    print("\nRINGKASAN SEGMEN:")
    print(output_df['Segmen'].value_counts())

def main():
    app = create_app()
    with app.app_context():
        # 1. Ambil Data
        rfm_df = get_data_and_rfm()
        if rfm_df is None:
            return
        
        # 2. Proses K-Means & Save DB
        # Gunakan 3 atau 4 cluster
        final_df = process_segmentation(rfm_df, n_clusters=3)
        
        # 3. Tampilkan
        display_table(final_df)

if __name__ == "__main__":
    main()