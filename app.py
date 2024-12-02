import streamlit as st
import pandas as pd
import requests
import json
import os

# Configuración inicial de la app
st.set_page_config(page_title="Portafolio Cripto", layout="wide")

# Archivo JSON para almacenar datos
DATA_FILE = "data.json"

# Función para cargar datos desde JSON
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    else:
        return {
            "crypto_sectors": {
                "DeFi": ["uniswap", "aave", "curve-dao-token"],
                "NFT": ["decentraland", "the-sandbox", "axie-infinity"],
            },
            "targets": {crypto: 100.0 for crypto in ["uniswap", "aave", "curve-dao-token", "decentraland", "the-sandbox", "axie-infinity"]}
        }

# Función para guardar datos en JSON
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Cargar datos al iniciar
data = load_data()

# Inicializar datos en la sesión
if "crypto_sectors" not in st.session_state:
    st.session_state["crypto_sectors"] = data["crypto_sectors"]
if "targets" not in st.session_state:
    st.session_state["targets"] = data["targets"]

# Función para obtener precios actuales desde CoinGecko
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_SEARCH_URL = "https://api.coingecko.com/api/v3/search"

@st.cache_data(ttl=600)
def fetch_prices(cryptos, currency="usd"):
    params = {"ids": ",".join(cryptos), "vs_currencies": currency}
    response = requests.get(COINGECKO_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener los precios. Intenta más tarde.")
        return {}

@st.cache_data(ttl=600)
def search_coins(query):
    response = requests.get(COINGECKO_SEARCH_URL, params={"query": query})
    if response.status_code == 200:
        return response.json()["coins"]
    else:
        st.error("Error al buscar monedas. Intenta más tarde.")
        return []

# Función para calcular diferencia porcentual
def calculate_difference(current_price, target_price):
    if current_price == 0:  # Evitar divisiones por 0
        return 0
    if current_price < target_price:  # Si falta para alcanzar el target
        return ((target_price - current_price) / current_price) * 100
    else:  # Si el precio ya superó el target
        return -((current_price - target_price) / target_price) * 100

# Sidebar: Añadir sector
st.sidebar.header("Configuración")
new_sector = st.sidebar.text_input("Nuevo Sector")
if st.sidebar.button("Agregar Sector"):
    if new_sector and new_sector not in st.session_state["crypto_sectors"]:
        st.session_state["crypto_sectors"][new_sector] = []
        save_data({"crypto_sectors": st.session_state["crypto_sectors"], "targets": st.session_state["targets"]})
        st.success(f"Sector '{new_sector}' agregado.")

# Sidebar: Buscar y agregar criptomonedas
selected_sector = st.sidebar.selectbox("Selecciona un Sector", list(st.session_state["crypto_sectors"].keys()))
new_crypto_query = st.sidebar.text_input("Buscar Criptomoneda")

if new_crypto_query:
    coins = search_coins(new_crypto_query)
    coin_options = {coin["id"]: f"{coin['name']} ({coin['symbol']})" for coin in coins}
    selected_coin = st.sidebar.selectbox("Resultados de búsqueda", list(coin_options.keys()), format_func=lambda x: coin_options[x])

    if st.sidebar.button("Agregar Criptomoneda"):
        if selected_coin and selected_sector:
            st.session_state["crypto_sectors"][selected_sector].append(selected_coin)
            st.session_state["targets"][selected_coin] = 100.0
            save_data({"crypto_sectors": st.session_state["crypto_sectors"], "targets": st.session_state["targets"]})
            st.success(f"Criptomoneda '{coin_options[selected_coin]}' agregada al sector '{selected_sector}'.")

# Sidebar: Eliminar sector o criptomoneda
st.sidebar.subheader("Eliminar")
sector_to_delete = st.sidebar.selectbox("Eliminar Sector", list(st.session_state["crypto_sectors"].keys()))
if st.sidebar.button("Eliminar Sector"):
    if sector_to_delete:
        del st.session_state["crypto_sectors"][sector_to_delete]
        save_data({"crypto_sectors": st.session_state["crypto_sectors"], "targets": st.session_state["targets"]})
        st.success(f"Sector '{sector_to_delete}' eliminado.")

crypto_to_delete = st.sidebar.selectbox("Eliminar Criptomoneda", [crypto for sector in st.session_state["crypto_sectors"].values() for crypto in sector])
if st.sidebar.button("Eliminar Criptomoneda"):
    for sector, cryptos in st.session_state["crypto_sectors"].items():
        if crypto_to_delete in cryptos:
            cryptos.remove(crypto_to_delete)
            del st.session_state["targets"][crypto_to_delete]
            save_data({"crypto_sectors": st.session_state["crypto_sectors"], "targets": st.session_state["targets"]})
            st.success(f"Criptomoneda '{crypto_to_delete}' eliminada.")
            break

# Sidebar: Seleccionar moneda
selected_currency = st.sidebar.selectbox("Selecciona la moneda", ["usd", "eur", "ars"], index=0)

# Obtener precios actuales
all_cryptos = [crypto for sector in st.session_state["crypto_sectors"].values() for crypto in sector]
crypto_prices = fetch_prices(all_cryptos, selected_currency)

# Tabs
tabs = st.tabs(list(st.session_state["crypto_sectors"].keys()) + ["Todas las Monedas", "Configurar Targets"])

# Mostrar datos por sector
for idx, sector in enumerate(st.session_state["crypto_sectors"].keys()):
    with tabs[idx]:
        st.header(f"Sector: {sector}")

        sector_cryptos = st.session_state["crypto_sectors"][sector]
        data = []

        for crypto in sector_cryptos:
            current_price = crypto_prices.get(crypto, {}).get(selected_currency, 0)
            target_price = st.session_state["targets"].get(crypto, 0)
            difference = calculate_difference(current_price, target_price)
            data.append(
                {
                    "Criptomoneda": crypto.capitalize(),
                    "Precio Actual": f"{current_price:,.2f} {selected_currency.upper()}",
                    "Target": f"{target_price:,.2f} {selected_currency.upper()}",
                    "Diferencia (%)": f"{difference:+.2f}%",
                }
            )

        # Mostrar en formato de zócalos
        df = pd.DataFrame(data)
        for _, row in df.iterrows():
            color = "green" if float(row["Diferencia (%)"][:-1]) >= 0 else "red"
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; background-color: #f9f9f9; border-radius: 5px;">
                    <h4 style="color: black;">{row['Criptomoneda']}</h4>
                    <p style="margin: 0;">Precio Actual: <b>{row['Precio Actual']}</b></p>
                    <p style="margin: 0;">Target: <b>{row['Target']}</b></p>
                    <p style="margin: 0; color: {color};">Diferencia: <b>{row['Diferencia (%)']}</b></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# Tab para configurar targets
with tabs[-1]:
    st.header("Configurar Targets")
    st.markdown("Ajusta los targets para cada criptomoneda.")
    for crypto in all_cryptos:
        current_target = st.session_state["targets"].get(crypto, 0)
        new_target = st.number_input(f"Target para {crypto.capitalize()}", min_value=0.0, value=current_target, step=1.0)
        st.session_state["targets"][crypto] = new_target
    save_data({"crypto_sectors": st.session_state["crypto_sectors"], "targets": st.session_state["targets"]})

