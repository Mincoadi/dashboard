import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import streamlit.components.v1 as components
import matplotlib.pyplot as plt

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Portal Garansi", page_icon="📦", layout="wide")

# ==========================================
# 1b. KUSTOMISASI WARNA SIDEBAR (CSS)
# ==========================================
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #d4e6f1;
    }
    [data-testid="stSidebar"] * {
        color: #154360;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {
        color: #0b3d5c;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #2e86c1;
        color: white;
        border: none;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1a5276;
        color: white;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: #ffffff;
        border: 1px solid #a9cce3;
    }
    [data-testid="stSidebar"] .stForm {
        border: 1px solid #a9cce3;
        border-radius: 10px;
        padding: 10px;
        background-color: #ebf5fb;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. KREDENSIAL ADMIN (HARDCODE)
# ==========================================
USER_ADMIN = "admin"
PASSWORD_ADMIN = "admin123"

# ==========================================
# 3. FUNGSI COUNTDOWN (HANYA BULAN & HARI)
# ==========================================
def get_countdown_component(seconds_left, uid, height=50):
    """Menampilkan countdown hanya dalam bulan dan hari (tanpa jam/menit/detik)."""
    if seconds_left <= 0:
        return components.html("<span style='color:red; font-weight:bold;'>🔴 Expired</span>", height=30)

    html_code = f"""
    <div id="countdown_{uid}" style="font-size:16px; font-weight:bold;"></div>
    <script>
    (function() {{
        let remaining = {int(seconds_left)};
        const el = document.getElementById('countdown_{uid}');
        if (!el) return;
        function update() {{
            if (remaining <= 0) {{
                el.innerHTML = '🔴 Expired';
                return;
            }}
            const totalDays = Math.floor(remaining / (24 * 3600));
            const months = Math.floor(totalDays / 30);
            const days = totalDays % 30;
            let text = '';
            if (months > 0) text += months + ' Bln ';
            if (days > 0) text += days + ' Hari ';
            if (text === '') text = '0 Hari';
            el.innerHTML = '🟢 ' + text;
            remaining--;
        }}
        update();
        setInterval(update, 1000);
    }})();
    </script>
    """
    return components.html(html_code, height=height)

# ==========================================
# 4. INISIALISASI DATABASE
# ==========================================
def init_db():
    conn = sqlite3.connect("warranty_data.db")
    c = conn.cursor()
    c.execute("""
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

# ==========================================
# 5. FUNGSI HITUNG SISA (BULAN & HARI)
# ==========================================
def calculate_warranty(purchase_datetime_str, duration_months):
    """
    Mengembalikan tuple: (status_text, sisa_teks_bulan_hari, sisa_detik_total)
    """
    try:
        # Ambil tanggal saja (abaikan jam)
        purchase_date = datetime.strptime(purchase_datetime_str[:10], "%Y-%m-%d").date()
        expiry_date = purchase_date + relativedelta(months=duration_months)
        today = date.today()

        if today > expiry_date:
            return "🔴 Expired", "Expired", 0

        delta = expiry_date - today
        total_days = delta.days
        months = total_days // 30
        days = total_days % 30

        teks = ""
        if months > 0:
            teks += f"{months} Bln "
        if days > 0:
            teks += f"{days} Hari "
        if teks == "":
            teks = "0 Hari"

        expiry_datetime = datetime.combine(expiry_date, datetime.min.time())
        seconds_left = (expiry_datetime - datetime.now()).total_seconds()
        if seconds_left < 0:
            seconds_left = 0

        return "🟢 Aktif", teks.strip(), int(seconds_left)
    except Exception:
        return "🔴 Error", "Data Tidak Valid", 0

# ==========================================
# 6. FUNGSI CRUD DATABASE (DENGAN CACHING)
# ==========================================
@st.cache_data(ttl=5)
def get_data():
    conn = sqlite3.connect("warranty_data.db")
    df_raw = pd.read_sql_query(
        "SELECT serial_number, product_name, customer_name, purchase_datetime, duration_months, status, product_image FROM warranties_v4",
        conn
    )
    conn.close()
    if df_raw.empty:
        return pd.DataFrame()

    processed = []
    for _, row in df_raw.iterrows():
        status_icon, sisa_teks, sisa_detik = calculate_warranty(
            row['purchase_datetime'], int(row['duration_months'])
        )
        processed.append({
            "Nomor Serial": row['serial_number'],
            "Nama Produk": row['product_name'],
            "Pelanggan": row['customer_name'],
            "Waktu Beli": row['purchase_datetime'],
            "Durasi Awal": f"{row['duration_months']} Bulan",
            "Sisa Garansi": sisa_teks,
            "SisaDetik": sisa_detik,
            "Status": status_icon,
            "Foto_Base64": row['product_image']
        })
    return pd.DataFrame(processed)

def clear_cache():
    st.cache_data.clear()

def insert_data(sn, produk, pelanggan, tgl_beli, durasi):
    try:
        datetime_combined = datetime.combine(tgl_beli, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect("warranty_data.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO warranties_v4
            (serial_number, product_name, customer_name, purchase_datetime, duration_months, status, product_image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sn, produk, pelanggan, datetime_combined, int(durasi), "Aktif", ""))
        conn.commit()
        conn.close()
        clear_cache()
        return True
    except sqlite3.IntegrityError:
        return False

def delete_data(sn):
    conn = sqlite3.connect("warranty_data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM warranties_v4 WHERE serial_number = ?", (sn,))
    data = c.fetchone()
    if data is None:
        conn.close()
        return False
    c.execute("DELETE FROM warranties_v4 WHERE serial_number = ?", (sn,))
    conn.commit()
    conn.close()
    clear_cache()
    return True

# ==========================================
# 7. SESSION STATE LOGIN
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ==========================================
# 8. TAMPILAN UTAMA (HEADER: GAMBAR DI ATAS, JUDUL DI BAWAH)
# ==========================================
# Baris pertama: dua gambar bersebelahan
col1, col2 = st.columns([1, 1])
with col1:
    if os.path.exists("images (5).jpg"):
        st.image("images (5).jpg", width=150)
    else:
        st.write("📦")
with col2:
    if os.path.exists("images (3).svg"):
        st.image("images (3).svg", width=150)
    else:
        st.write("📦")

# Baris kedua: judul dan caption (di bawah gambar)
st.title("Portal Garansi Produk Resmi")
st.caption("Sistem Pelacakan Garansi untuk Pelanggan & Panel Manajemen Admin")
st.markdown("---")

df_garansi = get_data()

# -------------------------------------------------------------------------
# AREA PELANGGAN: CEK GARANSI
# -------------------------------------------------------------------------
st.write("### 🔍 Pusat Cek Status Garansi (Pelanggan)")
cari_sn = st.text_input("Masukkan Nomor Serial Produk Anda:", placeholder="Ketik nomor serial di sini...")

if cari_sn:
    if not df_garansi.empty:
        hasil = df_garansi[df_garansi["Nomor Serial"].str.lower() == cari_sn.strip().lower()]
        if not hasil.empty:
            st.success("✨ Data Garansi Ditemukan!")
            for idx, row in hasil.iterrows():
                st.markdown(f"**🔹 Nomor Serial:** {row['Nomor Serial']}")
                st.markdown(f"**📦 Produk:** {row['Nama Produk']}  |  **👤 Pelanggan:** {row['Pelanggan']}")
                st.markdown(f"**Status:** {row['Status']}")
                st.markdown("**⏳ Sisa Garansi:**")
                get_countdown_component(row['SisaDetik'], f"cust_{idx}", height=50)
                st.divider()
        else:
            st.error("❌ Mohon maaf, Nomor Serial tidak terdaftar di sistem kami.")
    else:
        st.error("❌ Belum ada data garansi terdaftar di dalam sistem.")

st.markdown("---")

# -------------------------------------------------------------------------
# SIDEBAR ADMIN
# -------------------------------------------------------------------------
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
            input_durasi = st.number_input("Durasi Garansi (Bulan):", min_value=1, max_value=120, value=12)
            submit_button = st.form_submit_button("Simpan Data")
            if submit_button:
                if input_sn and input_produk and input_pelanggan:
                    sukses = insert_data(input_sn.strip(), input_produk.strip(), input_pelanggan.strip(),
                                         input_tgl, input_durasi)
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
            konfirmasi = st.checkbox("☑️ Saya yakin ingin menghapus data ini secara permanen!")
            submit_hapus = st.form_submit_button("Hapus Permanen")
            if submit_hapus:
                if not konfirmasi:
                    st.warning("⚠️ Centang kotak konfirmasi terlebih dahulu!")
                elif hapus_sn:
                    berhasil_hapus = delete_data(hapus_sn.strip())
                    if berhasil_hapus:
                        st.success(f"🗑️ Data dengan SN '{hapus_sn}' berhasil dihapus!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal! Nomor Serial tidak ditemukan di database.")
                else:
                    st.warning("⚠️ Masukkan Nomor Serial terlebih dahulu!")

# -------------------------------------------------------------------------
# AREA ADMIN: TABEL DATA & GRAFIK (POPOVER)
# -------------------------------------------------------------------------
if st.session_state['logged_in']:
    st.write("### 📋 Semua Data Garansi (Sisi Admin)")
    if not df_garansi.empty:
        df_tampil = df_garansi.drop(columns=["SisaDetik", "Foto_Base64"]).copy()
        df_tampil.insert(0, "No", range(1, len(df_tampil) + 1))
        st.dataframe(df_tampil, use_container_width=True)

        csv_data = df_tampil.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Unduh Semua Data Garansi (CSV/Excel)",
            data=csv_data,
            file_name="laporan_garansi_otomatis.csv",
            mime="text/csv",
            use_container_width=True
        )

        # ==========================================
        # POPOVER 1: MONITORING UNIT WARRANTY
        # ==========================================
        with st.popover("📋 Monitoring Unit Warranty", use_container_width=True):
            st.write("### 📋 Monitoring Unit Warranty")
            st.caption("Jumlah unit garansi per pelanggan")
            
            customer_counts = df_garansi['Pelanggan'].value_counts().reset_index()
            customer_counts.columns = ['Pelanggan', 'Jumlah Unit']
            st.dataframe(customer_counts, use_container_width=True, hide_index=True)
            
            fig, ax = plt.subplots(figsize=(6, 3))
            bars = ax.barh(customer_counts['Pelanggan'], customer_counts['Jumlah Unit'], color='#2e86c1')
            ax.set_xlabel('Jumlah Unit')
            ax.set_ylabel('Pelanggan')
            ax.set_title('Jumlah Unit Garansi per Pelanggan')
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{int(width)}', 
                        va='center', ha='left', fontweight='bold', fontsize=10)
            plt.tight_layout()
            st.pyplot(fig)

        # ==========================================
        # POPOVER 2: STATISTIK GARANSI
        # ==========================================
        with st.popover("📊 Lihat Statistik Garansi", use_container_width=True):
            st.write("### 📊 Statistik Garansi")
            status_counts = df_garansi['Status'].value_counts()
            aktif = status_counts.get('🟢 Aktif', 0)
            expired = status_counts.get('🔴 Expired', 0)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Total Data", len(df_garansi))
            with col2:
                st.metric("🟢 Aktif", aktif)
            with col3:
                st.metric("🔴 Expired", expired)

            fig, ax = plt.subplots(figsize=(6, 4))
            colors = ['#2ecc71' if x == '🟢 Aktif' else '#e74c3c' for x in status_counts.index]
            wedges, texts, autotexts = ax.pie(
                status_counts,
                labels=status_counts.index,
                autopct='%1.1f%%',
                colors=colors,
                startangle=90,
                textprops={'fontsize': 12}
            )
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            ax.axis('equal')
            st.pyplot(fig)

    else:
        st.info("Database masih kosong. Silakan tambah data melalui formulir di sidebar kiri.")
else:
    st.info("ℹ️ Panel data admin dan fitur rekap laporan disembunyikan. Silakan login pada menu sidebar untuk membukanya.")

# -------------------------------------------------------------------------
# FOOTER
# -------------------------------------------------------------------------
st.divider()
st.caption("© 2026 Portal Garansi Resmi. Hak Cipta Dilindungi.")
