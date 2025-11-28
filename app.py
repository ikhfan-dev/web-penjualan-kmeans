from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from config import Config
import pandas as pd

import random
from datetime import datetime, timedelta
from faker import Faker

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
    
    # Import models
    from models.user import User
    from models.customer import Customer
    from models.product import Product
    from models.transaction import Transaction, TransactionItem
    from models.analytics import CustomerSegment, CustomerSegmentMembership, Promotion
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
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
    
    # Main routes
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    @app.cli.command("seed-db")

    def seed_db_command():
        """Seed the database with dummy data, run K-Means, and create promotions."""
        fake = Faker('id_ID')
        
        print("🌱 Memulai proses seeding database...")

        with app.app_context():
            # Hapus data lama
            print("🗑️  Menghapus data lama...")
            db.session.query(TransactionItem).delete()
            db.session.query(Transaction).delete()
            db.session.query(CustomerSegmentMembership).delete()
            db.session.query(Promotion).delete()
            db.session.query(CustomerSegment).delete()
            db.session.query(Customer).delete()
            db.session.query(Product).delete()
            db.session.query(User).delete()
            db.session.commit()

            # 1. Buat Users
            print("👤 Membuat data user...")
            admin_user = User(username='admin', email='admin@pos.com', role='admin')
            kasir_user = User(username='kasir', email='kasir@pos.com', role='cashier')
            admin_user.set_password('password')
            kasir_user.set_password('password')
            db.session.add_all([admin_user, kasir_user])
            db.session.commit()
            user_ids = [admin_user.id, kasir_user.id]

            # 2. Buat Produk
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
            
            products = []
            for i, p in enumerate(products_data):
                products.append(Product(
                    sku=f'PRD-{i+1:03}', name=p['name'], description=fake.sentence(),
                    price=p['price'], stock=p['stock'], category=p['category'], unit=p['unit']
                ))
            db.session.add_all(products)
            db.session.commit()

            # 3. Buat Pelanggan
            print("👥 Membuat data pelanggan...")
            customers = []
            for _ in range(1000):
                customers.append(Customer(name=fake.name(), phone=fake.phone_number(), email=fake.email(), address=fake.address()))
            db.session.add_all(customers)
            db.session.commit()
            
            # 4. Buat Transaksi
            print("🧾 Membuat data transaksi...")
            transactions = []
            today = datetime.now()
            
            for customer in customers:
                if random.random() < 0.1:
                    num_transactions = random.randint(10, 25)
                    last_purchase_date = today - timedelta(days=random.randint(1, 15))
                elif random.random() < 0.3:
                    num_transactions = random.randint(5, 10)
                    last_purchase_date = today - timedelta(days=random.randint(5, 30))
                else:
                    num_transactions = random.randint(1, 4)
                    last_purchase_date = today - timedelta(days=random.randint(20, 180))
                
                for i in range(num_transactions):
                    if i == num_transactions - 1:
                        trans_date = last_purchase_date
                    else:
                        days_ago = random.randint(1, (today - last_purchase_date).days + 30)
                        trans_date = last_purchase_date - timedelta(days=days_ago)
                    
                    num_items = random.randint(1, 4)
                    items = random.sample(products, num_items)
                    
                    transaction = Transaction(
                        customer_id=customer.id, user_id=random.choice(user_ids),
                        total_amount=0, created_at=trans_date
                    )
                    
                    total_amount = 0
                    for item in items:
                        quantity = random.randint(1, 3)
                        price = item.price
                        subtotal = price * quantity
                        total_amount += subtotal
                        
                        transaction.items.append(TransactionItem(
                            product_id=item.id, quantity=quantity, price=price
                        ))
                    
                    transaction.total_amount = total_amount
                    transactions.append(transaction)
            
            db.session.add_all(transactions)
            db.session.commit()
            
            # --- AWAL PERUBAAN BESAR: JALANKAN K-MEANS DARI SINI ---
            print("🔍 Menjalankan analisis K-Means otomatis...")
            
            # Get transaction data
            trans_data = db.session.query(Transaction.customer_id, Transaction.id, Transaction.total_amount, Transaction.created_at).all()
            
            if trans_data:
                # Convert to DataFrame
                df = pd.DataFrame([(t.customer_id, t.id, t.total_amount, t.created_at) for t in trans_data],
                                    columns=['customer_id', 'transaction_id', 'amount', 'date'])
                
                # Calculate RFM values
                current_date = datetime.now()
                
                # Recency: Days since last purchase
                recency_df = df.groupby('customer_id')['date'].max().reset_index()
                # PERBAIKAN: .days, bukan .dt.days
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
                n_clusters = 3 # Gunakan 3 cluster untuk seeder
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                rfm_df['cluster'] = kmeans.fit_predict(rfm_scaled)
                
                # Create segments
                segment_names = ['VIP', 'Frequent Buyer', 'Occasional Shopper']
                segment_colors = ['#28a745', '#007bff', '#ffc107']
                
                for i in range(n_clusters):
                    cluster_data = rfm_df[rfm_df['cluster'] == i]
                    avg_recency = cluster_data['recency'].mean()
                    avg_frequency = cluster_data['frequency'].mean()
                    avg_monetary = cluster_data['monetary'].mean()
                    
                    segment_name = segment_names[i]
                    segment_color = segment_colors[i]
                    description = f'Pelanggan dengan rata-rata pembelian {avg_frequency:.1f}x, ' \
                                f'total belanja Rp {avg_monetary:,.0f}, ' \
                                f'dan pembelian terakhir {avg_recency:.0f} hari yang lalu.'
                    
                    segment = CustomerSegment(
                        segment_name=segment_name, description=description, color=segment_color
                    )
                    db.session.add(segment)
                    db.session.flush()
                    
                    for _, row in cluster_data.iterrows():
                        membership = CustomerSegmentMembership(customer_id=row['customer_id'], segment_id=segment.id)
                        db.session.add(membership)
                
                # Handle new customers
                new_customers_query = db.session.query(Customer).filter(~Customer.transactions.any()).all()
                new_customer_ids = {customer.id for customer in new_customers_query}
                
                if new_customer_ids:
                    new_segment = CustomerSegment(segment_name='New Customer', description='Pelanggan yang belum pernah melakukan transaksi.', color='#6c757d')
                    db.session.add(new_segment)
                    db.session.flush()
                    
                    for customer_id in new_customer_ids:
                        membership = CustomerSegmentMembership(customer_id=customer_id, segment_id=new_segment.id)
                        db.session.add(membership)
            
            print("✅ Analisis K-Means selesai.")
            # --- AKHIR PERUBAAN BESAR ---
            
            # --- SEKARANG, BUAT PROMOSI (INI AKAN BERHASIL) ---
            print("🎁 Membuat data promosi...")
            promotions_data = [
                {'segment_name': 'VIP', 'type': 'percentage_discount', 'value': 10.0, 'desc': 'Diskon 10% untuk semua produk'},
                {'segment_name': 'Frequent Buyer', 'type': 'percentage_discount', 'value': 5.0, 'desc': 'Diskon 5% untuk semua produk'},
                {'segment_name': 'Occasional Shopper', 'type': 'percentage_discount', 'value': 2.0, 'desc': 'Diskon 2% untuk pembelian di atas Rp 100.000'},
                {'segment_name': 'New Customer', 'type': 'fixed_discount', 'value': 5000.0, 'desc': 'Diskon Rp 5.000 untuk pembelian pertama'},
            ]
            
            for promo_data in promotions_data:
                segment = CustomerSegment.query.filter_by(segment_name=promo_data['segment_name']).first()
                if segment:
                    promotion = Promotion(
                        segment_id=segment.id, promotion_type=promo_data['type'],
                        promotion_value=promo_data['value'], description=promo_data['desc']
                    )
                    db.session.add(promotion)
            
            db.session.commit()
            print("✅ Promosi berhasil dibuat.")
            # --- AKHIR PEMBUATAN PROMOSI ---
            
            print("✅ Database berhasil diisi dengan data dummy, segmen, dan promosi!")
            print(f"   - {User.query.count()} User")
            print(f"   - {Product.query.count()} Produk")
            print(f"   - {Customer.query.count()} Pelanggan")
            print(f"   - {Transaction.query.count()} Transaksi")
            print(f"   - {CustomerSegment.query.count()} Segmen")
            print(f"   - {Promotion.query.count()} Promosi")
            print("\n🎉 Aplikasi siap digunakan. Login dengan 'admin' / 'password'.")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
