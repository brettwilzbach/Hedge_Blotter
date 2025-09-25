# Bloomberg API Integration for Hedge Blotter

This document describes the Bloomberg API integration implemented for the Hedge Blotter application.

## Overview

The integration provides a simple, lightweight wrapper around Bloomberg's API for fetching historical price data and creating charts. The current scope is intentionally minimal, focusing on charting tickers, with plans to extend to Greeks and Market Values from MARS in the future.

## Architecture

### 1. Bloomberg Client (`utils/bloomberg_client.py`)

A lightweight wrapper that provides clean functions for Bloomberg data access:

- `get_hist_data(ticker, flds, start, end)` - Fetch historical data
- `get_current_price(ticker)` - Get current price
- `get_greeks(ticker)` - Placeholder for future Greeks integration
- `get_market_value(mars_id)` - Placeholder for future MARS integration

### 2. Charting Page

A dedicated "Bloomberg Charts" page in the main app that allows users to:
- Enter any Bloomberg ticker
- Select date ranges
- View live price charts
- See current prices

### 3. Integration with Main Blotter

The main blotter page now uses the Bloomberg client to fetch data for trade charts, replacing the previous direct Bloomberg API calls.

## Setup

### 1. Install Dependencies

```bash
pip install blpapi xbbg
```

### 2. Bloomberg Terminal

Ensure Bloomberg Terminal (or Server API) is running on the same machine.

### 3. Environment Variables

Verify `BLPAPI_ROOT` environment variable and DLL paths are set correctly.

## Usage

### Basic Charting

1. Run the app: `streamlit run app.py`
2. Select "Bloomberg Charts" from the sidebar
3. Enter a Bloomberg ticker (e.g., "SPY US Equity")
4. Select date range
5. Click "Get Chart"

### Ticker Examples

- `SPY US Equity` - SPDR S&P 500 ETF
- `CDX HY CDSI S44 5Y PRC Corp` - CDX High Yield Index
- `SPX Index` - S&P 500 Index
- `CLA Comdty` - Crude Oil futures

### Trade Charting

1. Add trades using the manual entry forms
2. Select trades from the dropdown in the main blotter
3. View Bloomberg charts with strike lines for options

## Naming Convention

Bloomberg tickers are used exactly as entered in the blotter (e.g., "SPY US Equity", "CDX HY CDSI S44 5Y PRC Corp"). This ensures the blotter trade log can flow directly into Bloomberg queries without mappings.

## Future Extensions

### Greeks Integration
- Add Delta, Vega, Theta for options via `blp.bdp()`
- Integrate with MARS Bloomberg IDs stored in the blotter

### Market Values
- Pull Market Values from MARS via Bloomberg IDs
- Keep integration clean and modular within `bloomberg_client.py`

## Testing

Run the test script to verify the integration:

```bash
python test_bloomberg_integration.py
```

This will test:
- Bloomberg client imports
- Historical data fetching
- Current price retrieval
- App integration

## Troubleshooting

### Common Issues

1. **"blpapi not installed"** - Run `pip install blpapi xbbg`
2. **"Bloomberg connection failed"** - Ensure Terminal is running
3. **"No data returned"** - Check ticker format and permissions
4. **Import errors** - Verify Bloomberg API installation

### Debug Mode

The app includes detailed error messages and debug information to help diagnose issues.

## Key Features

- ✅ Simple ticker charting
- ✅ Historical price data
- ✅ Current price display
- ✅ Integration with trade blotter
- ✅ Clean, modular architecture
- ✅ Future-ready for Greeks and MARS

## Code Structure

```
utils/
├── bloomberg_client.py    # Bloomberg API wrapper
app.py                     # Main Streamlit app
test_bloomberg_integration.py  # Test script
requirements.txt           # Dependencies
```

The integration follows the principle of "simplicity first" - one small wrapper function + Streamlit charting, with clear extension points for future enhancements.
