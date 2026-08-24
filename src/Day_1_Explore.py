import requests

HEADERS = {'User-Agent': 'Charles Cheng zic065@ucsd.edu'}
url = 'https://www.sec.gov/files/company_tickers.json'
tickers_raw = requests.get(url, headers=HEADERS).json()

ticker_map={}
for record in tickers_raw.values():
    ticker_map[record['ticker']] = record

print('There are', len(ticker_map), 'companies in total.')
print('Sample:', tickers_raw['0'])

ilmn = ticker_map['ILMN']
cik = str(ilmn['cik_str']).zfill(10)
print('\nILMN CIK:', cik)

sub = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers = HEADERS).json()

print('\ncompany name:', sub['name'])
print('SIC:', sub['sic'], sub['sicDescription'])

addr = sub['addresses']['business']
print('City:', addr['city'])
print('State:', addr['stateOrCountry'])
print('Zip code:', addr['zipCode'])

recent = sub['filings']['recent']
forms = recent['form']
dates = recent['filingDate']

count = forms.count('8-K')
print('\nThere are', count, '8-K in recent')
print('Recent covers', min(dates), 'to', max(dates))
print('Filing.files has:', len(sub['filings'].get('files', [])))