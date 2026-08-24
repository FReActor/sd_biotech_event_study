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