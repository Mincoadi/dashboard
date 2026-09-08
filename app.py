import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. Konfigurasi Halaman & Koneksi Database SQLite
st.set_page_config(page_title="Portal Garansi", page_icon="📦", layout="wide")

USER_ADMIN = "admin"
PASSWORD_ADMIN = "admin123"

def init_db():
    conn = sqlite3.connect("warranty_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warranties_v4 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT UNIQUE,
            product_name TEXT,
            customer_name TEXT,
            purchase_datetime TEXT,
            duration_months INTEGER,
            status TEXT,
            product_image TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- FUNGSI HITUNG MUNDUR SUPER DETAIL ---
def calculate_precise_warranty(purchase_datetime_str, duration_months):
    try:
        purchase_dt = datetime.strptime(purchase_datetime_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        expiry_dt = purchase_dt + relativedelta(months=duration_months)
        
        if now >= expiry_dt:
            return "🔴 Expired", "Expired"
        
        time_left = expiry_dt - now
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        months = days // 30
        remaining_days = days % 30
        
        if months > 0:
            text = f"{months} Bln {remaining_days} Hari, {hours} Jam {minutes} Mnt {seconds} Dtk"
        elif remaining_days > 0:
            text = f"{remaining_days} Hari, {hours} Jam {minutes} Mnt {seconds} Dtk"
        else:
            text = f"{hours} Jam {minutes} Mnt {seconds} Dtk"
            
        return "🟢 Aktif", text
    except Exception:
        return "🔴 Error", "Data Tidak Valid"

# --- FUNGSI AMBIL, SIMPAN, & HAPUS DATA ---
def get_data():
    conn = sqlite3.connect("warranty_data.db")
    df_raw = pd.read_sql_query("SELECT serial_number, product_name, customer_name, purchase_datetime, duration_months, status, product_image FROM warranties_v4", conn)
    conn.close()
    
    if df_raw.empty:
        return pd.DataFrame()
        
    processed_rows = []
    for _, row in df_raw.iterrows():
        status_auto, remaining_auto = calculate_precise_warranty(row['purchase_datetime'], int(row['duration_months']))
        processed_rows.append({
            "Nomor Serial": row['serial_number'],
            "Nama Produk": row['product_name'],
            "Pelanggan": row['customer_name'],
            "Waktu Beli": row['purchase_datetime'],
            "Durasi Awal": f"{row['duration_months']} Bulan",
            "Sisa Garansi": remaining_auto,
            "Status": status_auto,
            "Foto_Base64": row['product_image']
        })
    return pd.DataFrame(processed_rows)

def insert_data(sn, produk, pelanggan, tgl_beli, jam_beli, durasi):
    try:
        datetime_combined = datetime.combine(tgl_beli, jam_beli).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect("warranty_data.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO warranties_v4 (serial_number, product_name, customer_name, purchase_datetime, duration_months, status, product_image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sn, produk, pelanggan, datetime_combined, int(durasi), "Aktif", ""))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def delete_data(sn):
    conn = sqlite3.connect("warranty_v4")
    conn = sqlite3.connect("warranty_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warranties_v4 WHERE serial_number = ?", (sn,))
    data = cursor.fetchone()
    if data is None:
        conn.close()
        return False
    cursor.execute("DELETE FROM warranties_v4 WHERE serial_number = ?", (sn,))
    conn.commit()
    conn.close()
    return True

# --- SISTEM CEK STATUS LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- TAMPILAN UTAMA DASHBOARD ---
try:
    st.image("15976.jpg", width=150)
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
            st.table(hasil.drop(columns=["Foto_Base64"]))
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
        st.subheader("📝 Input Garansi Baru")
        
        with st.form("form_input", clear_on_submit=True):
            input_sn = st.text_input("Nomor Serial:", placeholder="Contoh: SN-2026-001")
            input_produk = st.text_input("Nama Produk:", placeholder="Contoh: Mobil Mainan")
            input_pelanggan = st.text_input("Nama Pelanggan:", placeholder="Contoh: Pasep")
            input_tgl = st.date_input("Tanggal Pembelian:", value=datetime.today().date())
            input_jam = st.time_input("Jam Pembelian:", value=datetime.today().time())
            input_durasi = st.number_input("Durasi Garansi (Bulan):", min_value=1, max_value=120, value=12)
            
            submit_button = st.form_submit_button("Simpan Data")
            if submit_button:
                if input_sn and input_produk and input_pelanggan:
                    sukses = insert_data(input_sn.strip(), input_produk.strip(), input_pelanggan.strip(), input_tgl, input_jam, input_durasi)
                    if sukses:
                        st.success("🎉 Data berhasil disimpan!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal! Nomor Serial sudah terdaftar.")
                else:
                    st.warning("⚠️ Mohon isi semua kolom yang wajib!")

        st.markdown("---")
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

# TAMPILAN 3: TABEL DATA ADMIN
if st.session_state['logged_in']:
    st.write("### 📋 Semua Data Garansi (Sisi Admin)")
    if not df_garansi.empty:
        st.dataframe(df_garansi.drop(columns=["Foto_Base64"]), use_container_width=True)
        
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
    st.info("ℹ️ Panel data admin dan fitur rekap laporan disembunyikan. Silakan login pada menu sidebar untuk membukanya.")

# --- AUTO REFRESH HALAMAN (Agar detik hitung mundur berjalan live) ---
if cari_sn or st.session_state['logged_in']:
    time.sleep(1)
    st.rerun()
