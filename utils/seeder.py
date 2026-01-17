import random
from datetime import datetime, timedelta
from faker import Faker
import json
from sqlalchemy.orm import joinedload # <-- ADDED THIS IMPORT
from decimal import Decimal # <-- ADDED THIS IMPORT

# Helper function untuk mendapatkan tanggal acak dalam rentang
def get_random_date(start_date, end_date):
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date

def run_seeding(db):
    """Isi database dengan data dummy, jalankan K-Means, dan buat promosi."""
    
    # Import model di dalam fungsi untuk menghindari circular import saat app context dibutuhkan
    from models.user import User
    from models.customer import Customer
    from models.product import Product
    from models.transaction import Transaction, TransactionItem
    from models.analytics import CustomerSegment, CustomerSegmentMembership, Promotion
    from utils.kmeans_service import KMeansService

    fake = Faker('id_ID')
    print("🌱 Memulai proses seeding database...")

    # --- DEFINISI TANGGAL UNTUK TIMELINE ---
    discount_system_start_date = datetime(2025, 5, 1) # Mulai Mei (Jan-Apr Tanpa Promo)
    pre_system_start_date = datetime(2025, 1, 1)    # Mulai 1 Jan 2025
    current_date = datetime.now()                   # Tanggal saat ini
    # ----------------------------------------


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

    # B. Buat Produk dari file JSON
    print("📦 Membuat data produk dari JSON...")
    try:
        with open('seed_data/products.json', 'r', encoding='utf-8') as f:
            products_data = json.load(f)
    except FileNotFoundError:
        print("❌ Gagal: File 'seed_data/products.json' tidak ditemukan.")
        return
    
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
    real_customers_data = [
        {'name': 'Pak Ajat', 'phone': '+6281212831625', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Adel', 'phone': '+6285591323702', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Joni', 'phone': '+6285280918020', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Empik', 'phone': '+6285861361425', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Bu Lilin', 'phone': '+6281517924974', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Bu Ajal', 'phone': '+6281398812589', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Wak Dudin', 'phone': '+6285864337381', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Adit', 'phone': '+6285283331975', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Empik', 'phone': '+6285891293006', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Ibu Gorengan', 'phone': '+628568514579', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Asep Cibitung', 'phone': '+6285659415949', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Mama Fahri', 'phone': '+6285720980786', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Icha', 'phone': '+6285603291423', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Indah', 'phone': '+6285871464647', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Deny', 'phone': '+6282110837811', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Windy', 'phone': '+6285692678486', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Ajit', 'phone': '+6285811942466', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Ugan', 'phone': '+6285659937234', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Ujang', 'phone': '+6281460987884', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Teh Uni', 'phone': '+6285871732389', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Dede', 'phone': '+6285723621543', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Yeppi', 'phone': '+6285603151340', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Ade Nuryana', 'phone': '+6281522742178', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Mul', 'phone': '+6285864232099', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Ahmad gudang cahaya', 'phone': '+6285872128505', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Indra', 'phone': '+6285661537274', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Giesendrayogi', 'phone': '+6281380440649', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Nia vila daun mas', 'phone': '+6282213689742', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Cici', 'phone': '+6285722556929', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Ni Putu Hilda', 'phone': '+628562269105', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Rahmat', 'phone': '+6281377000150', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Dede bu mely', 'phone': '+62895415494449', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Rehan sopir angkot', 'phone': '+628979890824', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Reno', 'phone': '+6285178261266', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Mulyadi ojol', 'phone': '+628164642896', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Abdul', 'phone': '+6285325518452', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Jajang cibitung', 'phone': '+6281572762626', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Iyang', 'phone': '+6283811991075', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Ine Rahma', 'phone': '+6285860986804', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Titi Amel', 'phone': '+6281282949618', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Pak Cece', 'phone': '+6285603134553', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Teh Puloh', 'phone': '+6285798762325', 'address': 'Limusnunggal, Sukabumi'},
        {'name': 'Bu Lin', 'phone': '+6281517924974', 'address': 'Limusnunggal, Sukabumi'}
    ]
    
    customers = []
    print(f"👥 Membuat {len(real_customers_data)} data pelanggan real...")
    for customer_data in real_customers_data:
        customers.append(Customer(
            name=customer_data['name'], 
            phone=customer_data['phone'],
            address=customer_data['address']
        ))

    # Tambah 1000 data dummy dengan alamat spesifik
    num_dummy_customers = 1000
    print(f"👥 Membuat {num_dummy_customers} data pelanggan dummy dengan alamat Limusnunggal, Sukabumi...")
    for _ in range(num_dummy_customers):
        customers.append(Customer(
            name=fake.name(), 
            phone='+62' + fake.phone_number()[:13], # Ensure +62 prefix
            email=None, # No email for dummy customers
            address="Limusnunggal, Sukabumi"
        ))
    
    print(f"Total pelanggan yang akan dibuat: {len(customers)}")
    db.session.add_all(customers)
    db.session.commit()

    
    # D. Buat Transaksi (PENTING: Pola belanja variatif untuk K-Means)
    print("🧾 Membuat riwayat transaksi (Jan 2025 - Sekarang)...")
    transactions = []
    covered_dates = set() # Untuk melacak tanggal yang sudah ada transaksinya
    
    # Pastikan ada produk untuk dijadikan sampel
    if not products:
        print("❌ Tidak ada produk di database untuk membuat transaksi.")
        return

    # Eager load CustomerSegment dan Promotion
    all_segments = CustomerSegment.query.options(joinedload(CustomerSegment.promotion)).all()
    segment_promo_map = {}
    for seg in all_segments:
        segment_promo_map[seg.id] = seg.promotion

    # --- 1. Generate Transaksi Utama per Customer ---
    for customer in customers:
        rand_val = random.random()
        
        # Logika VIP vs Regular
        if rand_val < 0.1: # VIP (Belanja banyak)
            num_transactions = random.randint(15, 30)
        elif rand_val < 0.4: # Frequent Buyer
            num_transactions = random.randint(5, 15)
        else: # Occasional Shopper
            num_transactions = random.randint(1, 4)
        
        for _ in range(num_transactions):
            # Acak tanggal dari 1 Jan 2025 s/d Sekarang
            trans_date = get_random_date(pre_system_start_date, current_date)
            covered_dates.add(trans_date.date()) # Catat tanggal
            
            # Buat transaksi
            transaction = Transaction(
                customer_id=customer.id, user_id=random.choice(user_ids),
                total_amount=0, created_at=trans_date
            )
            
            # Pilih item random
            num_items_to_sample = min(len(products), 5)
            num_items = random.randint(1, num_items_to_sample)
            items = random.sample(products, num_items)
            
            current_total = Decimal('0')
            transaction_items_list = []
            
            for item in items:
                qty = random.randint(1, 3)
                price = Decimal(str(item.price))
                subtotal = price * qty
                current_total += subtotal
                
                transaction_item = TransactionItem(
                    product_id=item.id, quantity=qty, price=item.price
                )
                transaction_items_list.append(transaction_item)
            
            # --- Perhitungan Diskon Kondisional (Jan-Apr: NO, Mei+: YES) ---
            discount_amount = Decimal('0')
            if trans_date >= discount_system_start_date:
                customer_segment_membership = db.session.query(CustomerSegmentMembership)\
                                                    .filter_by(customer_id=customer.id)\
                                                    .first()
                if customer_segment_membership:
                    segment_id = customer_segment_membership.segment_id
                    active_promo = segment_promo_map.get(segment_id)

                    if active_promo:
                        if active_promo.promotion_type == 'percentage_discount':
                            discount_amount = current_total * (Decimal(str(active_promo.promotion_value)) / 100)
                        elif active_promo.promotion_type == 'fixed_discount':
                            discount_amount = Decimal(str(active_promo.promotion_value))
            
            if discount_amount > current_total:
                discount_amount = current_total
            
            transaction.total_amount = current_total - discount_amount
            transaction.discount_amount = discount_amount
            transaction.items = transaction_items_list
            transactions.append(transaction)

    # --- 2. Gap Filling: Pastikan Setiap Tanggal Ada Transaksi ---
    print("🗓️  Memeriksa dan mengisi tanggal yang kosong...")
    total_days = (current_date - pre_system_start_date).days + 1
    
    for i in range(total_days):
        check_date = (pre_system_start_date + timedelta(days=i)).date()
        
        # Jika tanggal ini belum ada di covered_dates, buat transaksi dummy
        if check_date not in covered_dates:
            # Buat 1-3 transaksi untuk hari kosong ini
            num_fill_tx = random.randint(1, 3)
            for _ in range(num_fill_tx):
                # Pilih customer random
                random_cust = random.choice(customers)
                
                # Set jam random di tanggal tersebut
                tx_datetime = datetime.combine(check_date, datetime.min.time()) + timedelta(hours=random.randint(8, 20), minutes=random.randint(0, 59))
                
                transaction = Transaction(
                    customer_id=random_cust.id, user_id=random.choice(user_ids),
                    total_amount=0, created_at=tx_datetime
                )
                
                # Item simple
                item = random.choice(products)
                qty = 1
                price = Decimal(str(item.price))
                total = price * qty
                
                t_item = TransactionItem(product_id=item.id, quantity=qty, price=item.price)
                
                # Cek Promo (Mei+)
                disc = Decimal('0')
                if tx_datetime >= discount_system_start_date:
                     # Simple logic for gap filler: random small discount chance if promo era
                     pass # Biarkan 0 untuk simplicity di gap filler, atau copy logic full jika perlu
                
                transaction.total_amount = total - disc
                transaction.discount_amount = disc
                transaction.items = [t_item]
                transactions.append(transaction)
            
            covered_dates.add(check_date) # Tandai sudah diisi

    db.session.add_all(transactions)
    db.session.commit()
    
    # E. Jalankan K-Means Otomatis
    print("🔍 Menjalankan analisis K-Means & Sorting Segmen...")
    
    from utils.kmeans_service import KMeansService
    kmeans_service = KMeansService(n_clusters=3)
    rfm_df, score = kmeans_service.analyze() # Tangkap score
    
    if score is not None:
        print(f"📊 Silhouette Score (k=3): {score:.4f}")
    
    segment_objects = []
    if rfm_df is not None and not rfm_df.empty:
        
        segment_names = ['VIP', 'Frequent Buyer', 'Occasional Shopper']
        segment_colors = ['#28a745', '#007bff', '#ffc107'] # Green, Blue, Yellow
        
        # Simpan Segmen ke DB
        for i in range(3):
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
        analyzed_ids = rfm_df['customer_id'].tolist()
        new_customers = db.session.query(Customer).filter(Customer.id.notin_(analyzed_ids)).all()
        
        if new_customers:
            new_seg = CustomerSegment(
                segment_name="New Customer", 
                description="Customers who have not yet made any transactions", 
                color="#17a2b8" # Cyan
            )
            db.session.add(new_seg)
            db.session.flush()
            segment_objects.append(new_seg)
            
            new_memberships = [{'customer_id': c.id, 'segment_id': new_seg.id} for c in new_customers]
            db.session.bulk_insert_mappings(CustomerSegmentMembership, new_memberships)

        # F. Buat Promosi Berdasarkan Segmen yang Sudah Terbentuk
        print("🎁 Membuat data promosi otomatis...")
        
        promos = [
            {'name_match': 'VIP', 'type': 'percentage_discount', 'val': 10, 'desc': 'Special 10% Discount for VIP Members'},
            {'name_match': 'Frequent Buyer', 'type': 'percentage_discount', 'val': 5, 'desc': '5% Discount for being a Frequent Buyer'},
            {'name_match': 'Occasional Shopper', 'type': 'fixed_discount', 'val': 2000, 'desc': 'Rp 2,000 Off for your next purchase'},
            {'name_match': 'New Customer', 'type': 'fixed_discount', 'val': 5000, 'desc': 'Welcome Voucher Rp 5,000'}
        ]
        
        for p in promos:
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
    else:
        print("⚠️  Tidak ada data RFM yang dihasilkan, promosi tidak dibuat.")