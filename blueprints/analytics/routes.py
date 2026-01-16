from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.analytics import bp
from models.customer import Customer
from models.transaction import Transaction, TransactionItem
from models.analytics import CustomerSegment, CustomerSegmentMembership, Promotion
from app import db
from datetime import datetime
import pandas as pd
from utils.decorators import admin_required
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload

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
    
    page = request.args.get('page', 1, type=int)
    customers_query = db.session.query(Customer).join(CustomerSegmentMembership).filter(
        CustomerSegmentMembership.segment_id == id
    )
    customers = customers_query.paginate(page=page, per_page=20, error_out=False)
    
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
        
    total_discount_given = db.session.query(func.sum(Transaction.discount_amount))\
        .join(Customer, Transaction.customer_id == Customer.id)\
        .join(CustomerSegmentMembership, Customer.id == CustomerSegmentMembership.customer_id)\
        .filter(CustomerSegmentMembership.segment_id == id)\
        .scalar() or 0

    return render_template('analytics/segment_detail.html', 
                          segment=segment, 
                          customers=customers,
                          discount_history=discount_history,
                          total_discount_given=total_discount_given)

@bp.route('/run_kmeans', methods=['GET', 'POST'])
@admin_required
@login_required
def run_kmeans():
    if request.method == 'POST':
        n_clusters = int(request.form.get('n_clusters', 3))
        
        try:
            from utils.kmeans_service import KMeansService
            
            kmeans_service = KMeansService(n_clusters=n_clusters)
            rfm_df, score = kmeans_service.analyze()

            if rfm_df is None or rfm_df.empty:
                flash('Data tidak cukup untuk analisis atau tidak ada transaksi.', 'warning')
                return redirect(url_for('analytics.dashboard'))

            flash_message = f'Analisis K-Means selesai. {len(rfm_df)} pelanggan aktif dianalisis.'
            if score is not None:
                flash_message += f' — **Silhouette Score: {score:.4f}**'
            
            flash(flash_message, 'success')
            
            CustomerSegmentMembership.query.delete()
            
            existing_segments = CustomerSegment.query.filter(
                CustomerSegment.segment_name != 'New Customer'
            ).order_by(CustomerSegment.id).all()
            
            default_names = [
                'VIP',
                'Frequent Buyer',
                'Occasional Shopper',
                'At Risk',
                'New Customer'
            ]
            
            default_colors = ['#28a745', '#007bff', '#ffc107', '#6c757d', '#17a2b8']
            
            new_customer_segment_id = None

            for i in range(n_clusters):
                cluster_data = rfm_df[rfm_df['cluster_sorted'] == i]
                
                avg_recency = cluster_data['recency'].mean()
                avg_frequency = cluster_data['frequency'].mean()
                avg_monetary = cluster_data['monetary'].mean()
                
                description = f'Rata-rata belanja Rp {avg_monetary:,.0f}, ' \
                             f'frekuensi {avg_frequency:.1f}x, ' \
                             f'terakhir transaksi {avg_recency:.0f} hari lalu.'

                segment = None
                
                if i < len(existing_segments):
                    segment = existing_segments[i]
                    segment.description = description
                else:
                    if i < len(default_names):
                        new_name = default_names[i]
                        new_color = default_colors[i]
                    else:
                        new_name = f'Segmen {i+1}'
                        new_color = '#6c757d'
                        
                    segment = CustomerSegment.query.filter_by(segment_name=new_name).first()
                    
                    if not segment:
                        segment = CustomerSegment(
                            segment_name=new_name,
                            description=description,
                            color=new_color
                        )
                        db.session.add(segment)
                    else:
                        segment.description = description
                        if segment.color == '#007bff':
                            segment.color = new_color
                            
                    db.session.flush()
                
                if segment.segment_name == 'New Customer':
                    new_customer_segment_id = segment.id

                memberships = []
                for _, row in cluster_data.iterrows():
                    memberships.append({
                        'customer_id': row['customer_id'],
                        'segment_id': segment.id
                    })
                
                if memberships:
                    db.session.bulk_insert_mappings(CustomerSegmentMembership, memberships)
            
            analyzed_customer_ids = rfm_df['customer_id'].tolist()
            new_customers = db.session.query(Customer.id).filter(
                ~Customer.id.in_(analyzed_customer_ids)
            ).all()
            
            if new_customers:
                target_segment_id = None
                
                if new_customer_segment_id:
                    target_segment_id = new_customer_segment_id
                else:
                    zero_segment_name = 'New Customer'
                    zero_segment = CustomerSegment.query.filter_by(segment_name=zero_segment_name).first()
                    
                    if not zero_segment:
                        zero_segment = CustomerSegment(
                            segment_name=zero_segment_name, 
                            description="Pelanggan yang belum pernah melakukan transaksi",
                            color="#17a2b8"
                        )
                        db.session.add(zero_segment)
                        db.session.flush()
                    
                    target_segment_id = zero_segment.id
                
                zero_memberships = [{'customer_id': c.id, 'segment_id': target_segment_id} for c in new_customers]
                db.session.bulk_insert_mappings(CustomerSegmentMembership, zero_memberships)

            db.session.commit()
            return redirect(url_for('analytics.dashboard'))
        
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
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
            'count': segment.memberships.count(),
            'color': segment.color
        })
    return jsonify(data)

