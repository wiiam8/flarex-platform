# Data manifest

All data comes from NASA's public Physical Sciences Informatics (PSI) repository: the *experimental table* files for the combustion investigations.
Retrieved 2026-11-14 with `scripts/psi_tables.py`. Files are stored unmodified in `data/psi_tables/`; the app never edits them.

| File | PSI | Rows | Bytes | Encoding | SHA-256 (first 16) |
|---|---|---|---|---|---|
| PSI-100_Experimental table_SAFFIRE-3.csv | PSI-100 | 2 | 239 | utf-8 | `4d3c717ec20dd024` |
| PSI-101_Experimental table_SAME-R.csv | PSI-101 | 109 | 5674 | utf-8 | `87164b7dc9168a42` |
| PSI-102_Experimental table_SAME.csv | PSI-102 | 8 | 331 | utf-8 | `268d1e121d2f211b` |
| PSI-106_Experimental table_Slice.csv | PSI-106 | 12 | 734 | utf-8 | `89ef980810ca6d9a` |
| PSI-107_Experimental table_Spice.csv | PSI-107 | 469 | 31205 | utf-8 | `fb0d7e60cf5367af` |
| PSI-10_Experimental table_Flame Design_Inverse Flame.csv | PSI-10 | 120 | 17314 | utf-8 | `97933ee9ae0b9ebc` |
| PSI-10_Experimental table_Flame Design_Normal Flame.csv | PSI-10 | 207 | 26933 | utf-8 | `4a663292bd3f6520` |
| PSI-142_Experimental table_Data Summary Table.csv | PSI-142 | 8 | 727 | utf-8 | `c66d135b0053590d` |
| PSI-159_Experimental table_CFI-G_Inverse Flames.csv | PSI-159 | 154 | 39422 | utf-8 | `d4d44f8b98969367` |
| PSI-159_Experimental table_CFI-G_Normal Flames.csv | PSI-159 | 179 | 22166 | utf-8 | `d95a621c3fbd27d2` |
| PSI-20_Experimental table_ACME BRE.csv | PSI-20 | 18 | 1113 | utf-8 | `4aa5d3f98708ceac` |
| PSI-21_Experimental table_CLD Flame.csv | PSI-21 | 32 | 2454 | utf-8 | `9fafbc5b3dddaf71` |
| PSI-22_Experimental table_ACME E-FIELD Flames.csv | PSI-22 | 32 | 2475 | utf-8 | `69090c357b83ae38` |
| PSI-23_Experimental table_ACME s-Flame.csv | PSI-23 | 18 | 2456 | utf-8 | `16cd10f50bd2e962` |
| PSI-25_Experimental table_BASS-II.csv | PSI-25 | 129 | 16590 | utf-8 | `71e792bf6b5fb5ea` |
| PSI-26_Experimental table_BASS.csv | PSI-26 | 122 | 4726 | utf-8 | `ccfc3c54d948b64a` |
| PSI-39_Experimental table_CFI.csv | PSI-39 | 87 | 7792 | utf-8 | `fb898e28762353aa` |
| PSI-47_Experimental table_DAFT.csv | PSI-47 | 2 | 518 | utf-8 | `d9d1a436c6e7bbc4` |
| PSI-68_Experimental table_Flex2.csv | PSI-68 | 8 | 1029 | utf-8 | `cc57ad1bd9977aa1` |
| PSI-69_Experimental table_FLEX.csv | PSI-69 | 274 | 24776 | cp1252 | `37c88ce8ae9391b7` |
| PSI-98_Experimental table_SAFFIRE-1.csv | PSI-98 | 4 | 469 | utf-8 | `c01f29c62455f0a3` |
| PSI-99_Experimental table_SAFFIRE-2.csv | PSI-99 | 15 | 1973 | utf-8 | `3c24390b9ef86f3d` |

**Total:** 22 files, 2009 non-empty rows, 211116 bytes.

## How values are interpreted (nothing is guessed)

- **FLEX (PSI-69):** pressure is in mmHg, converted to atm (divide by 760) and psi (x14.696). Headers read `O`, `N`, `CO`, `He` (subscripts lost in the source); FLARE-X reads them as O2, N2, CO2, He. Row sums of 0.98 to 1.01 support this, but it is an interpretation. Test 114 has pressure 0 and is excluded from pressure analysis (flagged).
- **CFI-G (PSI-159) and Flame Design (PSI-10):** pressure is `approx p (bar)` (converted to atm by /1.01325) and `pmean (atm)`. Computed columns (Tad, Zst) are not measurements and are not used for scoring. Inverse-flame CFI-G has trailing blank rows, dropped.
- **CFI (PSI-39):** pressure is text such as `1 atm`; parsed only when the unit is atm.
- **BASS-II (PSI-25), Saffire-I/II (PSI-98, PSI-99):** oxygen only; no pressure column. Saffire oxygen strings like `~ 21.5` are parsed to the first number and flagged `o2_approximate`.
- **FLEX-2 (PSI-68):** planned condition ranges, not measurements; never plotted as tests.
- **BASS (PSI-26), SAME, SAME-R, DAFT, SLICE, SPICE, ACME summaries:** no oxygen/pressure per test; used for the catalog and comparison only.
- Duplicate test IDs, ramped flows and approximate values are kept and flagged, never silently fixed (see the Data & coverage page).

## Other sources

- NASA FLEX and BASS fact sheets and the NASA Combustion Science page (investigation descriptions).
- 2026 Space Apps challenge text (Moon-base reference atmosphere of 30% O2 or more at 10.2 psi or less; absence of partial-gravity data in PSI).
- DOIs for PSI records were taken from the records as documented publicly; verify against the PSI page. Where no DOI was captured the record link is used.
- The PSI web-service endpoints used by `scripts/psi_tables.py` were taken from other participants' public documentation, not an official NASA API guarantee.

## Data reuse and attribution

The NASA Physical Sciences Informatics (PSI) dataset is listed in
the AWS Open Data Registry as having no restrictions on use.
Dataset-specific notices and conditions, where present, take
precedence. FLARE-X preserves the original experimental table
files and documents their source, retrieval date, and processing
interpretations.

Please cite the original PSI investigation records and their
persistent identifiers when reusing this data.