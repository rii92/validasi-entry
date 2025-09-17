import streamlit as st
import pandas as pd
import requests

# ===================== KONFIGURASI =====================
API_URL = "https://script.google.com/macros/s/AKfycbw27UeUwh0bYJLMm2-m8XtpwHlWjkcilLvVameK6H2pHivl8eMslPQuN5QUW2NcHmIu/exec?action=read"

# ===================== AMBIL DATA DARI API =====================
@st.cache_data(ttl=600)  # cache 10 menit agar tidak memanggil API terus
def load_data():
    try:
        r = requests.get(API_URL, timeout=20)
        r.raise_for_status()
        payload = r.json()
        if "records" not in payload:
            st.error("Response API tidak memiliki key 'records'.")
            return pd.DataFrame()
        df = pd.DataFrame(payload["records"])
    except Exception as e:
        st.error(f"Gagal mengambil data dari API: {e}")
        return pd.DataFrame()
    return df

df = load_data()

# ===================== BERSIHKAN DATA =====================
if df.empty:
    st.stop()

# Buang baris yang MIN/MAX = "#NULL!"
df = df[(df["MIN_25_rev"] != "#NULL!") & (df["MAX_25_rev"] != "#NULL!")]

# Konversi ke numerik
df["MIN_25_rev"] = pd.to_numeric(df["MIN_25_rev"], errors="coerce")
df["MAX_25_rev"] = pd.to_numeric(df["MAX_25_rev"], errors="coerce")

# Buang baris penting yang NaN
df = df.dropna(subset=["NAMA", "SATUAN", "MIN_25_rev", "MAX_25_rev"])

if df.empty:
    st.error("Tidak ada data komoditas yang valid untuk ditampilkan.")
    st.stop()

# ===================== SESSION STATE =====================
if "selected_item" not in st.session_state:
    st.session_state.selected_item = df["NAMA"].iloc[0]
if "price" not in st.session_state:
    st.session_state.price = None
if "unit_value" not in st.session_state:
    st.session_state.unit_value = None

# ===================== UI LAYOUT =====================
st.title("💹 Validasi Harga & Satuan Komoditas")

st.sidebar.header("🔎 Pilihan Komoditas")
st.session_state.selected_item = st.sidebar.selectbox(
    "Pilih Nama Barang",
    df["NAMA"].unique(),
    index=list(df["NAMA"]).index(st.session_state.selected_item)
)

# Data komoditas terpilih
item_row = df[df["NAMA"] == st.session_state.selected_item].iloc[0]
min_price, max_price = item_row["MIN_25_rev"], item_row["MAX_25_rev"]
valid_unit = item_row["SATUAN"]

st.markdown(
    f"### 🛒 **{st.session_state.selected_item}**  \n"
    f"Rentang Harga/Satuan: **{min_price} – {max_price} Rupiah per {valid_unit}**"
)

# ===================== TAB =====================
tab_price, tab_unit = st.tabs(["💰 Masukkan Harga", "⚖️ Masukkan Satuan"])

# ---- Tab Harga ----
with tab_price:
    st.info("Masukkan harga total, sistem akan merekomendasikan perkiraan jumlah satuan.")
    price = st.number_input(
        "Harga Total (Rupiah)",
        min_value=0.0,
        step=100.0,
        value=st.session_state.price if st.session_state.price else 0.0,
        key="price_input"
    )
    if price > 0:
        st.session_state.price = price
        min_qty = price / max_price if max_price else 0
        max_qty = price / min_price if min_price else 0
        if min_price <= price <= max_price:
            st.success(f"Harga sesuai rentang standar ({min_price} – {max_price} / {valid_unit}).")
        else:
            st.warning("Harga di luar rentang harga per satuan, estimasi jumlah tetap ditampilkan.")
        st.write(
            f"💡 **Rekomendasi Rentang Satuan:** {min_qty:.2f} – {max_qty:.2f} **{valid_unit}** "
            f"untuk harga total Rp{price:,.0f}"
        )

# ---- Tab Satuan ----
with tab_unit:
    st.info("Masukkan jumlah satuan, sistem akan menampilkan rentang harga total.")
    unit_val = st.number_input(
        f"Jumlah {valid_unit}",
        min_value=0.0,
        step=0.1,
        value=st.session_state.unit_value if st.session_state.unit_value else 0.0,
        key="unit_input"
    )
    if unit_val > 0:
        st.session_state.unit_value = unit_val
        min_total = min_price * unit_val
        max_total = max_price * unit_val
        st.write(
            f"💡 **Rentang Harga Total yang Direkomendasikan:** "
            f"Rp{min_total:,.0f} – Rp{max_total:,.0f} "
            f"untuk {unit_val:.2f} {valid_unit}"
        )

# ---- Tombol Reset ----
if st.sidebar.button("🔄 Reset"):
    st.session_state.price = None
    st.session_state.unit_value = None
    st.experimental_rerun()
