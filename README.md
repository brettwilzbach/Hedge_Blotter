# Cannae Hedge Blotter (MVP)

## What this does
Single Streamlit app to log trades on trade date, combine MARS vanilla with manual dual digitals, and show a 1-year chart per trade from Bloomberg with strike and a plain-English "rooting for" label.

## Quick start
1. Python 3.11+
2. `pip install -r requirements.txt`
3. Open Bloomberg Terminal or ensure B-PIPE is reachable
4. `streamlit run app.py`

## Uploads
1. MARS vanilla file, xlsx or csv
2. Manual exotics file, csv

Minimum columns
- Vanilla: trade_date, trade_id, book, strategy, side, index, bbg_ticker, notional_mm_or_contracts, expiry, payoff_type, strike, cost_bp_or_pt, cost_usd
- Exotics: trade_date, trade_id, book, strategy, side, notional_mm, expiry, index1, cond1, strike1, index2, cond2, strike2, logic, cost_bp, cost_usd

## Bloomberg charts
Sidebar shows a Bloomberg connection expander. Desktop API works with defaults. The app fetches PX_LAST for the past year and draws a strike line. Dual digitals show two charts.

## Recon
Recon matches by trade_id only in this MVP and lists three sets:
Matched, Only in MARS, Only in Manual.

## Next steps
- Add SS&C uploader and IDs
- Add tolerances on PV and strikes
- Add Bloomberg Greeks and MARS risk refresh
