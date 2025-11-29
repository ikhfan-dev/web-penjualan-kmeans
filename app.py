from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from config import Config
import pandas as pd
import numpy as np # Import numpy

import random
from datetime import datetime, timedelta
from faker import Faker

# Inisialisasi Extension di luar fungsi create_app agar bisa diimport
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Init Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
    
    # --- 1. SETUP FILTER TEMPLATE (FORMAT RUPIAH) ---
    @app.template_filter('rp')
    def format_rupiah(value):
        try:
            if value is None:
                return "Rp 0"
            # Format: Rp 10.000 (menggunakan library bawaan python string formatting)
            return f"Rp {float(value):,.0f}".replace(',', '.')
        except (ValueError, TypeError):
            return "Rp 0"

    # --- 2. IMPORT MODELS ---
    # Import di sini untuk menghindari circular import
    from models.user import User
    from models.customer import Customer
    from models.product import Product
    from models.transaction import Transaction, TransactionItem
    from models.analytics import CustomerSegment, CustomerSegmentMembership, Promotion
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # --- 3. REGISTER BLUEPRINTS ---
    from blueprints.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from blueprints.products import bp as products_bp
    app.register_blueprint(products_bp, url_prefix='/products')
    
    from blueprints.customers import bp as customers_bp
    app.register_blueprint(customers_bp, url_prefix='/customers')
    
    from blueprints.sales import bp as sales_bp
    app.register_blueprint(sales_bp, url_prefix='/sales')
    
    from blueprints.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    
    from blueprints.promotions import bp as promotions_bp
    app.register_blueprint(promotions_bp, url_prefix='/promotions')

    from blueprints.segments import bp as segments_bp
    app.register_blueprint(segments_bp, url_prefix='/segments')
    
    # --- 4. MAIN ROUTES ---
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    # --- 5. CLI COMMAND: SEED DB ---
    @app.cli.command("seed-db")
    def seed_db_command():
        """Isi database dengan data dummy, jalankan K-Means, dan buat promosi."""
        fake = Faker('id_ID')
        print("🌱 Memulai proses seeding database...")

        # Hapus data lama (Urutan penting karena Foreign Key!)
        print("🗑️  Menghapus data lama...")
        try:
            db.session.query(TransactionItem).delete()
            db.session.query(Transaction).delete()
            db.session.query(CustomerSegmentMembership).delete()
            db.session.query(Promotion).delete()
            db.session.query(CustomerSegment).delete()
            db.session.query(Customer).delete() # Customer dihapus setelah transaksi
            db.session.query(Product).delete()
            db.session.query(User).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"⚠️  Gagal menghapus data lama (mungkin tabel belum ada): {e}")

        # A. Buat Users
        print("👤 Membuat data user...")
        admin_user = User(username='admin', email='admin@pos.com', role='admin')
        kasir_user = User(username='kasir', email='kasir@pos.com', role='cashier')
        admin_user.set_password('password')
        kasir_user.set_password('password')
        db.session.add_all([admin_user, kasir_user])
        db.session.commit()
        user_ids = [admin_user.id, kasir_user.id]

        # B. Buat Produk
        print("📦 Membuat data produk...")
        products_data = [
            # --- A ---

            {'name': 'ABC Susu Kopi', 'category': 'minuman', 'price': 2500, 'stock': 180, 'unit': 'sachet'},

            {'name': 'Ale-Ale', 'category': 'minuman', 'price': 1000, 'stock': 200, 'unit': 'pcs'},

            {'name': 'ABC Batre', 'category': 'lainnya', 'price': 3000, 'stock': 40, 'unit': 'pcs'},

            {'name': 'Aqua Gelas', 'category': 'minuman', 'price': 500, 'stock': 300, 'unit': 'gelas'},

            {'name': 'Aqua Botol', 'category': 'minuman', 'price': 3000, 'stock': 150, 'unit': 'botol'},

            {'name': 'Antangin', 'category': 'obat', 'price': 4000, 'stock': 90, 'unit': 'sachet'},

            {'name': 'Amplop', 'category': 'lainnya', 'price': 500, 'stock': 120, 'unit': 'pcs'},

            {'name': 'Adem Sari', 'category': 'minuman', 'price': 2500, 'stock': 160, 'unit': 'sachet'},


            # --- B ---

            {'name': 'Buku Tulis', 'category': 'sekolah', 'price': 3000, 'stock': 70, 'unit': 'pcs'},

            {'name': 'Beng-Beng', 'category': 'makanan', 'price': 2500, 'stock': 140, 'unit': 'pcs'},

            {'name': 'Bango Kecap Kecil', 'category': 'sembako', 'price': 1000, 'stock': 60, 'unit': 'sachet'},

            {'name': 'Bango Kecap Sedang', 'category': 'sembako', 'price': 3000, 'stock': 80, 'unit': 'botol'},

            {'name': 'Bodrex', 'category': 'obat', 'price': 1000, 'stock': 90, 'unit': 'tablet'},


            # --- C ---

            {'name': 'Cibodas Air Mineral', 'category': 'minuman', 'price': 500, 'stock': 250, 'unit': 'gelas'},

            {'name': 'Cimory Yogurt', 'category': 'minuman', 'price': 3000, 'stock': 120, 'unit': 'botol'},

            {'name': 'Chiki Citato', 'category': 'makanan', 'price': 2000, 'stock': 180, 'unit': 'pak'},

            {'name': 'Class Mild Rokok', 'category': 'rokok', 'price': 30000, 'stock': 50, 'unit': 'bungkus'},

            {'name': 'Clear Sampo', 'category': 'rumah tangga', 'price': 1000, 'stock': 200, 'unit': 'sachet'},

            {'name': 'Cuka', 'category': 'sembako', 'price': 1000, 'stock': 100, 'unit': 'botol'},


            # --- D ---

            {'name': 'Downy Pewangi', 'category': 'rumah tangga', 'price': 1000, 'stock': 150, 'unit': 'sachet'},

            {'name': 'Diapet', 'category': 'obat', 'price': 1000, 'stock': 100, 'unit': 'tablet'},


            # --- E ---

            {'name': 'Energen', 'category': 'minuman', 'price': 2000, 'stock': 180, 'unit': 'sachet'},

            {'name': 'Envio Rokok', 'category': 'rokok', 'price': 1500, 'stock': 90, 'unit': 'bungkus'},

            {'name': 'Entrostop', 'category': 'obat', 'price': 1000, 'stock': 100, 'unit': 'strip'},

            {'name': 'Extra Joss', 'category': 'minuman', 'price': 1500, 'stock': 200, 'unit': 'sachet'},


            # --- F ---

            {'name': 'Fanta', 'category': 'minuman', 'price': 3500, 'stock': 120, 'unit': 'botol'},

            {'name': 'Floridina', 'category': 'minuman', 'price': 3500, 'stock': 130, 'unit': 'botol'},

            {'name': 'Frisian Flag', 'category': 'minuman', 'price': 2500, 'stock': 150, 'unit': 'sachet'},


            # --- G ---

            {'name': 'Garuda Kacang Atom', 'category': 'makanan', 'price': 1000, 'stock': 170, 'unit': 'pcs'},

            {'name': 'Gift Sabun', 'category': 'rumah tangga', 'price': 3500, 'stock': 110, 'unit': 'batang'},

            {'name': 'Gudang Garam Rokok', 'category': 'rokok', 'price': 26000, 'stock': 60, 'unit': 'bungkus'},

            {'name': 'Gula Pasir 1/4kg', 'category': 'sembako', 'price': 4000, 'stock': 80, 'unit': 'pak'},

            {'name': 'Good Day (Sachetan)', 'category': 'minuman', 'price': 2000, 'stock': 200, 'unit': 'sachet'},

            {'name': 'Garam', 'category': 'sembako', 'price': 1500, 'stock': 90, 'unit': 'pak'},

            {'name': 'Gillette Cukuran Kumis', 'category': 'lainnya', 'price': 6000, 'stock': 40, 'unit': 'pcs'},


            # --- H ---

            {'name': 'Head & Shoulders Sampo', 'category': 'rumah tangga', 'price': 1000, 'stock': 150, 'unit': 'sachet'},

            {'name': 'Hansaplast', 'category': 'obat', 'price': 500, 'stock': 100, 'unit': 'pcs'},


            # --- I ---

            {'name': 'Indomie Semua Jenis', 'category': 'makanan', 'price': 3500, 'stock': 300, 'unit': 'bungkus'},


            # --- J ---

            {'name': 'Jarum Super Rokok', 'category': 'rokok', 'price': 26000, 'stock': 60, 'unit': 'bungkus'},

            {'name': 'Jarum Kretek', 'category': 'rokok', 'price': 17000, 'stock': 70, 'unit': 'bungkus'},

            {'name': 'Jie Sam Soe', 'category': 'rokok', 'price': 21000, 'stock': 50, 'unit': 'bungkus'},

            {'name': 'Jazzy Bold', 'category': 'rokok', 'price': 25000, 'stock': 40, 'unit': 'bungkus'},


            # --- K ---

            {'name': 'Koyo Cabe', 'category': 'obat', 'price': 1500, 'stock': 90, 'unit': 'lembar'},

            {'name': 'Kiss Permen', 'category': 'makanan', 'price': 130, 'stock': 300, 'unit': 'pcs'},

            {'name': 'Kopiko', 'category': 'makanan', 'price': 150, 'stock': 300, 'unit': 'pcs'},

            {'name': 'Korek Api', 'category': 'lainnya', 'price': 2000, 'stock': 100, 'unit': 'pcs'},

            {'name': 'Kapal Api (Sachetan)', 'category': 'minuman', 'price': 2500, 'stock': 180, 'unit': 'sachet'},

            {'name': 'Kacang', 'category': 'makanan', 'price': 1000, 'stock': 150, 'unit': 'pcs'},

            {'name': 'Kalpa', 'category': 'makanan', 'price': 2500, 'stock': 120, 'unit': 'pcs'},

            {'name': 'Kopi Luwak (Sachetan)', 'category': 'minuman', 'price': 2000, 'stock': 200, 'unit': 'sachet'},

            {'name': 'Kratingdeng', 'category': 'minuman', 'price': 7000, 'stock': 80, 'unit': 'botol'},


            # --- L ---

            {'name': 'Larutan K3', 'category': 'minuman', 'price': 7000, 'stock': 90, 'unit': 'botol'},

            {'name': 'Lifebuoy Sampo', 'category': 'rumah tangga', 'price': 1000, 'stock': 120, 'unit': 'sachet'},

            {'name': 'Liong Bulan Kopi (Sachetan)', 'category': 'minuman', 'price': 2500, 'stock': 140, 'unit': 'sachet'},

            {'name': 'Lux Sabun', 'category': 'rumah tangga', 'price': 3500, 'stock': 100, 'unit': 'batang'},

            {'name': 'Le Minerale Gelas', 'category': 'minuman', 'price': 3000, 'stock': 200, 'unit': 'gelas'},

            {'name': 'Le Minerale Botol', 'category': 'minuman', 'price': 3000, 'stock': 150, 'unit': 'botol'},

            {'name': 'Lakban Bening', 'category': 'lainnya', 'price': 1000, 'stock': 60, 'unit': 'pcs'},

            {'name': 'Lampu 10W', 'category': 'rumah tangga', 'price': 15000, 'stock': 40, 'unit': 'pcs'},


            # --- M ---

            {'name': 'Magnum Rokok', 'category': 'rokok', 'price': 26000, 'stock': 60, 'unit': 'bungkus'},

            {'name': 'Molto Pewangi', 'category': 'rumah tangga', 'price': 500, 'stock': 200, 'unit': 'sachet'},

            {'name': 'Masako', 'category': 'makanan', 'price': 500, 'stock': 250, 'unit': 'sachet'},

            {'name': 'Mixagrip', 'category': 'obat', 'price': 1000, 'stock': 90, 'unit': 'tablet'},

            {'name': 'Mama Lemon (Kecil)', 'category': 'rumah tangga', 'price': 1000, 'stock': 80, 'unit': 'botol'},

            {'name': 'Masker', 'category': 'lainnya', 'price': 2000, 'stock': 150, 'unit': 'pcs'},

            {'name': 'Materai', 'category': 'lainnya', 'price': 12000, 'stock': 50, 'unit': 'pcs'},


            # --- N ---

            {'name': 'Nuvo Sabun', 'category': 'rumah tangga', 'price': 3500, 'stock': 90, 'unit': 'batang'},

            {'name': 'Neozep', 'category': 'obat', 'price': 1000, 'stock': 100, 'unit': 'tablet'},


            # --- O ---

            {'name': 'Oskadon', 'category': 'obat', 'price': 1000, 'stock': 100, 'unit': 'tablet'},

            {'name': 'Okky Jelly Drink', 'category': 'minuman', 'price': 2000, 'stock': 200, 'unit': 'pcs'},


            # --- P ---

            {'name': 'Power F', 'category': 'lainnya', 'price': 1000, 'stock': 60, 'unit': 'pcs'},

            {'name': 'Passeo Tisu', 'category': 'rumah tangga', 'price': 3000, 'stock': 120, 'unit': 'pak'},

            {'name': 'Pampes', 'category': 'rumah tangga', 'price': 2000, 'stock': 100, 'unit': 'pcs'},

            {'name': 'Plastik 1kg', 'category': 'lainnya', 'price': 8000, 'stock': 90, 'unit': 'pak'},

            {'name': 'Paramex', 'category': 'obat', 'price': 1000, 'stock': 80, 'unit': 'tablet'},

            {'name': 'Pocari Sweat', 'category': 'minuman', 'price': 8000, 'stock': 130, 'unit': 'botol'},


            # --- S ---

            {'name': 'Sampoerna Mild', 'category': 'rokok', 'price': 35000, 'stock': 70, 'unit': 'bungkus'},

            {'name': 'Susu Beruang', 'category': 'minuman', 'price': 12000, 'stock': 90, 'unit': 'kaleng'},

            {'name': 'Surya 16 Rokok', 'category': 'rokok', 'price': 36000, 'stock': 60, 'unit': 'bungkus'},

            {'name': 'Sariwangi Teh', 'category': 'minuman', 'price': 1000, 'stock': 180, 'unit': 'sachet'},

            {'name': 'Salonpas', 'category': 'obat', 'price': 2000, 'stock': 70, 'unit': 'lembar'},

            {'name': 'Soklin', 'category': 'rumah tangga', 'price': 1000, 'stock': 100, 'unit': 'sachet'},


            # --- T ---

            {'name': 'Teh Gelas', 'category': 'minuman', 'price': 1000, 'stock': 200, 'unit': 'gelas'},

            {'name': 'Teh Pucuk', 'category': 'minuman', 'price': 4000, 'stock': 150, 'unit': 'botol'},

            {'name': 'Tolak Angin', 'category': 'obat', 'price': 4000, 'stock': 90, 'unit': 'sachet'},


            # --- U ---

            {'name': 'Ultra Flu', 'category': 'obat', 'price': 1000, 'stock': 90, 'unit': 'tablet'},


            # --- Z ---

            {'name': 'Zinc Sampo', 'category': 'rumah tangga', 'price': 1000, 'stock': 120, 'unit': 'sachet'},

            ] 
        
        # Tambahan produk dummy agar data banyak
        for i in range(20):
             products_data.append({
                 'name': f'Produk Dummy {i}', 
                 'category': 'lainnya', 
                 'price': random.randint(10, 100) * 100, 
                 'stock': 100, 
                 'unit': 'pcs'
             })

        products = []
        for i, p in enumerate(products_data):
            products.append(Product(
                sku=f'PRD-{i+1:03}', name=p['name'], description=fake.sentence(),
                price=p['price'], stock=p['stock'], category=p['category'], unit=p['unit']
            ))
        db.session.add_all(products)
        db.session.commit()

        # C. Buat Pelanggan
        print("👥 Membuat 100 data pelanggan...")
        customers = []
        for _ in range(100):
            customers.append(Customer(name=fake.name(), phone=fake.phone_number()[:13], email=fake.email(), address=fake.address()))
        db.session.add_all(customers)
        db.session.commit()
        
        # D. Buat Transaksi (PENTING: Pola belanja variatif untuk K-Means)
        print("🧾 Membuat riwayat transaksi...")
        transactions = []
        today = datetime.now()
        
        for customer in customers:
            # Tentukan tipe pelanggan secara acak untuk simulasi data real
            rand_val = random.random()
            
            if rand_val < 0.1: # 10% Pelanggan Sultan (Banyak & Mahal)
                num_transactions = random.randint(15, 30)
                days_spread = 30
            elif rand_val < 0.4: # 30% Pelanggan Menengah
                num_transactions = random.randint(5, 15)
                days_spread = 60
            else: # 60% Pelanggan Jarang
                num_transactions = random.randint(1, 4)
                days_spread = 90
            
            for _ in range(num_transactions):
                days_ago = random.randint(0, days_spread)
                trans_date = today - timedelta(days=days_ago)
                
                # Buat transaksi
                transaction = Transaction(
                    customer_id=customer.id, user_id=random.choice(user_ids),
                    total_amount=0, created_at=trans_date # Total dihitung nanti
                )
                
                # Pilih item random
                num_items = random.randint(1, 5)
                items = random.sample(products, num_items)
                
                current_total = 0
                transaction_items_list = []
                
                for item in items:
                    qty = random.randint(1, 3)
                    price = item.price
                    subtotal = price * qty
                    current_total += subtotal
                    
                    transaction_items_list.append(TransactionItem(
                        product_id=item.id, quantity=qty, price=price
                    ))
                
                transaction.total_amount = current_total
                transaction.items = transaction_items_list # Assign items
                transactions.append(transaction)
        
        db.session.add_all(transactions)
        db.session.commit()
        
        # E. Jalankan K-Means Otomatis
        print("🔍 Menjalankan analisis K-Means & Sorting Segmen...")
        
        # Query Data Aggregate (Optimasi memori)
        # Gunakan Pandas read_sql agar lebih robust
        results = db.session.query(
            Transaction.customer_id, 
            db.func.count(Transaction.id).label('frequency'),
            db.func.sum(Transaction.total_amount).label('monetary'),
            db.func.max(Transaction.created_at).label('last_purchase_date')
        ).group_by(Transaction.customer_id).all()
        
        if results:
            # Konversi hasil query (List of Row objects) langsung ke DataFrame
            rfm_df = pd.DataFrame(results)
            
            # Pastikan nama kolom sesuai (agar aman jika versi library berbeda)
            if not rfm_df.empty:
                rfm_df.columns = ['customer_id', 'frequency', 'monetary', 'last_purchase_date']

            # Hitung Recency
            current_date = pd.Timestamp.now()
            rfm_df['recency'] = (current_date - pd.to_datetime(rfm_df['last_purchase_date'])).dt.days
            
            # K-Means
            scaler = StandardScaler()
            rfm_scaled = scaler.fit_transform(rfm_df[['recency', 'frequency', 'monetary']])
            
            n_clusters = 3
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            rfm_df['cluster'] = kmeans.fit_predict(rfm_scaled)
            
            # --- CRITICAL: SORTING CLUSTER LOGIC ---
            # Kita urutkan cluster berdasarkan rata-rata Monetary (Uang)
            # Cluster dengan uang terbanyak jadi index 0 (VIP)
            cluster_summary = rfm_df.groupby('cluster')['monetary'].mean().reset_index()
            cluster_summary = cluster_summary.sort_values('monetary', ascending=False).reset_index(drop=True)
            
            # Buat mapping: ID Cluster Lama -> ID Cluster Baru (0=VIP, 1=Mid, 2=Low)
            cluster_map = {row['cluster']: i for i, row in cluster_summary.iterrows()}
            rfm_df['cluster_sorted'] = rfm_df['cluster'].map(cluster_map)
            
            segment_names = ['VIP / Prioritas', 'Pelanggan Setia', 'Pelanggan Biasa']
            segment_colors = ['#28a745', '#007bff', '#ffc107'] # Hijau, Biru, Kuning
            
            # Simpan Segmen ke DB
            segment_objects = []
            for i in range(n_clusters):
                # Statistik untuk deskripsi
                cluster_data = rfm_df[rfm_df['cluster_sorted'] == i]
                avg_m = cluster_data['monetary'].mean()
                avg_f = cluster_data['frequency'].mean()
                
                desc = f"Rata-rata belanja Rp {avg_m:,.0f} dengan frekuensi {avg_f:.1f}x."
                
                seg = CustomerSegment(
                    segment_name=segment_names[i] if i < len(segment_names) else f"Segmen {i}",
                    description=desc,
                    color=segment_colors[i] if i < len(segment_colors) else "#6c757d"
                )
                db.session.add(seg)
                db.session.flush() # Agar dapat ID
                segment_objects.append(seg)
                
                # Masukkan Member
                memberships = []
                for _, row in cluster_data.iterrows():
                    memberships.append({
                        'customer_id': row['customer_id'],
                        'segment_id': seg.id
                    })
                if memberships:
                    db.session.bulk_insert_mappings(CustomerSegmentMembership, memberships)
            
            # Handle Pelanggan Baru (Belum ada transaksi)
            # Ambil semua ID yang sudah dianalisis
            analyzed_ids = rfm_df['customer_id'].tolist()
            new_customers = db.session.query(Customer).filter(Customer.id.notin_(analyzed_ids)).all()
            
            if new_customers:
                new_seg = CustomerSegment(
                    segment_name="Pelanggan Baru", 
                    description="Belum pernah bertransaksi", 
                    color="#17a2b8" # Cyan
                )
                db.session.add(new_seg)
                db.session.flush()
                segment_objects.append(new_seg)
                
                new_memberships = [{'customer_id': c.id, 'segment_id': new_seg.id} for c in new_customers]
                db.session.bulk_insert_mappings(CustomerSegmentMembership, new_memberships)

            # F. Buat Promosi Berdasarkan Segmen yang Sudah Terbentuk
            print("🎁 Membuat data promosi otomatis...")
            
            # Kita gunakan segment_objects yang baru dibuat agar ID-nya valid
            promos = [
                {'name_match': 'VIP / Prioritas', 'type': 'percentage_discount', 'val': 10, 'desc': 'Diskon Spesial 10% Member VIP'},
                {'name_match': 'Pelanggan Setia', 'type': 'percentage_discount', 'val': 5, 'desc': 'Diskon 5% Tanda Terima Kasih'},
                {'name_match': 'Pelanggan Biasa', 'type': 'fixed_discount', 'val': 2000, 'desc': 'Potongan Rp 2.000'},
                {'name_match': 'Pelanggan Baru', 'type': 'fixed_discount', 'val': 5000, 'desc': 'Voucher Selamat Datang Rp 5.000'}
            ]
            
            for p in promos:
                # Cari segmen yang namanya cocok
                target_seg = next((s for s in segment_objects if s.segment_name == p['name_match']), None)
                if target_seg:
                    db.session.add(Promotion(
                        segment_id=target_seg.id,
                        promotion_type=p['type'],
                        promotion_value=p['val'],
                        description=p['desc']
                    ))
            
            db.session.commit()
            print("✅ Seeding Selesai! Login: admin / password")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)