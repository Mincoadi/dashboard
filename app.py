import streamlit as st
import pandas as pd
import sqlite3

# 1. Konfigurasi Halaman & Koneksi Database SQLite
st.set_page_config(page_title="Warranty Dashboard", layout="wide")

# Fungsi untuk menghubungkan ke database file (otomatis dibuat jika belum ada)
def init_db():
    conn = sqlite3.connect("warranty_data.db")
    cursor = conn.cursor()
    # Membuat tabel jika belum ada di database
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warranties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT UNIQUE,
            product_name TEXT,
            customer_name TEXT,
            duration TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

# Jalankan inisialisasi database
init_db()

# --- FUNGSI AMBIL & SIMPAN DATA ---
def get_data():
    conn = sqlite3.connect("warranty_data.db")
    df = pd.read_sql_query("SELECT serial_number AS 'Nomor Serial', product_name AS 'Nama Produk', customer_name AS 'Pelanggan', duration AS 'Sisa Garansi', status AS 'Status' FROM warranties", conn)
    conn.close()
    return df

def insert_data(sn, produk, pelanggan, sisa, status):
    try:
        conn = sqlite3.connect("warranty_data.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO warranties (serial_number, product_name, customer_name, duration, status)
            VALUES (?, ?, ?, ?, ?)
        """, (sn, produk, pelanggan, sisa, status))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False # Jika nomor serial sudah ada (karena bersifat unik)

# --- TAMPILAN DASHBOARD ---
st.title("🛡️ Dashboard Garansi Produk")
st.caption("Sistem Manajemen & Pelacakan Status Garansi Produk (Versi Database)")
st.markdown("---")

# Mengambil data terbaru dari database SQLite
df_garansi = get_data()

# 2. RINGKASAN DATA (METRICS)
st.write("### 📈 Ringkasan Garansi")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="📦 Total Produk Terdaftar", value=f"{len(df_garansi)} Unit")
with col2:
    # Menghitung jumlah status aktif secara dinamis
    aktif_count = len(df_garansi[df_garansi["Status"] == "🟢 Aktif"]) if not df_garansi.empty else 0
    st.metric(label="✅ Garansi Aktif", value=f"{aktif_count} Unit")
with col3:
    # Menghitung selain status aktif
    perhatian_count = len(df_garansi[df_garansi["Status"] != "🟢 Aktif"]) if not df_garansi.empty else 0
    st.metric(label="⚠️ Perlu Perhatian", value=f"{perhatian_count} Unit")

st.markdown("---")

# 3. SIDEBAR: FORMULIR INPUT DATA (KHUSUS ADMIN)
with st.sidebar:
    st.header("📝 Input Garansi Baru")
    st.write("Gunakan formulir ini untuk menambah data ke database.")
    
    # Komponen Formulir
    with st.form("form_input", clear_on_submit=True):
        input_sn = st.text_input("Nomor Serial:", placeholder="Contoh: SN-2026-001")
        input_produk = st.text_input("Nama Produk:", placeholder="Contoh: Asus ROG")
        input_pelanggan = st.text_input("Nama Pelanggan:", placeholder="Contoh: Budi")
        input_sisa = st.text_input("Sisa Garansi:", placeholder="Contoh: 12 Bulan")
        input_status = st.selectbox("Status Garansi:", ["🟢 Aktif", "🔴 Tidak Aktif", "🟡 Klaim Proses"])
        
        submit_button = st.form_submit_button("Simpan Data")
        
        if submit_button:
            if input_sn and input_produk and input_pelanggan:
                sukses = insert_data(input_sn.strip(), input_produk.strip(), input_pelanggan.strip(), input_sisa.strip(), input_status)
                if sukses:
                    st.success("🎉 Data berhasil disimpan!")
                    # Memicu pembaruan halaman agar data langsung muncul di tabel bawah
                    st.rerun()
                else:
                    st.error("❌ Gagal! Nomor Serial sudah terdaftar.")
            else:
                st.warning("⚠️ Mohon isi semua kolom yang wajib!")

# 4. PUSAT CEK GARANSI (UNTUK KONSUMEN)
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
else:
    st.info("Database masih kosong. Silakan tambah data melalui formulir di sebelah kiri (Sidebar).")
