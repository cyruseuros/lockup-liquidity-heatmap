from typing import List, Type
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import dfply as ply
from dfply import X as x

MARKETBEAT_URL = 'https://www.marketbeat.com/ipos/lockup-expirations/'
lockup_html = requests.get(MARKETBEAT_URL).text

# NOTE: May throw requests.exceptions.RequestException
# TODO: Look into parametrizing this thing to tweak the timeframe
def fetch_html():
    return requests.get(MARKETBEAT_URL).text

def parse_data(html: str) -> List[List[str]]:
    try:
        soup = BeautifulSoup(lockup_html, features='html.parser')
        rows = soup.select('#cphPrimaryContent_pnlFilterTable tbody > tr:not(.bottom-sort)')

        row_data = []
        for row in rows:
            contents = row.contents

            try:
                logo_url = contents[0].find('img')['src']
            # Missing logos
            except TypeError:
                logo_url = None

            _ticker_name = contents[0]['data-clean'].split('|')
            ticker = _ticker_name[0]
            name = _ticker_name[1]

            _price_price_change = contents[1]['data-clean'].split('|')
            price = _price_price_change[0]
            price_change = _price_price_change[1]
            price_initial = contents[4].text
            price_date = contents[6].text

            num_shares = contents[3].text
            offer_size = contents[5].text
            expiration_date = contents[2].text
            row_data.append([
                logo_url, ticker, name,
                price, price_change, price_initial, price_date,
                num_shares, offer_size, expiration_date
            ])

        return row_data

    except Exception as e:
        raise ValueError(f'Something about the contents of {MARKETBEAT_URL} has changed: {e}')

def make_df(data: List[List[str]]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    df.columns = [
        'logo_url', 'ticker', 'name',
        'price', 'price_change', 'initial_price', 'pricing_date',
        'num_shares', 'offer_size', 'expiration_date'
    ]

    df_clean = (
        df >>
        ply.mutate(
            price = x.price.str.replace(',', '').str.slice(start=1).astype(float),
            initial_price = x.initial_price.str.replace(',', '').str.slice(start=1).astype(float),
            offer_size = x.offer_size.str.replace(',', '').str.slice(start=1).astype(float),
            price_change = x.price_change.str.replace(',', '').str.slice(stop=-1).astype(float),
            num_shares = x.num_shares.str.replace(',', '').astype(int),
            expiration_date = x.expiration_date.astype(np.datetime64)
        )
    )

    return df_clean

def get_lockup_data() -> pd.DataFrame:
    html = fetch_html()
    data = parse_data(html)
    df = make_df(data)
    return df