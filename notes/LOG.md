Day 8: 8/31

Done:
- Set up the timezone of the events. I parsed them at UTC first and then converted to New York time
- Aligned all filings to trading days, estimated the market model per event, computed AR and CAR over four windows
- Produced diagnostic figures for the events. The four graphs include: ar0 distribution graph, ar0 clipped distribution graph, car graph, and drift scatter graph

FIndings:
- Beta median 1.040, IQR 0.767-1.380. Reasonable for biotech.
- 13 events have beta < -1, all from DRMA and EQ, both thinly traded.
- Clinical mean and median have OPPOSITE signs. The mean is positive and median is opposite. The shows a higher percentage of decrease among the biotech stock prices, yet the increase has substantially higher rates.

Distributions (this is the substantive finding of the day):
              mean    median   skew   kurtosis   share negative
  CLINICAL    3.229   -1.367    9.91    123.19        56.8%
  EARNINGS    0.221   -0.248    0.62      9.55        51.5%
  REGULATORY -1.277   -0.468   -1.97      7.59        52.8%

- This implies that most findings are dissapointing(which decreases the stock price), but good fidings greatly boosts the stock prcie


Day 7: 8/30

Done:
- Merged 7.01 and 8.01 filings into a single event table. Added earning lables for 2.02 filings.
- Pulled daily prices for all 60 companies plus SPY from yfinance,
2018-01-01 to 2026-03-31.
- Excluded 206 filings carrying BOTH 2.02 and (7.01 or 8.01). These mix earnings with a catalyst, so the price reaction cannot be attributed to either.

Findings:
- 165 filings appear under both 7.01 and 8.01. All 165 received IDENTICAL lables under two runs. 
- CLINICAL dropped from 363 to 222 after removing confounded filings, which is a 39% cut.
Final event table:
EARNINGS      992
CLINICAL      222
REGULATORY    126
PRESENTATION  236
OTHER        1007
unusable       43


Day 6: 8/29

Done:
- Applied Claude API to classify the 100 samples and assign them to different groups with the three encoding rules applied yesterday. Rules include: regulator must be the subject; conference presentations judged by content not format; human translational data counts as CLINICAL
- Then applied LLM to classify all of the 8.01 and 7.01 filings. The results are in the Findings session.
- Pufified the samples by checking their address. Confirmed geographic errors include:Gyre Therapeutics, Zura Bio, Kiora Pharmaceuticals, Ligand, Capricor. Dropped the companies that has less than 50% of historical filings based in San Diego. Result: 67 -> 60 companies, 4,788 -> 4,230 filings.

Findings:
- LLM classification:
- Validated on the 100 hand-labeled filings first: Cohen's kappa = 0.817,
raw agreement 90.0%. CLINICAL precision 0.82, recall 0.93 -- errs toward
over-inclusion, which is the safer direction.
- REGULATORY precision was 0.60, driven by two filings where FDA appears
as background rather than as the subject. Only 3 true cases in the
validation sample, so the estimate is unstable. Stopped iterating here
to avoid overfitting the prompt to 100 filings.

Results:
                 7.01        8.01
  OTHER          500 (54%)   878 (65%)
  PRESENTATION   214 (23%)   115 ( 8%)
  CLINICAL       141 (15%)   222 (16%)
  REGULATORY      35 ( 4%)   131 (10%)
  unusable        44 ( 5%)    12 ( 1%)


Day 5: 8/28

Done:
- Trying to filter the clinical report from 7.01 filings. 
- Decided to drop 1.01 filings and focus on the difference of people's reaction on clinical data and financial report.
- Manually catogorized 100 filings beofre seeing LLM output to set up the baseline and check for accuracy later.
- Decided to narrow down the research topic to: Does Information Complexity Slow Price Discovery? Clinical Trial Results versus Earnings Announcements in San Diego Biotechnology

Findings:
- I tried to filter by matching keywords in the beginning. But after 2,3 rounds of improvement I still found the matching system not satisfying enough. Human language can hardly be understood and filtered by matching keywords and I decided to implement LLM to help catagorize the filings.
- Only 11/100 filings were catagorized into clinical data. Maybe FDA decisions are concentrated in 8.01
- The samples are polluted because reverse mergers preserve the CIK while replacing the business

Day 4: 8/27

Done:
- Filtered the 8-k filings based on their codes and kept those that I need for my papaer:
Baseline group 1: 2.02, the financial report of the biotech compaies. They can be understood more easily.
Baseline group 2: 5.02, the important job changes of the biotech companies. By downloading the text and search for key words such as 'CEO', 'CMO', 'CFO' etc. to determine that they are important enough to shift the stock price (MIGHT DELETE LATER)
Group of interest: 1.01, 7.01, 8.01: these groups' filings need to be fed to the LLM to determine if they are relevant enough for the stock price.
All the other groups are dropped.
- After categorizing the groups, I downloaded the 99.1 files attached on the 8-k filings for future purposes.

Findings:
- The primary 8-k filings are not useful at times. It usually only contains the time, location, and other information that are not related. That's why I decided to shift to the 99.1 filings attached in 8-k filings.


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