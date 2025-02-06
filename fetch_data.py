import requests
import pandas as pd

def fetch_historical_data(crypto_symbol: str, data_limit: int) -> dict:
    api_url = f"https://min-api.cryptocompare.com/data/v2/histoday"
    request_params = {
        'fsym': crypto_symbol,
        'tsym': 'USD',
        'limit': data_limit,
    }
    try:
        response = requests.get(api_url, params=request_params)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        response_data = response.json()
        if 'Data' in response_data and 'Data' in response_data['Data']:
            return response_data
        else:
            raise ValueError("Unexpected response format")
    except requests.RequestException as e:
        print(f"Error fetching historical data: {e}")
        return {}

def get_usd_to_mad_conversion_rate(api_key: str) -> float:
    url= f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
    response = requests.get(url)
    data = response.json()
    return data['usd']['mad']

def convert_usd_to_cny(usd_amount: float, conversion_rate: float) -> float:
    return usd_amount * conversion_rate

crypto_compare_api_key = 'f10e3a32c45c0c9d37086e05818794ce285b1e0862fcb99856cb666b2338531a'
crypto_symbol = 'BTC'
data_limit = 100  # Number of days of data to fetch

historical_data = fetch_historical_data(crypto_compare_api_key, crypto_symbol, data_limit)

if historical_data:
    # Convert the closing prices from USD to CNY
    for day_data in historical_data['Data']['Data']:
        day_data['close_cny'] = convert_usd_to_cny(day_data['close'], get_usd_to_cny_conversion_rate())

    # Print the converted data
    print(historical_data)
else:
    print("Failed to fetch or convert data.")
