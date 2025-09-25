# Cannae Hedge Blotter (MVP)

## What this does
Single Streamlit app for manual entry of all trades (vanilla options and exotic dual digitals), with Bloomberg integration for 1-year price charts with strike lines and plain-English "rooting for" descriptions.

## Quick start
1. Python 3.11+
2. `pip install -r requirements.txt`
3. **Test Bloomberg API:** `python test_bloomberg.py`
4. Open Bloomberg Terminal or ensure B-PIPE is reachable
5. `streamlit run app.py`

## Manual Entry
**Vanilla Options Form:**
- Trade ID, Book, Strategy, Side, Notional, Expiry
- Index/Ticker, Bloomberg Ticker, Payoff Type, Strike
- Cost (bp/USD), MARS ID (optional)

**Exotic Trades Form:**
- All dual digital fields (Index1, Index2, conditions, strikes)
- Logic (AND/OR), MARS ID (optional for Bloomberg integration)

## Bloomberg Integration
- **Test first:** Run `python test_bloomberg.py` to verify connection
- **In-app test:** Click "Test Bloomberg Connection" in the app
- **Charts:** Select trades to view 1-year price history with strike lines
- **MARS ID:** Optional field for Bloomberg integration and reconciliation

## Recon
Recon matches by trade_id and shows:
- Matched trades (between vanilla and exotic)
- Only vanilla trades
- Only exotic trades

## Next steps
- Add SS&C uploader and IDs
- Add tolerances on PV and strikes
- Add Bloomberg Greeks and MARS risk refresh
