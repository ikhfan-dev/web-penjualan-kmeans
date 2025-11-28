from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.analytics import bp
from models.customer import Customer
from models.transaction import Transaction, TransactionItem
from models.analytics import CustomerSegment, CustomerSegmentMembership
from app import db
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from utils.decorators import admin_required

@bp.route('/')
@admin_required
@login_required
def dashboard():
    # Get all segments
    segments = CustomerSegment.query.all()
    
    # Get segment statistics
    segment_stats = []
    for segment in segments:
        customer_count = segment.memberships.count()
        segment_stats.append({
            'id': segment.id,
            'name': segment.segment_name,
            'description': segment.description,
            'color': segment.color,
            'customer_count': customer_count
        })
    
    return render_template('analytics/dashboard.html', segment_stats=segment_stats)

@bp.route('/segment/<int:id>')
@admin_required
@login_required
def segment_detail(id):
    segment = CustomerSegment.query.get_or_404(id)
    
    # Get customers in this segment
    customers = db.session.query(
        Customer, CustomerSegmentMembership
    ).join(CustomerSegmentMembership).filter(
        CustomerSegmentMembership.segment_id == id
    ).all()
    
    return render_template('analytics/segment_detail.html', 
                          segment=segment, 
                          customers=customers)

@bp.route('/run_kmeans', methods=['GET', 'POST'])
@admin_required
@login_required
def run_kmeans():
    if request.method == 'POST':
        n_clusters = int(request.form.get('n_clusters', 3))
        
        try:
            # Get transaction data
            transactions = db.session.query(
                Transaction.customer_id,
                Transaction.id,
                Transaction.total_amount,
                Transaction.created_at
            ).all()
            
            if not transactions:
                flash('Tidak ada data transaksi untuk dianalisis', 'warning')
                return redirect(url_for('analytics.dashboard'))
            
            # Convert to DataFrame
            df = pd.DataFrame([(t.customer_id, t.id, t.total_amount, t.created_at) for t in transactions],
                             columns=['customer_id', 'transaction_id', 'amount', 'date'])
            
            # Calculate RFM values
            current_date = datetime.now()
            
            # Recency: Days since last purchase
            recency_df = df.groupby('customer_id')['date'].max().reset_index()
            recency_df['recency'] = (current_date - recency_df['date']).dt.days
            recency_df = recency_df[['customer_id', 'recency']]
            
            # Frequency: Number of transactions
            frequency_df = df.groupby('customer_id')['transaction_id'].count().reset_index()
            frequency_df.columns = ['customer_id', 'frequency']
            
            # Monetary: Total amount spent
            monetary_df = df.groupby('customer_id')['amount'].sum().reset_index()
            monetary_df.columns = ['customer_id', 'monetary']
            
            # Merge RFM values
            rfm_df = recency_df.merge(frequency_df, on='customer_id').merge(monetary_df, on='customer_id')
            
            # Standardize the data
            scaler = StandardScaler()
            rfm_scaled = scaler.fit_transform(rfm_df[['recency', 'frequency', 'monetary']])
            
            # Apply K-Means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            rfm_df['cluster'] = kmeans.fit_predict(rfm_scaled)
            
            # Clear existing segment memberships
            CustomerSegmentMembership.query.delete()
            db.session.commit()
            
            # Create or update segments for clustered customers
            segment_names = ['VIP', 'Frequent Buyer', 'Occasional Shopper', 'New Customer', 'At Risk']
            segment_colors = ['#28a745', '#007bff', '#ffc107', '#17a2b8', '#dc3545']
            
            for i in range(n_clusters):
                cluster_data = rfm_df[rfm_df['cluster'] == i]
                
                # Determine segment characteristics
                avg_recency = cluster_data['recency'].mean()
                avg_frequency = cluster_data['frequency'].mean()
                avg_monetary = cluster_data['monetary'].mean()
                
                # Determine segment name based on characteristics
                if i < len(segment_names):
                    segment_name = segment_names[i]
                    segment_color = segment_colors[i]
                else:
                    segment_name = f'Segment {i+1}'
                    segment_color = '#6c757d'
                
                # Create description
                description = f'Pelanggan dengan rata-rata pembelian {avg_frequency:.1f}x, ' \
                             f'total belanja Rp {avg_monetary:,.0f}, ' \
                             f'dan pembelian terakhir {avg_recency:.0f} hari yang lalu.'
                
                # Check if segment already exists
                segment = CustomerSegment.query.filter_by(segment_name=segment_name).first()
                if not segment:
                    segment = CustomerSegment(
                        segment_name=segment_name,
                        description=description,
                        color=segment_color
                    )
                    db.session.add(segment)
                    db.session.flush()  # Get the ID without committing
                else:
                    segment.description = description
                    segment.color = segment_color
                
                # Add customers to this segment
                for _, row in cluster_data.iterrows():
                    membership = CustomerSegmentMembership(
                        customer_id=row['customer_id'],
                        segment_id=segment.id
                    )
                    db.session.add(membership)
            
            # --- AWAL PERUBAAN LOGIKA ---
            # Cari pelanggan yang benar-benar tidak memiliki transaksi sama sekali
            new_customers_query = db.session.query(Customer).filter(~Customer.transactions.any()).all()
            new_customer_ids = {customer.id for customer in new_customers_query}
            
            # --- PERUBAAN: TANGANI PELANGGAN TANPA TRANSAKSI (HANYA SATU LOOP) ---
            
            if new_customer_ids:
                # Cari segmen "New Customer" yang sudah dibuat oleh K-Means
                new_segment = CustomerSegment.query.filter_by(segment_name='New Customer').first()
                
                # Jika segmen ditemukan, tambahkan pelanggan tanpa transaksi ke dalamnya
                if new_segment:
                    for customer_id in new_customer_ids:
                        membership = CustomerSegmentMembership(
                            customer_id=customer_id,
                            segment_id=new_segment.id
                        )
                        db.session.add(membership)
            
            # --- AKHIR PERUBAAN ---
            
            db.session.commit()
            flash(f'Analisis K-Means dengan {n_clusters} cluster berhasil dilakukan!', 'success')
            return redirect(url_for('analytics.dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
            return redirect(url_for('analytics.dashboard'))
    
    return render_template('analytics/run_kmeans.html')

@bp.route('/api/segment-data')
@login_required
def api_segment_data():
    # Get segment data for visualization
    segments = CustomerSegment.query.all()
    
    data = []
    for segment in segments:
        customer_count = segment.memberships.count()
        data.append({
            'name': segment.segment_name,
            'count': customer_count,
            'color': segment.color
        })
    
    return jsonify(data)

@bp.route('/api/rfm-data')
@login_required
def api_rfm_data():
    # Get RFM data for visualization
    transactions = db.session.query(
        Transaction.customer_id,
        Transaction.id,
        Transaction.total_amount,
        Transaction.created_at
    ).all()
    
    if not transactions:
        return jsonify({'error': 'No transaction data available'})
    
    # Convert to DataFrame
    df = pd.DataFrame([(t.customer_id, t.id, t.total_amount, t.created_at) for t in transactions],
                     columns=['customer_id', 'transaction_id', 'amount', 'date'])
    
    # Calculate RFM values
    current_date = datetime.now()
    
    # Recency: Days since last purchase
    recency_df = df.groupby('customer_id')['date'].max().reset_index()
    recency_df['recency'] = (current_date - recency_df['date']).dt.days
    recency_df = recency_df[['customer_id', 'recency']]
    
    # Frequency: Number of transactions
    frequency_df = df.groupby('customer_id')['transaction_id'].count().reset_index()
    frequency_df.columns = ['customer_id', 'frequency']
    
    # Monetary: Total amount spent
    monetary_df = df.groupby('customer_id')['amount'].sum().reset_index()
    monetary_df.columns = ['customer_id', 'monetary']
    
    # Merge RFM values
    rfm_df = recency_df.merge(frequency_df, on='customer_id').merge(monetary_df, on='customer_id')
    
    # Get segment information for each customer
    segment_info = db.session.query(
        CustomerSegmentMembership.customer_id,
        CustomerSegment.segment_name,
        CustomerSegment.color
    ).join(CustomerSegment).all()
    
    segment_df = pd.DataFrame([(s.customer_id, s.segment_name, s.color) for s in segment_info],
                             columns=['customer_id', 'segment_name', 'color'])
    
    # Merge with RFM data
    if not segment_df.empty:
        rfm_df = rfm_df.merge(segment_df, on='customer_id', how='left')
        rfm_df['segment_name'] = rfm_df['segment_name'].fillna('Not Segmented')
        rfm_df['color'] = rfm_df['color'].fillna('#6c757d')
    else:
        rfm_df['segment_name'] = 'Not Segmented'
        rfm_df['color'] = '#6c757d'
    
    # Convert to JSON
    data = rfm_df.to_dict(orient='records')
    
    return jsonify(data)