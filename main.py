import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd

def get_fed_rate():
    url = 'https://markets.newyorkfed.org/read?productCode=50&eventCodes=500&limit=25&startPosition=0&sort=postDt:-1&format=xml'
    response = requests.get(url)
    root = ET.fromstring(response.content)
    
    for rate in root.findall('.//rate'):
        if rate.find('type').text == 'EFFR':
            percent_rate = rate.find('percentRate').text
            return float(percent_rate) / 100
    
    print("Effective Federal Funds Rate (EFFR) not found")
    return None

def get_bond_rate(cnbc_url):
    response = requests.get(cnbc_url)
    if response.status_code != 200:
        print(f"Failed to retrieve data from {cnbc_url}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    rate_element = soup.find('span', class_='QuoteStrip-lastPrice')
    if rate_element:
        try:
            return float(rate_element.text.strip('%'))
        except ValueError:
            print(f"Failed to parse the rate from {cnbc_url}")
            return None
    else:
        print(f"Failed to retrieve bond rate from {cnbc_url}")
        return None

def calculate_ib_fx_fee(usd_amount):
    return max(2, 0.2 * 0.0001 * usd_amount)

def calculate_ib_bond_fee(face_value):
    if face_value <= 1000000:
        return max(0.002 * 0.0001 * face_value, 5)
    else:
        return max(0.0001 * face_value, 5)

def calculate_futu_bond_fee(face_value):
    commission = max(0.0008 * face_value, 2)
    platform_fee = min(max(0.0004 * face_value, 2), 15)
    return commission + platform_fee

def calculate_usd_received(capital_hkd, fx_rate, fx_fee_function=None):
    usd_amount = capital_hkd * fx_rate
    if fx_fee_function:
        fee = fx_fee_function(usd_amount)
        usd_amount -= fee
    return usd_amount

def calculate_ib_money_market_return(principal_usd, fed_rate):
    return principal_usd * (fed_rate - 0.005)

def calculate_futu_money_market_return(principal_usd, annualized_return):
    return principal_usd * (annualized_return / 100)

def calculate_hk_money_market_return(capital_hkd, annualized_return):
    return capital_hkd * (annualized_return / 100)

def main():
    # Default values
    default_capital_hkd = 2000000
    default_ib_fx_rate = 0.128
    default_futu_fx_rate = 0.12785
    default_futu_annualized_return_usd = 4.8491
    default_futu_annualized_return_hkd = 3.8
    default_preferential_rate_hkd = 3.5

    # User inputs
    try:
        capital_hkd = float(input(f"Enter your capital in HKD (default is {default_capital_hkd}): ") or default_capital_hkd)
        ib_fx_rate = float(input(f"Enter the IB FX rate for 1 HKD to USD (default is {default_ib_fx_rate}): ") or default_ib_fx_rate)
        futu_fx_rate = float(input(f"Enter the FUTU FX rate for 1 HKD to USD (default is {default_futu_fx_rate}): ") or default_futu_fx_rate)
        futu_annualized_return_usd = float(input(f"Enter the FUTU annualized return for USD money market fund (default is {default_futu_annualized_return_usd}%): ") or default_futu_annualized_return_usd)
        futu_annualized_return_hkd = float(input(f"Enter the FUTU annualized return for HKD money market fund (default is {default_futu_annualized_return_hkd}%): ") or default_futu_annualized_return_hkd)
        preferential_rate_hkd = float(input(f"Enter the preferential rate in HKD (default is {default_preferential_rate_hkd}%): ") or default_preferential_rate_hkd)
    except ValueError:
        print("Invalid input. Please enter numeric values.")
        return

    # Fetch bond rates
    bond_rate_1y = get_bond_rate('https://www.cnbc.com/quotes/US1Y')
    bond_rate_10y = get_bond_rate('https://www.cnbc.com/quotes/US10Y')
    
    if bond_rate_1y is None or bond_rate_10y is None:
        print("Failed to retrieve bond rates.")
        return
    
    best_bond_rate = max(bond_rate_1y, bond_rate_10y)

    # Scrape the current fed rate
    fed_rate = get_fed_rate()
    if fed_rate is None:
        print("Failed to retrieve the Fed rate.")
        return

    print(f"Best bond rate: {best_bond_rate}%")
    print(f"Current Fed rate: {fed_rate * 100:.2f}%")

    # Calculate USD received for IB
    usd_received_ib = calculate_usd_received(capital_hkd, ib_fx_rate, calculate_ib_fx_fee)
    # Calculate USD received for FUTU (assuming no additional fee)
    usd_received_futu = calculate_usd_received(capital_hkd, futu_fx_rate)

    print(f"USD received with IB: {usd_received_ib:.2f}")
    print(f"USD received with FUTU: {usd_received_futu:.2f}")

    # Calculate money market returns in USD
    ib_money_market_return = calculate_ib_money_market_return(usd_received_ib, fed_rate)
    futu_money_market_return_usd = calculate_futu_money_market_return(usd_received_futu, futu_annualized_return_usd)

    print(f"IB money market return (1 year): {ib_money_market_return:.2f} USD")
    print(f"FUTU money market return (1 year): {futu_money_market_return_usd:.2f} USD")

    # Calculate bond returns in USD
    ib_bond_fee = calculate_ib_bond_fee(usd_received_ib)
    futu_bond_fee = calculate_futu_bond_fee(usd_received_futu)

    ib_bond_return = usd_received_ib * (best_bond_rate / 100) - ib_bond_fee
    futu_bond_return = usd_received_futu * (best_bond_rate / 100) - futu_bond_fee

    print(f"IB bond return (1 year): {ib_bond_return:.2f} USD")
    print(f"FUTU bond return (1 year): {futu_bond_return:.2f} USD")

    # Calculate HK money market fund return in HKD
    futu_money_market_return_hkd = calculate_hk_money_market_return(capital_hkd, futu_annualized_return_hkd)
    print(f"FUTU HK money market return (1 year): {futu_money_market_return_hkd:.2f} HKD")

    # Preferential rate return in HKD
    preferential_return = capital_hkd * (preferential_rate_hkd / 100)
    print(f"Preferential rate return (1 year) in HKD: {preferential_return:.2f} HKD")

    # Compare returns for IB
    if ib_money_market_return > ib_bond_return:
        best_ib_return = ib_money_market_return
        best_ib_option = "Money Market Fund (USD)"
    else:
        best_ib_return = ib_bond_return
        best_ib_option = "Bond (USD)"

    # Compare returns for FUTU in USD
    if futu_money_market_return_usd > futu_bond_return:
        best_futu_return_usd = futu_money_market_return_usd
        best_futu_option_usd = "Money Market Fund (USD)"
    else:
        best_futu_return_usd = futu_bond_return
        best_futu_option_usd = "Bond (USD)"

    # Prepare the results table
    data = {
        "Investment Option": [
            "IB Money Market Fund (USD)", "IB Bond (USD)",
            "FUTU Money Market Fund (USD)", "FUTU Bond (USD)",
            "SCB Preferential Rate (HKD)", "FUTU HK Money Market Fund (HKD)"
        ],
        "USD/HKD Received": [
            usd_received_ib, usd_received_ib, usd_received_futu, usd_received_futu,
            capital_hkd, capital_hkd
        ],
        "Return (USD/HKD)": [
            ib_money_market_return, ib_bond_return,
            futu_money_market_return_usd, futu_bond_return,
            preferential_return, futu_money_market_return_hkd
        ],
        "Total (USD/HKD)": [
            usd_received_ib + ib_money_market_return, usd_received_ib + ib_bond_return,
            usd_received_futu + futu_money_market_return_usd, usd_received_futu + futu_bond_return,
            capital_hkd + preferential_return, capital_hkd + futu_money_market_return_hkd
        ]
    }

    df = pd.DataFrame(data)
    print(df)

    # Compare total returns in USD
    total_ib_return = usd_received_ib + best_ib_return
    total_futu_return_usd = usd_received_futu + best_futu_return_usd
    total_preferential_return = capital_hkd + preferential_return
    total_futu_return_hkd = capital_hkd + futu_money_market_return_hkd

    # Best return in USD and HKD
    best_usd_return = max(total_ib_return, total_futu_return_usd)
    best_hkd_return = max(total_preferential_return, total_futu_return_hkd)

    # Exchange rate where HKD investment is better than USD investment
    exchange_rate_threshold = best_usd_return / best_hkd_return

    # Determine the best method
    if best_usd_return == total_ib_return:
        best_usd_method = f"IB with {best_ib_option}"
    else:
        best_usd_method = f"FUTU with {best_futu_option_usd}"

    if best_hkd_return == total_preferential_return:
        best_hkd_method = "SCB Preferential Rate"
    else:
        best_hkd_method = "FUTU HK Money Market Fund"

    # Ask user for their preferred currency
    preferred_currency = input("Do you prefer the final return in USD or HKD? ").strip().upper()

    if preferred_currency == "USD":
        print(f"Best return in USD: {best_usd_return:.2f} USD ({best_usd_method})")
        if best_usd_return < best_hkd_return * exchange_rate_threshold:
            converted_return = best_hkd_return * exchange_rate_threshold
            print(f"Converted return from HKD: {converted_return:.2f} USD at threshold rate {exchange_rate_threshold:.5f}")
    elif preferred_currency == "HKD":
        print(f"Best return in HKD: {best_hkd_return:.2f} HKD ({best_hkd_method})")
        if best_hkd_return < best_usd_return / exchange_rate_threshold:
            converted_return = best_usd_return / exchange_rate_threshold
            print(f"Converted return from USD: {converted_return:.2f} HKD at threshold rate {exchange_rate_threshold:.5f}")
    else:
        print("Invalid input. Please choose either 'USD' or 'HKD'.")

    # Show cutoff conversion rate
    print(f"The cutoff conversion rate where USD assets have a better return than HKD assets is: {exchange_rate_threshold:.5f}")

    # Compare returns and find the best option
    if total_ib_return > total_futu_return_usd and total_ib_return > total_preferential_return and total_ib_return > total_futu_return_hkd:
        final_result = f"IB offers the better return by investing in {best_ib_option}."
    elif total_futu_return_usd > total_ib_return and total_futu_return_usd > total_preferential_return and total_futu_return_usd > total_futu_return_hkd:
        final_result = f"FUTU offers the better return by investing in {best_futu_option_usd}."
    elif total_futu_return_hkd > total_ib_return and total_futu_return_hkd > total_preferential_return and total_futu_return_hkd > total_futu_return_usd:
        final_result = "FUTU HK Money Market Fund offers the better return."
    else:
        final_result = "SCB Preferential Rate offers the better return."

    print(final_result)

if __name__ == "__main__":
    main()
