from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.analytics import bp
from models.customer import Customer
from models.transaction import Transaction
from models.analytics import CustomerSegment, CustomerSegmentMembership
from app import db
from datetime import datetime
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from utils.decorators import admin_required
from sqlalchemy import func, desc

@bp.route('/')
@admin_required
@login_required
def dashboard():
    # Mengambil data segmen beserta jumlah membernya
    segments_data = db.session.query(
        CustomerSegment,
        func.count(CustomerSegmentMembership.id).label('member_count')
    ).outerjoin(
        CustomerSegmentMembership, CustomerSegment.id == CustomerSegmentMembership.segment_id
    ).group_by(CustomerSegment.id).all()
    
    segment_stats = []
    for segment, count in segments_data:
        segment_stats.append({
            'id': segment.id,
            'name': segment.segment_name,
            'description': segment.description,
            'color': segment.color,
            'customer_count': count
        })
    
    return render_template('analytics/dashboard.html', segment_stats=segment_stats)

@bp.route('/segment/<int:id>')
@admin_required
@login_required
def segment_detail(id):
    segment = CustomerSegment.query.get_or_404(id)
    
    # 1. Get customers in this segment (Pagination) - KODE LAMA
    page = request.args.get('page', 1, type=int)
    customers_query = db.session.query(Customer).join(CustomerSegmentMembership).filter(
        CustomerSegmentMembership.segment_id == id
    )
    customers = customers_query.paginate(page=page, per_page=20, error_out=False)
    
    # --- 2. KODE BARU: Ambil Riwayat Penggunaan Diskon (Limit 20 Terakhir) ---
    # Logic: Cari transaksi -> Join Customer -> Join Membership
    # Filter: Member segmen ini DAN ada discount_amount > 0
    discount_history = db.session.query(Transaction)\
        .join(Customer, Transaction.customer_id == Customer.id)\
        .join(CustomerSegmentMembership, Customer.id == CustomerSegmentMembership.customer_id)\
        .filter(
            CustomerSegmentMembership.segment_id == id,
            Transaction.discount_amount > 0
        )\
        .order_by(desc(Transaction.created_at))\
        .limit(20)\
        .all()
        
    # Hitung Total Diskon yang sudah diberikan ke segmen ini
    total_discount_given = db.session.query(func.sum(Transaction.discount_amount))\
        .join(Customer, Transaction.customer_id == Customer.id)\
        .join(CustomerSegmentMembership, Customer.id == CustomerSegmentMembership.customer_id)\
        .filter(CustomerSegmentMembership.segment_id == id)\
        .scalar() or 0

    return render_template('analytics/segment_detail.html', 
                          segment=segment, 
                          customers=customers,
                          discount_history=discount_history,     # Variable Baru
                          total_discount_given=total_discount_given) # Variable Baru

