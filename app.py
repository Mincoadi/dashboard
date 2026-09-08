import streamlit as st
import pandas as pd

# 1. Judul Dashboard
st.title("📊 Dashboard Garansi Produk")
st.subheader("Tampilan Sementara (Prototipe)")

# 2. Data Garansi Palsu/Sementara (Mock Data)
data_garansi = {
    "Nomor Serial": ["SN-2026-001", "SN-2026-002", "SN-2026-003"],
    "Nama Produk": ["Laptop ASUS ROG", "iPhone 15 Pro", "Monitor Samsung 24\""],
    "Pelanggan": ["Budi Santoso", "Siti Aminah", "Rian Wijaya"],
    "Sisa Garansi": ["8 Bulan", "Expired", "14 Bulan"],
    "Status": ["Aktif", "Tidak Aktif", "Aktif"]
}

df = pd.DataFrame(data_garansi)

# 3. Kotak Pencarian / Fitur Cek Garansi
st.write("### 🔍 Cek Status Garansi")
cari_sn = st.text_input("Masukkan Nomor Serial Produk:")

if cari_sn:
    hasil = df[df["Nomor Serial"] == cari_sn]
    if not hasil.empty:
        st.success("Data Ditemukan!")
        st.table(hasil)
    else:
        st.error("Nomor Serial tidak terdaftar.")

# 4. Menampilkan Semua Data Garansi
st.write("### 📋 Semua Data Garansi (Sisi Admin)")
st.dataframe(df)
