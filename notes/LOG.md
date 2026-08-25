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