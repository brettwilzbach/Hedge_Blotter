# Cannae Hedge Blotter

## What this does
Single Streamlit app for manual entry of all trades (vanilla options and exotic dual digitals), with Bloomberg integration for 1-year price charts with strike lines and plain-English "rooting for" descriptions.

## Quick start
1. Python 3.11+
2. `pip install -r requirements.txt`
3. **Optional - Bloomberg API:** Run `python install_bloomberg.py` to install Bloomberg features
4. **Test Bloomberg API:** `python test_bloomberg.py` (if Bloomberg is installed)
5. Open Bloomberg Terminal or ensure B-PIPE is reachable (if using Bloomberg features)
6. `streamlit run app.py`

**Note:** The app works without Bloomberg API - you'll just see warnings for Bloomberg features and won't be able to use live charts.

## Data Storage
- **Automatic Saving:** All trades are automatically saved to CSV files in the `data/` folder
- **Persistent Data:** Your trades persist between browser sessions and app restarts
- **Backup System:** Create backups of your data using the "Create Backup" button
- **File Locations:**
  - Live trades: `data/live_trades.csv`
  - Trade history: `data/trade_history.csv`
  - Backups: `data/backups/`

## Manual Entry
**Vanilla Options Form:**
- Trade ID, Trade Date (MM-DD-YYYY), Book, Strategy, Side
- Notional (mm), Contracts (for equity options)
- Expiry, Payoff Type, Index/Ticker, Bloomberg Ticker, Strike
- Cost (bp/USD), MARS ID (optional), Notes
- **Safe Submission:** Radio button prevents accidental submission on Enter

**Exotic Trades Form:**
- All dual digital fields (Index1, Index2, conditions, strikes)
- Logic (AND/OR), MARS ID (optional for Bloomberg integration), Notes
- **Safe Submission:** Radio button prevents accidental submission on Enter

## Bloomberg Integration
- **Installation:** Run `python install_bloomberg.py` to install Bloomberg API
- **Test first:** Run `python test_bloomberg.py` to verify connection
- **In-app test:** Click "Test Bloomberg Connection" in the app
- **Charts:** Select trades to view 1-year price history with strike lines
- **MARS ID:** Optional field for Bloomberg integration and reconciliation
- **Fallback:** App works without Bloomberg - shows warnings instead of charts

## Recon
Recon matches by trade_id and shows:
- Matched trades (between vanilla and exotic)
- Only vanilla trades
- Only exotic trades

## Next steps
- Add SS&C uploader and IDs
- Add tolerances on PV and strikes
- Add Bloomberg Greeks and MARS risk refresh
