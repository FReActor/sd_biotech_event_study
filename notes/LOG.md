Day 3: 8/26

Done:
- Downloaded all 8-k filings of the companies from 2019-2025.
- Confirmed that the timezone is UTC instead of eastern(the stock market time). And I converted the timezone into Eastern for Consequetiveness purpose
- Extracted the companies that are:
    1. out of the time range(4)(First Tracks, Atrium, BlossomHill, Oncolytics)
    2. are foreign companies which submit 6-k files instead of 8-k(1)(Belite Bio)
    3. in the list, yet only has 6- files from 2019-2025(1)(Connect Biopharma)
  so 67 companies and 4788 files are kept.

Findings:
- What out of my expectation was that I found one company that belongs to the orginal list, yet all of the files from 2019-2025 are 6-k files. As a result I deleted it from the company list, since I decided to delete companies with 6-k filings.
- All of the companies kept now are companies with only 8-k files from 2019-2025

Day2: 8/25

Done:
- Downloaded 7937 SIC files from SEC EDGARD(1 error) with safe funtion and error handling funtion. From all of the data, subtracted those who are based in San Diego(by checking the name of the city) and listed them.
- From all the listed San Diego based companies, manually checked and decided which companies belong to 'life science' by the SIC of the companies. 

Findings:
- San Diego has 132 companies, and 73 of which are life science companies accordnig to my filter. This shows that 55% of the companies in San Diego are life science related, implying that San Diego is a center of life science.
- Realized that multiple companies don't match the SICs they chose -- this is becasue SIC doesn't require verification. Also the definition of life science was , which might cause bias later.


Day1: 8/24

Done:
- Submitted request for WRDS and waiting for approval.(undergraduate might not have access during summer) Emailed UCSD librarian about the access and waiting for reply.
- EDGAR submissions API works.

Findings:
- Illumina's SIC is 3826, which is not my assumed set(2836, 2834, 3841)
- company_tickers.json has 10403 entries, and all of them are currently listed. The delisted firms are absent, which causes survivorship problem.
- Illumina is covered from 2019-01-11 to 2026-08-21, and has 114 8-K. This results in an average 15 8-k per year.

To do:
- Decide the fial SIC code set based on distribution.
- Filter the correct Zip codes that belong to San Diego.