@bp.route('/api/rfm-data')
@login_required
def api_rfm_data():
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
    .group_by(CustomerSegmentMembership.customer_id, CustomerSegment.id, CustomerSegment.segment_name, CustomerSegment.color)\
    .all()

    summary_stats = []
    results_list = []

    if raw_data:
        df = pd.DataFrame(raw_data)
        now = pd.Timestamp.now()
        df['recency'] = (now - pd.to_datetime(df['last_purchase'])).dt.days
        
        # 2. Hitung Ringkasan Statistik per Segmen
        summary_df = df.groupby(['segment_name', 'color']).agg(
            customer_count=('customer_id', 'count'),
            avg_recency=('recency', 'mean'),
            min_recency=('recency', 'min'),
            max_recency=('recency', 'max'),
            std_recency=('recency', 'std'),
            avg_frequency=('frequency', 'mean'),
            min_frequency=('frequency', 'min'),
            max_frequency=('frequency', 'max'),
            std_frequency=('frequency', 'std'),
            avg_monetary=('monetary', 'mean'),
            min_monetary=('monetary', 'min'),
            max_monetary=('monetary', 'max'),
            std_monetary=('monetary', 'std')
        ).reset_index()
        
        # Ganti nama kolom untuk flat structure
        summary_df.columns = [col[0] if isinstance(col, tuple) else col for col in summary_df.columns]
        
        for _, row in summary_df.iterrows():
            # Mengisi NaN dengan 0 untuk std jika hanya ada 1 data
            std_recency = row.get('std_recency', 0)
            std_frequency = row.get('std_frequency', 0)
            std_monetary = row.get('std_monetary', 0)

            summary_stats.append({
                'segment_name': row['segment_name'],
                'color': row['color'],
                'count': row['customer_count'],
                'avg_recency': row['avg_recency'] if not pd.isna(row['avg_recency']) else -1,
                'min_recency': row['min_recency'] if not pd.isna(row['min_recency']) else -1,
                'max_recency': row['max_recency'] if not pd.isna(row['max_recency']) else -1,
                'std_recency': std_recency if not pd.isna(std_recency) else 0,
                'avg_frequency': row['avg_frequency'],
                'min_frequency': row['min_frequency'],
                'max_frequency': row['max_frequency'],
                'std_frequency': std_frequency if not pd.isna(std_frequency) else 0,
                'avg_monetary': row['avg_monetary'],
                'min_monetary': row['min_monetary'],
                'max_monetary': row['max_monetary'],
                'std_monetary': std_monetary if not pd.isna(std_monetary) else 0,
            })
            
        df['recency'] = df['recency'].fillna(-1)
        results_list = df.to_dict('records')

    return render_template('analytics/kmeans_results.html', 
                          results=results_list, 
                          summary_stats=summary_stats)

@bp.route('/reset-data', methods=['POST'])
@admin_required
@login_required
def reset_data():
    """Endpoint untuk mereset semua data transaksional dan pelanggan."""
    try:
        # Hapus data dengan urutan yang benar untuk menghindari error foreign key
        db.session.query(TransactionItem).delete()
        db.session.query(Transaction).delete()
        db.session.query(CustomerSegmentMembership).delete()
        db.session.query(Promotion).delete()
        db.session.query(CustomerSegment).delete()
        db.session.query(Customer).delete()
        
        db.session.commit()
        flash('Semua data pelanggan, transaksi, dan segmentasi berhasil direset.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mereset data: {str(e)}', 'danger')
        
    return redirect(url_for('analytics.dashboard'))