import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score  # <-- 1. Import
from models.transaction import Transaction
from sqlalchemy import func

class KMeansService:
    def __init__(self, n_clusters=3):
        self.n_clusters = n_clusters
        self.scaler = StandardScaler()
        self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)

    def get_rfm_data(self):
        """
        Mengambil data transaksi dan mengagregasikannya menjadi data RFM (Recency, Frequency, Monetary).
        """
        from app import db  # Import here to avoid circular dependency
        results = db.session.query(
            Transaction.customer_id,
            func.count(Transaction.id).label('frequency'),
            func.sum(Transaction.total_amount).label('monetary'),
            func.max(Transaction.created_at).label('last_purchase_date')
        ).group_by(Transaction.customer_id).all()

        if not results:
            return pd.DataFrame()

        rfm_df = pd.DataFrame(results)
        if not rfm_df.empty:
            rfm_df.columns = ['customer_id', 'frequency', 'monetary', 'last_purchase_date']
        
        # Hitung Recency
        current_date = pd.Timestamp.now()
        rfm_df['recency'] = (current_date - pd.to_datetime(rfm_df['last_purchase_date'])).dt.days

        return rfm_df

    def perform_segmentation(self, rfm_df):
        """
        Menjalankan algoritma K-Means, menghitung Silhouette Score, dan mengurutkan cluster.
        """
        if rfm_df.empty or len(rfm_df) < self.n_clusters:
            # Fallback jika data kurang dari jumlah cluster
            effective_n_clusters = len(rfm_df) if not rfm_df.empty else 1
            if effective_n_clusters <= 1:
                # Tidak bisa menghitung score jika hanya ada 1 cluster atau kurang
                return rfm_df, None
            self.model = KMeans(n_clusters=effective_n_clusters, random_state=42, n_init=10)
        
        # Scaling
        rfm_features = rfm_df[['recency', 'frequency', 'monetary']]
        rfm_scaled = self.scaler.fit_transform(rfm_features)
        
        # Fitting
        rfm_df['cluster'] = self.model.fit_predict(rfm_scaled)
        
        # <-- 2. Hitung Silhouette Score
        # Skor dihitung setelah fitting, menggunakan data yang sudah di-scale dan label cluster
        score = silhouette_score(rfm_scaled, rfm_df['cluster'])
        
        # Sorting Clusters (0 = Highest Monetary/VIP)
        cluster_summary = rfm_df.groupby('cluster')['monetary'].mean().reset_index()
        cluster_summary = cluster_summary.sort_values('monetary', ascending=False).reset_index(drop=True)
        
        # Mapping Old Cluster ID -> New Sorted ID
        cluster_map = {row['cluster']: i for i, row in cluster_summary.iterrows()}
        rfm_df['cluster_sorted'] = rfm_df['cluster'].map(cluster_map)
        
        return rfm_df, score # <-- 3. Return score

    def analyze(self):
        """
        Pipeline utama: Get Data -> Segmentasi -> Return DataFrame dan Silhouette Score
        """
        rfm_df = self.get_rfm_data()
        if rfm_df.empty or len(rfm_df) < self.n_clusters:
            return None, None # Return two values
            
        result_df, score = self.perform_segmentation(rfm_df)
        return result_df, score # <-- 4. Return both
