from io import BytesIO
import requests
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from cache_app import load_cache, save_cache
from pycoingecko import CoinGeckoAPI
import streamlit as st
from crypto_symbols import symbol_to_id
import altair as alt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

cg = CoinGeckoAPI()

EXCHANGE_RATE_API_KEY = '086bd38a4414f9e8baecd7e7'
CURRENCY = 'USD'
LIMIT = 365  # Number of days of data to fetch

def fetch_historical_data(crypto_symbol, crypto_currency, data_limit):
    cached_data = load_cache()
    if cached_data is not None:
        return pd.DataFrame(cached_data['Data']['Data'])
    api_url = f"https://min-api.cryptocompare.com/data/v2/histoday"
    request_params = {
        'fsym': crypto_symbol,
        'tsym': crypto_currency,
        'limit': data_limit,
    }
    response = requests.get(api_url, params=request_params)
    response_data = response.json()
    save_cache(response_data)
    return pd.DataFrame(response_data['Data']['Data'])

def get_usd_to_cny_conversion_rate(api_key: str) -> float:
    url= f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
    response = requests.get(url)
    data = response.json()
    return data['usd']['cny']

def convert_usd_to_cny(usd_amount: float, conversion_rate: float) -> float:
    return usd_amount * conversion_rate

def predict_prices(df, days_to_predict):
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df['close'] = df['close'].astype(float)

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df[['close']])

    X = []
    y = []
    for i in range(60, len(scaled_data)):
        X.append(scaled_data[i-60:i, 0])
        y.append(scaled_data[i, 0])

    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))

    model = LinearRegression()
    model.fit(X.reshape(X.shape[0], X.shape[1]), y)

    predictions = []
    last_60_days = scaled_data[-60:]
    for _ in range(days_to_predict):
        pred = model.predict(last_60_days.reshape(1, -1))
        predictions.append(pred[0])
        last_60_days = np.append(last_60_days[1:], pred[0]).reshape(-1, 1)

    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
    return predictions

# Streamlit app
st.set_page_config(page_title="Cryptocurrency Price Prediction", page_icon="📈", initial_sidebar_state='collapsed')

# Sidebar Developer Info
st.sidebar.title("Developer Info")
st.sidebar.info("""
**Developer:** Chen Feng

**Location:** Dandong, China

**email** vijaiaaravindh.v10@gmail.com

This app is built with ❤️ using **Streamlit**.
""")

st.title('📈 Cryptocurrency Price Prediction App')
st.markdown("""
Welcome to the Cryptocurrency Price Prediction App! 🎉
Here you can:
- Check current prices of cryptocurrencies in both USD and CNY.
- Visualize historical price trends.
- Predict future prices for up to 365 days.
""")

# Add a currency selector
currency = st.selectbox('Select Currency', options=['USD', 'CNY'], index=0)

# User input for cryptocurrency symbol
crypto_symbol = st.text_input('Enter the cryptocurrency symbol (e.g., BTC, ETH):', 'BTC')

# Separate input for the number of historical days
historical_days = st.number_input(
    'Select the number of past days for historical data:', min_value=30, max_value=365, value=365, step=10
)

# User input for number of days to predict
days_to_predict = st.number_input('Enter the number of days to predict:', min_value=1, max_value=365, value=30)

# Convert the entered symbol to its corresponding CoinGecko ID
crypto_id = symbol_to_id.get(crypto_symbol.lower())

if crypto_id is None:
    st.error(f"Unsupported cryptocurrency symbol: {crypto_symbol.upper()}")