@bp.route('/run_kmeans', methods=['GET', 'POST'])
@admin_required
@login_required
def run_kmeans():
    if request.method == 'POST':
        n_clusters = int(request.form.get('n_clusters', 3))
        
        try:
            # --- OPTIMASI 1: HITUNG RFM DI DATABASE LEVEL ---
            # Daripada load semua raw transaksi, kita load hasil agregasi saja.
            # Ini menghemat RAM secara signifikan.
            
            latest_transaction_date = db.session.query(func.max(Transaction.created_at)).scalar()
            if not latest_transaction_date:
                flash('Tidak ada data transaksi untuk dianalisis', 'warning')
                return redirect(url_for('analytics.dashboard'))
            
            # Kita set 'current_date' sedikit di depan transaksi terakhir agar recency tidak 0
            current_date = latest_transaction_date
            
            # Query RFM Aggregation
            results = db.session.query(
                Transaction.customer_id,
                func.count(Transaction.id).label('frequency'),
                func.sum(Transaction.total_amount).label('monetary'),
                func.max(Transaction.created_at).label('last_purchase_date')
            ).group_by(Transaction.customer_id).all()

            if not results:
                flash('Data tidak cukup untuk analisis', 'warning')
                return redirect(url_for('analytics.dashboard'))
            
            rfm_df = pd.DataFrame(results)

            if not rfm_df.empty:
                rfm_df.columns = ['customer_id', 'frequency', 'monetary', 'last_purchase_date']
            
            if rfm_df.empty:
                flash('Data tidak cukup untuk analisis', 'warning')
                return redirect(url_for('analytics.dashboard'))

            # Hitung Recency (hari)
            rfm_df['recency'] = (current_date - pd.to_datetime(rfm_df['last_purchase_date'])).dt.days
            
            # Siapkan data untuk clustering
            # Kita gunakan log transform untuk Monetary jika skewness tinggi (opsional, tapi disarankan)
            # Di sini kita pakai standard scaler saja sesuai kode asli
            scaler = StandardScaler()
            rfm_scaled = scaler.fit_transform(rfm_df[['recency', 'frequency', 'monetary']])
            
            # Apply K-Means
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            rfm_df['cluster'] = kmeans.fit_predict(rfm_scaled)
            
            # --- OPTIMASI 2: SORTING CLUSTER (CRITICAL LOGIC) ---
            # Kita harus memastikan Cluster 0, 1, 2 punya urutan logika yang jelas (misal berdasarkan Monetary).
            # Agar 'VIP' selalu jatuh ke cluster dengan spending tertinggi.
            
            # Hitung rata-rata monetary per cluster
            cluster_summary = rfm_df.groupby('cluster')['monetary'].mean().reset_index()
            # Urutkan dari monetary tertinggi ke terendah (VIP -> Low Value)
            cluster_summary = cluster_summary.sort_values('monetary', ascending=False).reset_index(drop=True)
            
            # Buat mapping: Cluster ID Asli -> Cluster ID Baru yang Terurut
            # Contoh: Cluster 2 punya duit terbanyak, dia jadi index 0 (VIP)
            cluster_map = {row['cluster']: i for i, row in cluster_summary.iterrows()}
            
            # Terapkan mapping ke dataframe utama
            rfm_df['cluster_sorted'] = rfm_df['cluster'].map(cluster_map)
            
            # --- DATABASE UPDATE ---
            CustomerSegmentMembership.query.delete()
            # Note: Jangan hapus CustomerSegment dulu jika ingin mempertahankan ID, 
            # tapi update saja isinya agar lebih rapi. 
            # Untuk simplicity, kita ikuti logic reset tapi dengan nama yang konsisten.
            
            segment_names = [
                'VIP / Prioritas',    # Sebelumnya: VIP
                'Pelanggan Setia',    # Sebelumnya: Frequent Buyer / Loyal
                'Pelanggan Biasa',    # Sebelumnya: Occasional Shopper
                'Berisiko Hilang',    # Sebelumnya: At Risk
                'Pelanggan Pasif'     # Cadangan jika cluster > 4
            ]
            
            # List warna: Hijau (Bagus), Biru (Oke), Kuning (Waspada), Merah (Bahaya)
            segment_colors = ['#28a745', '#007bff', '#ffc107', '#dc3545', '#6c757d']
            
            # Dictionary untuk menyimpan object segment agar tidak query berulang
            segment_map_obj = {}

            for i in range(n_clusters):
                # Ambil data berdasarkan cluster yang SUDAH DIURUTKAN
                cluster_data = rfm_df[rfm_df['cluster_sorted'] == i]
                
                avg_recency = cluster_data['recency'].mean()
                avg_frequency = cluster_data['frequency'].mean()
                avg_monetary = cluster_data['monetary'].mean()
                
                # Tentukan nama
                if i < len(segment_names):
                    segment_name = segment_names[i]
                    color = segment_colors[i] if i < len(segment_colors) else '#6c757d'
                else:
                    segment_name = f'Segmen {i+1}'
                    color = '#6c757d'
                
                description = f'Rata-rata belanja Rp {avg_monetary:,.0f}, ' \
                             f'frekuensi {avg_frequency:.1f}x, ' \
                             f'terakhir transaksi {avg_recency:.0f} hari lalu.'
                
                # Update atau Create Segment
                segment = CustomerSegment.query.filter_by(segment_name=segment_name).first()
                if not segment:
                    segment = CustomerSegment(segment_name=segment_name, color=color)
                    db.session.add(segment)
                
                segment.description = description
                segment.color = color
                db.session.flush() # Agar dapat ID
                
                segment_map_obj[i] = segment.id
                
                # Bulk Insert Membership (Jauh lebih cepat daripada loop add satu per satu)
                # Kita siapkan list of dicts
                memberships = []
                for _, row in cluster_data.iterrows():
                    memberships.append({
                        'customer_id': row['customer_id'],
                        'segment_id': segment.id
                    })
                
                if memberships:
                    db.session.bulk_insert_mappings(CustomerSegmentMembership, memberships)
            
            # --- HANDLE PELANGGAN TANPA TRANSAKSI (ZERO TRANSACTION) ---
            # Cari customer yang tidak ada di rfm_df
            analyzed_customer_ids = rfm_df['customer_id'].tolist()
            
            new_customers = db.session.query(Customer.id).filter(
                ~Customer.id.in_(analyzed_customer_ids)
            ).all()
            
            if new_customers:
                # Buat/Ambil segmen khusus 'Zero Transactions' atau gabung ke 'New/Low'
                zero_segment_name = 'Pelanggan Baru'
                
                zero_segment = CustomerSegment.query.filter_by(segment_name=zero_segment_name).first()
                if not zero_segment:
                    zero_segment = CustomerSegment(
                        segment_name=zero_segment_name, 
                        description="Pelanggan yang belum pernah melakukan transaksi",
                        color="#17a2b8" # Cyan
                    )
                    db.session.add(zero_segment)
                    db.session.flush()
                
                zero_memberships = [{'customer_id': c.id, 'segment_id': zero_segment.id} for c in new_customers]
                db.session.bulk_insert_mappings(CustomerSegmentMembership, zero_memberships)

            db.session.commit()
            flash(f'Analisis K-Means selesai. {len(rfm_df)} pelanggan dianalisis.', 'success')
            return redirect(url_for('analytics.dashboard'))
        
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc() # Print error ke console untuk debug
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
            return redirect(url_for('analytics.dashboard'))
    
    return render_template('analytics/run_kmeans.html')

