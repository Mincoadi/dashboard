import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. Konfigurasi Halaman & Koneksi Database SQLite
st.set_page_config(page_title="Warranty Dashboard", layout="wide")

def init_db():
    conn = sqlite3.connect("warranty_data.db")
    cursor = conn.cursor()
    # Menggunakan purchase_date dan duration_months untuk perhitungan otomatis
   cursor.execute("""
    CREATE TABLE IF NOT EXISTS warranties_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT UNIQUE,
            product_name TEXT,
            customer_name TEXT,
            purchase_date TEXT,
            duration_months INTEGER,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- FUNGSI HITUNG MUNDUR GARANSI ---
def calculate_remaining_warranty(purchase_date_str, duration_months):
    try:
        # Mengubah teks tanggal dari database menjadi objek tanggal asli
        purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
        today = datetime.today().date()
        
        # Menghitung tanggal kedaluwarsa (Tanggal beli + durasi bulan)
        expiry_date = purchase_date + relativedelta(months=duration_months)
        
        if today >= expiry_date:
            return "🔴 Expired", "Expired"
        
        # Menghitung selisih waktu dari hari ini ke tanggal expired
        diff = relativedelta(expiry_date, today)
        
        # Format tulisan sisa waktu
        if diff.years > 0:
            remaining_text = f"{diff.years} Tahun {diff.months} Bulan"
        elif diff.months > 0:
            remaining_text = f"{diff.months} Bulan {diff.days} Hari"
        else:
            remaining_text = f"{diff.days} Hari"
            
        return "🟢 Aktif", remaining_text
    except Exception as e:
        return "🔴 Error", "Data Tidak Valid"

# --- FUNGSI AMBIL & SIMPAN DATA ---
def get_data():
    conn = sqlite3.connect("warranty_data.db")
    # Ambil data mentah dari database
    df_raw = pd.read_sql_query("SELECT serial_number, product_name, customer_name, purchase_date, duration_months, status FROM warranties_v2", conn)
    
    if df_raw.empty:
        return pd.DataFrame()
        
    # Proses hitung mundur otomatis untuk setiap baris data
    processed_rows = []
    for _, row in df_raw.iterrows():
        status_auto, remaining_auto = calculate_remaining_warranty(row['purchase_date'], int(row['duration_months']))
        
        processed_rows.append({
            "Nomor Serial": row['serial_number'],
            "Nama Produk": row['product_name'],
            "Pelanggan": row['customer_name'],
            "Tanggal Beli": row['purchase_date'],
            "Durasi Awal": f"{row['duration_months']} Bulan",
            "Sisa Garansi": remaining_auto,
            "Status": status_auto
        })
        
    return pd.DataFrame(processed_rows)

def insert_data(sn, produk, pelanggan, tgl_beli, durasi):
    try:
        conn = sqlite3.connect("warranty_data.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO warranties_v2 (serial_number, product_name, customer_name, purchase_date, duration_months, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sn, produk, pelanggan, str(tgl_beli), int(durasi), "Aktif"))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# --- TAMPILAN DASHBOARD ---
st.title("🛡️ Dashboard Garansi Produk (Hitung Mundur Otomatis)")
st.caption("Sistem secara otomatis memperbarui sisa waktu garansi setiap hari.")
st.markdown("---")

df_garansi = get_data()

# 2. RINGKASAN DATA (METRICS)
st.write("### 📈 Ringkasan Garansi")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="📦 Total Produk Terdaftar", value=f"{len(df_garansi)} Unit")
with col2:
    aktif_count = len(df_garansi[df_garansi["Status"] == "🟢 Aktif"]) if not df_garansi.empty else 0
    st.metric(label="✅ Garansi Aktif", value=f"{aktif_count} Unit")
with col3:
    expired_count = len(df_garansi[df_garansi["Status"] == "🔴 Expired"]) if not df_garansi.empty else 0
    st.metric(label="⚠️ Garansi Expired", value=f"{expired_count} Unit")

st.markdown("---")

# 3. SIDEBAR: FORMULIR INPUT DATA BARU
with st.sidebar:
    st.header("📝 Input Garansi Baru")
    
    with st.form("form_input", clear_on_submit=True):
        input_sn = st.text_input("Nomor Serial:", placeholder="Contoh: SN-2026-001")
        input_produk = st.text_input("Nama Produk:", placeholder="Contoh: Mobil Mainan")
        input_pelanggan = st.text_input("Nama Pelanggan:", placeholder="Contoh: Pasep")
        
        # Fitur Baru: Kalender untuk memilih tanggal pembelian
        input_tgl = st.date_input("Tanggal Pembelian:", value=datetime.today().date())
        # Fitur Baru: Pilihan angka durasi bulan
        input_durasi = st.number_input("Durasi Garansi (Bulan):", min_value=1, max_value=120, value=12)
        
        submit_button = st.form_submit_button("Simpan Data")
        
        if submit_button:
            if input_sn and input_produk and input_pelanggan:
                sukses = insert_data(input_sn.strip(), input_produk.strip(), input_pelanggan.strip(), input_tgl, input_durasi)
                if sukses:
                    st.success("🎉 Data berhasil disimpan!")
                    st.rerun()
                else:
                    st.error("❌ Gagal! Nomor Serial sudah terdaftar.")
            else:
                st.warning("⚠️ Mohon isi semua kolom yang wajib!")

# 4. PUSAT CEK GARANSI
st.write("### 🔍 Pusat Cek Garansi")
cari_sn = st.text_input("Masukkan Nomor Serial Produk untuk Melacak:", placeholder="Ketik nomor serial di sini...")

if cari_sn:
    if not df_garansi.empty:
        hasil = df_garansi[df_garansi["Nomor Serial"].str.lower() == cari_sn.strip().lower()]
        if not hasil.empty:
            st.success("✨ Data Ditemukan!")
            st.table(hasil)
        else:
            st.error("❌ Nomor Serial tidak terdaftar di dalam sistem.")
    else:
        st.error("❌ Belum ada data di dalam database.")

st.markdown("---")

# 5. TABEL SEMUA DATA (SISI ADMIN)
st.write("### 📋 Semua Data Garansi (Sisi Admin)")
if not df_garansi.empty:
    st.dataframe(df_garansi, use_container_width=True)
    
    csv_data = df_garansi.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Unduh Semua Data Garansi (CSV/Excel)",
        data=csv_data,
        file_name="laporan_garansi_otomatis.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("Database masih kosong. Silakan tambah data melalui formulir di sebelah kiri (Sidebar).")
