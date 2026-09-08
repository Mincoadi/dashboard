import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
import streamlit.components.v1 as components
import matplotlib.pyplot as plt

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Portal Garansi", page_icon="📦", layout="wide")

# ==========================================
# 2. FUNGSI COUNTDOWN KOMPONEN (JavaScript)
# ==========================================
def get_countdown_component(expiry_dt_str, uid, height=50):
    """Mengembalikan komponen HTML/JS countdown real-time dengan ID unik."""
    if not expiry_dt_str:
        return components.html("<span>❌ Tidak valid</span>", height=30)
    html_code = f"""
    <div id="countdown_{uid}" style="font-size:16px; font-weight:bold;"></div>
    <script>
    (function() {{
        const target = new Date("{expiry_dt_str}").getTime();
        const el = document.getElementById('countdown_{uid}');
        if (!el) return;
        function update() {{
            const now = new Date().getTime();
            const diff = target - now;
            if (diff <= 0) {{
                el.innerHTML = '🔴 Expired';
                return;
            }}
            const months = Math.floor(diff / (1000 * 60 * 60 * 24 * 30));
            const days = Math.floor((diff % (1000 * 60 * 60 * 24 * 30)) / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            let text = '';
            if (months > 0) text += months + ' Bln ';
            if (days > 0) text += days + ' Hari ';
            text += hours + ' Jam ' + minutes + ' Mnt ' + seconds + ' Dtk';
            el.innerHTML = '🟢 ' + text;
        }}
        update();
        setInterval(update, 1000);
    }})();
    </script>
    """
    return components.html(html_code, height=height)

# ==========================================
# 3. INISIALISASI DATABASE
# ==========================================
# Ambil kredensial dari secrets (harus buat file .streamlit/secrets.toml)
try:
    USER_ADMIN = st.secrets["USER_ADMIN"]
    PASSWORD_ADMIN = st.secrets["PASSWORD_ADMIN"]
except Exception:
    # Fallback sementara (jangan dipakai di produksi)
    USER_ADMIN = "admin"
    PASSWORD_ADMIN = "admin123"
    st.warning("⚠️ Gunakan st.secrets untuk keamanan! Buat file .streamlit/secrets.toml")

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
# 4. FUNGSI HITUNG SISA GARANSI
# ==========================================
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

# ==========================================
# 5. FUNGSI DATABASE (DENGAN CACHING)
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
        status_auto, remaining_auto = calculate_precise_warranty(
            row['purchase_datetime'], int(row['duration_months'])
        )
        processed.append({
            "Nomor Serial": row['serial_number'],
            "Nama Produk": row['product_name'],
            "Pelanggan": row['customer_name'],
            "Waktu Beli": row['purchase_datetime'],
            "Durasi Awal": f"{row['duration_months']} Bulan",
            "DurasiBulan": row['duration_months'],
            "Sisa Garansi": remaining_auto,
            "Status": status_auto,
            "Foto_Base64": row['product_image']
        })
    return pd.DataFrame(processed)

def clear_cache():
    st.cache_data.clear()

def insert_data(sn, produk, pelanggan, tgl_beli, jam_beli, durasi):
    try:
        datetime_combined = datetime.combine(tgl_beli, jam_beli).strftime("%Y-%m-%d %H:%M:%S")
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
# 6. SESSION STATE LOGIN
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ==========================================
# 7. TAMPILAN UTAMA
# ==========================================
try:
    st.image("images (5).jpg", width=200)
except Exception:
    pass

st.title("Portal Garansi Produk Resmi")
st.caption("Sistem Pelacakan Garansi untuk Pelanggan & Panel Manajemen Admin")
st.markdown("---")

df_garansi = get_data()

# --- PUSAT CEK GARANSI (PELANGGAN) ---
st.write("### 🔍 Pusat Cek Status Garansi (Pelanggan)")
cari_sn = st.text_input("Masukkan Nomor Serial Produk Anda:", placeholder="Ketik nomor serial di sini...")

if cari_sn:
    if not df_garansi.empty:
        hasil = df_garansi[df_garansi["Nomor Serial"].str.lower() == cari_sn.strip().lower()]
        if not hasil.empty:
            st.success("✨ Data Garansi Ditemukan!")
            for idx, row in hasil.iterrows():
                purchase_dt = datetime.strptime(row['Waktu Beli'], "%Y-%m-%d %H:%M:%S")
                durasi_bulan = int(row['DurasiBulan'])
                expiry_dt = purchase_dt + relativedelta(months=durasi_bulan)
                expiry_time_str = expiry_dt.isoformat()

                st.markdown(f"**🔹 Nomor Serial:** {row['Nomor Serial']}")
                st.markdown(f"**📦 Produk:** {row['Nama Produk']}  |  **👤 Pelanggan:** {row['Pelanggan']}")
                st.markdown(f"**Status:** {row['Status']}")
                # ===== TAMBAHAN: TAMPILKAN SISA GARANSI DI SISI PELANGGAN =====
                st.markdown(f"**⏳ Sisa Garansi:** {row['Sisa Garansi']}")
                # ==============================================================
                get_countdown_component(expiry_time_str, idx, height=50)
                st.divider()
        else:
            st.error("❌ Mohon maaf, Nomor Serial tidak terdaftar di sistem kami.")
    else:
        st.error("❌ Belum ada data garansi terdaftar di dalam sistem.")

st.markdown("---")

# --- PANEL SIDEBAR ADMIN ---
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
                st.toast("🔓 Login berhasil!", icon="✅")
                st.rerun()
            else:
                st.error("❌ Username atau Password salah! Akses ditolak.")
    else:
        st.write(f"Anda masuk sebagai **{USER_ADMIN}**")
        btn_logout = st.button("Keluar / Logout")
        if btn_logout:
            st.session_state['logged_in'] = False
            st.toast("🔒 Logout berhasil!", icon="👋")
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
                    sukses = insert_data(input_sn.strip(), input_produk.strip(), input_pelanggan.strip(),
                                         input_tgl, input_jam, input_durasi)
                    if sukses:
                        st.toast("🎉 Data berhasil disimpan!", icon="✅")
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
                        st.toast(f"🗑️ Data dengan SN '{hapus_sn}' berhasil dihapus!", icon="🗑️")
                        st.rerun()
                    else:
                        st.error("❌ Gagal! Nomor Serial tidak ditemukan di database.")
                else:
                    st.warning("⚠️ Masukkan Nomor Serial terlebih dahulu!")

# --- TABEL DATA ADMIN (HANYA TERLIHAT SAAT LOGIN) ---
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
        
        # ===== TAMBAHAN GRAFIK STATISTIK =====
        st.write("### 📊 Statistik Garansi")
        status_counts = df_garansi['Status'].value_counts()
        if not status_counts.empty:
            fig, ax = plt.subplots(figsize=(6, 4))
            colors = ['#2ecc71' if x == '🟢 Aktif' else '#e74c3c' for x in status_counts.index]
            ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', colors=colors, startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        # ====================================
    else:
        st.info("Database masih kosong. Silakan tambah data melalui formulir di sidebar kiri.")
else:
    st.info("ℹ️ Panel data admin dan fitur rekap laporan disembunyikan. Silakan login pada menu sidebar untuk membukanya.")

# ==========================================
# 8. FOOTER
# ==========================================
st.divider()
st.caption("© 2026 Portal Garansi Resmi. Hak Cipta Dilindungi.")

# ==========================================
# 9. TIDAK ADA AUTO-REFRESH DI SINI!
# ==========================================