@bp.route('/api/segment-data')
@login_required
def api_segment_data():
    segments = CustomerSegment.query.all()
    data = []
    for segment in segments:
        data.append({
            'name': segment.segment_name,
            'count': segment.memberships.count(), # Note: Bisa dioptimasi querynya jika lambat
            'color': segment.color
        })
    return jsonify(data)

@bp.route('/api/rfm-data')
@login_required
def api_rfm_data():
    # Optimasi: Query Join langsung, jangan hitung RFM ulang di sini jika tidak perlu real-time calculation
    # atau gunakan query agregasi SQL yang sama seperti di run_kmeans
    
    # Contoh implementasi cepat menggunakan SQL view/join
    query = db.session.query(
        Customer.id,
        Customer.name,
        CustomerSegment.segment_name,
        CustomerSegment.color,
        func.count(Transaction.id).label('frequency'),
        func.sum(Transaction.total_amount).label('monetary'),
        func.max(Transaction.created_at).label('last_purchase')
    ).join(
        CustomerSegmentMembership, Customer.id == CustomerSegmentMembership.customer_id, isouter=True
    ).join(
        CustomerSegment, CustomerSegmentMembership.segment_id == CustomerSegment.id, isouter=True
    ).join(
        Transaction, Customer.id == Transaction.customer_id, isouter=True
    ).group_by(Customer.id, CustomerSegment.id).all()

    data = []
    current_time = datetime.now()
    
    for row in query:
        recency = 0
        if row.last_purchase:
            recency = (current_time - row.last_purchase).days
            
        data.append({
            'customer_id': row.id,
            'name': row.name,
            'segment_name': row.segment_name or 'Unsegmented',
            'color': row.color or '#ccc',
            'frequency': row.frequency or 0,
            'monetary': float(row.monetary or 0),
            'recency': recency
        })
        
    return jsonify(data)

@bp.route('/kmeans-results')
@admin_required
@login_required
def kmeans_results():
    # 1. Query Data Mentah untuk Statistik
    raw_data = db.session.query(
        CustomerSegment.segment_name,
        CustomerSegment.color,
        Customer.id.label('customer_id'),
        Customer.name.label('customer_name'),
        func.count(Transaction.id).label('frequency'),
        func.coalesce(func.sum(Transaction.total_amount), 0).label('monetary'),
        func.max(Transaction.created_at).label('last_purchase')
    ).select_from(CustomerSegmentMembership)\
     .join(CustomerSegment, CustomerSegmentMembership.segment_id == CustomerSegment.id)\
     .join(Customer, CustomerSegmentMembership.customer_id == Customer.id)\
     .outerjoin(Transaction, Customer.id == Transaction.customer_id)\
     .group_by(CustomerSegmentMembership.customer_id, CustomerSegment.id)\
     .all()

    summary_stats = []
    results_list = []

    if raw_data:
        df = pd.DataFrame(raw_data)
        now = pd.Timestamp.now()
        df['recency'] = (now - pd.to_datetime(df['last_purchase'])).dt.days
        
        # 2. Hitung Ringkasan per Segmen
        summary_df = df.groupby(['segment_name', 'color']).agg({
            'customer_id': 'count',
            'recency': 'mean',
            'frequency': 'mean',
            'monetary': 'mean'
        }).reset_index()
        
        for _, row in summary_df.iterrows():
            summary_stats.append({
                'segment_name': row['segment_name'],
                'color': row['color'],
                'count': row['customer_id'],
                'avg_recency': row['recency'] if not pd.isna(row['recency']) else -1,
                'avg_frequency': row['frequency'],
                'avg_monetary': row['monetary']
            })
            
        df['recency'] = df['recency'].fillna(-1)
        results_list = df.to_dict('records')

    return render_template('analytics/kmeans_results.html', 
                          results=results_list, 
                          summary_stats=summary_stats)