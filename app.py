import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt  # Fitur baru untuk membuat grafik
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. Konfigurasi Halaman & Koneksi Database SQLite
st.set_page_config(page_title="Warranty Dashboard", layout="wide")

# --- KONFIGURASI KREDENSIAL ADMIN ---
USER_ADMIN = "admin"
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

# --- FUNGSI AMBIL, SIMPAN, & HAPUS DATA ---
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

def delete_data(sn):
    conn = sqlite3.connect("warranty_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warranties_v2 WHERE serial_number = ?", (sn,))
    data = cursor.fetchone()
    if data is None:
        conn.close()
        return False
    cursor.execute("DELETE FROM warranties_v2 WHERE serial_number = ?", (sn,))
    conn.commit()
    conn.close()
    return True

# --- SISTEM CEK STATUS LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- TAMPILAN UTAMA DASHBOARD ---
# Memanggil file gambar yang sudah ada di dalam folder GitHub Anda secara lokal
NAMA_FILE_LOGO = "15976.jpg"

try:
    # Menampilkan foto logo dari folder dengan lebar 150 pixel
    st.image(NAMA_FILE_LOGO, width=150)
except Exception:
    pass

st.title("Portal Garansi Produk Resmi")
st.caption("Sistem Pelacakan Garansi untuk Pelanggan & Panel Manajemen Admin")
st.markdown("---")

df_garansi = get_data()

# TAMPILAN 1: PUSAT CEK GARANSI (UMUM)
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


# TAMPILAN 2: PANEL SIDEBAR & MENU ADMIN
with st.sidebar:
    st.header("🔐 Area Admin")
    
    if not st.session_state['logged_in']:
        st.write("Silakan masuk untuk mengakses fitur admin.")
        input_username = st.text_input("Username Admin:", placeholder="Masukkan username...")
        input_password = st.text_input("Password Admin:", type="password", placeholder="Masukkan password...")
        btn_login = st.button("Masuk")
        
        if btn_login:
            if input_username == USER_ADMIN and input_password == PASSWORD_ADMIN:
                st.session_state['logged_in'] = True
                st.success("🔓 Login berhasil!")
                st.rerun()
            else:
                st.error("❌ Username atau Password salah! Akses ditolak.")
    else:
        st.write(f"Anda masuk sebagai **{USER_ADMIN}**")
        btn_logout = st.button("Keluar / Logout")
        if btn_logout:
            st.session_state['logged_in'] = False
            st.rerun()
            
        st.markdown("---")
        
        # FORMULIR 1: INPUT GARANSI BARU
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

        st.markdown("---")
        
        # FORMULIR 2: HAPUS DATA GARANSI
        st.subheader("🗑️ Hapus Data Garansi")
        with st.form("form_hapus", clear_on_submit=True):
            hapus_sn = st.text_input("Nomor Serial yang Ingin Dihapus:", placeholder="Masukkan nomor serial...")
            submit_hapus = st.form_submit_button("Hapus Permanen Data")
            if submit_hapus:
                if hapus_sn:
                    berhasil_hapus = delete_data(hapus_sn.strip())
                    if berhasil_hapus:
                        st.success(f"🗑️ Data dengan SN '{hapus_sn}' berhasil dihapus!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal! Nomor Serial tidak ditemukan di database.")
                else:
                    st.warning("⚠️ Masukkan Nomor Serial terlebih dahulu!")


# TAMPILAN 3: MANAJEMEN DATA & STATISTIK (HANYA MUNCUL JIKA SUDAH LOGIN)
if st.session_state['logged_in']:
    # Hitung metrik data secara dinamis
    total_produk = len(df_garansi)
    aktif_count = len(df_garansi[df_garansi["Status"] == "🟢 Aktif"]) if not df_garansi.empty else 0
    expired_count = len(df_garansi[df_garansi["Status"] == "🔴 Expired"]) if not df_garansi.empty else 0

    # PEMBAGIAN LAYAR: Kiri untuk Tabel, Kanan untuk Grafik
    col_tabel, col_grafik = st.columns([2, 1])

    with col_tabel:
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

    with col_grafik:
        st.write("### 📊 Statistik Status")
        if not df_garansi.empty and (aktif_count > 0 or expired_count > 0):
            # --- PROSES MEMBUAT GRAFIK PIE CHART ---
            labels = ['Aktif', 'Expired']
            sizes = [aktif_count, expired_count]
            colors = ['#2ecc71', '#e74c3c'] # Hijau untuk Aktif, Merah untuk Expired
            
            fig, ax = plt.subplots(figsize=(4, 4))
            # Membuat Pie Chart dengan persentase otomatis
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, 
                   textprops={'fontsize': 10, 'weight': 'bold'})
            ax.axis('equal')  # Memastikan lingkaran berbentuk bulat sempurna
            
            # Memunculkan grafik ke layar website
            st.pyplot(fig)
        else:
            st.info("Grafik baru akan muncul setelah Anda menginput data garansi.")
else:
    st.info("ℹ️ Panel data admin dan fitur rekap laporan disembunyikan. Silakan login pada menu sidebar untuk membukanya.")
