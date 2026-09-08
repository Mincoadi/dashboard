import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. Konfigurasi Halaman & Koneksi Database SQLite
st.set_page_config(page_title="Warranty Dashboard", layout="wide")

# Konfigurasi Password Admin (Silakan ganti kata 'admin123' sesuai keinginan Anda)
PASSWORD_ADMIN = "admin123"

def init_db():
    conn = sqlite3.connect("warranty_data.db")
    cursor = conn.cursor()
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
        purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
        today = datetime.today().date()
        expiry_date = purchase_date + relativedelta(months=duration_months)
        
        if today >= expiry_date:
            return "🔴 Expired", "Expired"
        
        diff = relativedelta(expiry_date, today)
        
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
    df_raw = pd.read_sql_query("SELECT serial_number, product_name, customer_name, purchase_date, duration_months, status FROM warranties_v2", conn)
    conn.close()
    
    if df_raw.empty:
        return pd.DataFrame()
        
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

# --- SISTEM CEK STATUS LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- TAMPILAN UTAMA DASHBOARD ---
st.title("🛡️ Portal Garansi Produk Resmi")
st.caption("Sistem Pelacakan Garansi untuk Pelanggan & Panel Manajemen Admin")
st.markdown("---")

df_garansi = get_data()

# TAMPILAN 1: PUSAT CEK GARANSI (BISA DIAKSES SIAPA SAJA / UMUM)
st.write("### 🔍 Pusat Cek Status Garansi (Pelanggan)")
cari_sn = st.text_input("Masukkan Nomor Serial Produk Anda:", placeholder="Ketik nomor serial di sini...")

if cari_sn:
    if not df_garansi.empty:
        hasil = df_garansi[df_garansi["Nomor Serial"].str.lower() == cari_sn.strip().lower()]
        if not hasil.empty:
            st.success("✨ Data Garansi Ditemukan!")
            st.table(hasil)
        else:
            st.error("❌ Mohon maaf, Nomor Serial tidak terdaftar di sistem kami.")
    else:
        st.error("❌ Belum ada data garansi terdaftar di dalam sistem.")

st.markdown("---")


# TAMPILAN 2: PANEL SIDEBAR & MENU ADMIN (TERKUNCI PASSWORD)
with st.sidebar:
    st.header("🔐 Area Admin")
    
    if not st.session_state['logged_in']:
        # Jika belum login, tampilkan form login
        st.write("Silakan masuk untuk mengakses fitur input dan laporan.")
        input_password = st.text_input("Masukkan Password Admin:", type="password")
        btn_login = st.button("Masuk")
        
        if btn_login:
            if input_password == PASSWORD_ADMIN:
                st.session_state['logged_in'] = True
                st.success("🔓 Login berhasil!")
                st.rerun()
            else:
                st.error("❌ Password salah! Akses ditolak.")
    else:
        # Jika sudah sukses login, tampilkan Form Input Data Baru
        st.write("Anda masuk sebagai **Admin**")
        btn_logout = st.button("Keluar / Logout")
        if btn_logout:
            st.session_state['logged_in'] = False
            st.rerun()
            
        st.markdown("---")
        st.subheader("📝 Input Garansi Baru")
        
        with st.form("form_input", clear_on_submit=True):
            input_sn = st.text_input("Nomor Serial:", placeholder="Contoh: SN-2026-001")
            input_produk = st.text_input("Nama Produk:", placeholder="Contoh: Mobil Mainan")
            input_pelanggan = st.text_input("Nama Pelanggan:", placeholder="Contoh: Pasep")
            input_tgl = st.date_input("Tanggal Pembelian:", value=datetime.today().date())
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


# TAMPILAN 3: TABEL DATA ADMIN (HANYA MUNCUL JIKA SUDAH LOGIN)
if st.session_state['logged_in']:
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
        st.info("Database masih kosong. Silakan tambah data melalui formulir di sidebar kiri.")
else:
    # Pesan penutup untuk pengunjung yang belum login
    st.info("ℹ️ Panel data admin dan fitur rekap laporan disembunyikan. Silakan login pada menu sidebar untuk membukanya.")