else:
    try:
        # Fetch the current price of the cryptocurrency
        response = cg.get_price(ids=crypto_id, vs_currencies='usd')
        
        if crypto_id in response:
            current_price_usd = response[crypto_id]['usd']

            # Fetch the conversion rate from USD to CNY
            conversion_rate = get_usd_to_cny_conversion_rate(EXCHANGE_RATE_API_KEY)

            # Convert the current price to CNY
            current_price_cny = convert_usd_to_cny(current_price_usd, conversion_rate)

            st.markdown(f"### Current {crypto_symbol.upper()} Prices")
            st.write(f"💰 **Price in USD**: ${current_price_usd:.2f}")
            st.write(f"💵 **Price in CNY**: {current_price_cny:.2f} yuan")

        # Fetch historical data for the specified number of days
        historical_data = fetch_historical_data(crypto_symbol.upper(), CURRENCY, LIMIT)
        historical_data = historical_data.iloc[-historical_days:]

        # Add columns for "Day" and "Price (CNY)" to historical data
        historical_data['Day'] = range(1, len(historical_data) + 1)
        historical_data['Price (CNY)'] = historical_data['close'].apply(
            lambda price: convert_usd_to_cny(price, conversion_rate)
        )

        # Create a DataFrame for historical prices
        historical_df = historical_data[['Day', 'close', 'Price (CNY)']].rename(columns={'close': 'Price (USD)'})

        # historical_df  
        # Display historical prices DataFrame
        st.markdown(f"### Historical Prices ({currency})")
        st.dataframe(historical_df[['Day', f'Price ({currency})']])

        # Plot historical prices using Altair
        st.markdown(f"### Historical Price Trend ({currency})")
        historical_chart = (
            alt.Chart(historical_df)
            .mark_line()
            .encode(
                x='Day:Q',
                y=alt.Y(f'Price ({currency}):Q', title=f'Price ({currency})'),
                tooltip=['Day', 'Price (USD)', 'Price (CNY)']
            )
            .properties(width=700, height=400)
            .interactive()
        )
        st.altair_chart(historical_chart)

        # Predict prices for the next specified number of days
        predicted_prices = predict_prices(historical_data, days_to_predict)

        # Create columns for "Predicted Price (USD)" and "Predicted Price (CNY)"
        predicted_prices_usd = [price[0] for price in predicted_prices]
        predicted_prices_cny = [convert_usd_to_cny(price, conversion_rate) for price in predicted_prices_usd]

        # Create a DataFrame for predicted prices
        predicted_df = pd.DataFrame({
            'Day': range(1, days_to_predict + 1),
            'Predicted Price (USD)': predicted_prices_usd,
            'Predicted Price (CNY)': predicted_prices_cny
        })

        # Display predicted prices DataFrame
        st.markdown(f"### Predicted {crypto_symbol.upper()} Prices for the Next {days_to_predict} Days ({currency})")
        st.dataframe(predicted_df[['Day', f'Predicted Price ({currency})']])

        # Plot predicted prices using Altair
        st.markdown(f"### Predicted Price Trend ({currency})")
        predicted_chart = (
            alt.Chart(predicted_df)
            .mark_line()
            .encode(
                x='Day:Q',
                y=alt.Y(f'Predicted Price ({currency}):Q', title=f'Predicted Price ({currency})'),
                tooltip=['Day', 'Predicted Price (USD)', 'Predicted Price (CNY)']
            )
            .properties(width=700, height=400)
            .interactive()
        )
        st.altair_chart(predicted_chart)

        # Add summary statistics for historical prices
        st.markdown(f"### Historical Price Statistics ({currency})")
        st.write(f"Mean Price ({currency}): {historical_df[f'Price ({currency})'].mean():.2f}")
        st.write(f"Median Price ({currency}): {historical_df[f'Price ({currency})'].median():.2f}")
        st.write(f"Max Price ({currency}): {historical_df[f'Price ({currency})'].max():.2f}")
        st.write(f"Min Price ({currency}): {historical_df[f'Price ({currency})'].min():.2f}")

        # Add a button to export data as CSV
        if st.button('Export Data as CSV'):
            combined_df = pd.concat([historical_df, predicted_df], keys=['Historical', 'Predicted'])
            csv_data = combined_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="crypto_prices.csv",
                mime="text/csv"
            )
            st.success('Data exported successfully! File saved as crypto_prices.csv')

        elif st.button('Export Data as PDF'):
            combined_df = pd.concat([historical_df, predicted_df], keys=['Historical', 'Predicted'])
            table_data = [combined_df.columns.tolist()] + combined_df.values.tolist()
            pdf_buffer = BytesIO()
            pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            pdf.build([table])
            # Provide a download button for PDF
            pdf_buffer.seek(0)
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="crypto_prices.pdf",
                mime="application/pdf"
    )
            st.success('Data exported successfully! File saved as crypto_prices.pdf')


    except Exception as e:
        st.error(f"An error occurred: {e}")