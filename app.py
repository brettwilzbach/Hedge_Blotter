# Cannae Hedge Blotter MVP — Streamlit App
# Save as: app.py
# Run with: streamlit run app.py

import io
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import logging

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

# Import Bloomberg client
from utils.bloomberg_client import get_hist_data, get_current_price

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Configuration
# ------------------------------
PRIMARY_COLOR = "#3A606E"  # Cannae teal
CHART_HEIGHT = 300
CHART_WIDTH = 500

# ------------------------------
# Page Setup
# ------------------------------
st.set_page_config(
    page_title="Cannae Hedge Blotter MVP",
    page_icon="📘",
    layout="wide",
)

st.markdown(
    f"""
    <style>
        .metric-label {{ color: {PRIMARY_COLOR}; font-weight: 600; }}
        .chart-container {{ margin: 10px 0; }}
        .recon-section {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------
# Data Loading Functions
# ------------------------------

def load_mars_data(file) -> pd.DataFrame:
    """Load MARS vanilla trades from Excel or CSV."""
    try:
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
        
        # Show original columns for debugging
        st.write("**Original columns found:**", list(df.columns))
        
        # Normalize column names for matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Show normalized columns for debugging
        st.write("**Normalized columns:**", list(df.columns))
        
        # Expected MARS columns (flexible matching)
        mars_columns = {
            'trade_date': ['trade_date', 'date', 'trade date'],
            'trade_id': ['trade_id', 'tradeid', 'id', 'trade id'],
            'book': ['book', 'portfolio'],
            'strategy': ['strategy', 'strat'],
            'side': ['side', 'direction'],
            'index': ['index', 'underlying', 'ticker'],
            'bbg_ticker': ['bbg_ticker', 'bloomberg_ticker', 'bbg ticker', 'ticker'],
            'notional_mm_or_contracts': ['notional_mm_or_contracts', 'notional', 'size'],
            'expiry': ['expiry', 'expiration', 'maturity'],
            'payoff_type': ['payoff_type', 'payoff', 'product_type'],
            'strike': ['strike', 'strike_price'],
            'cost_bp_or_pt': ['cost_bp_or_pt', 'cost_bp', 'premium_bp'],
            'cost_usd': ['cost_usd', 'cost', 'premium_usd']
        }
        
        # Map columns
        standardized = pd.DataFrame()
        mapped_columns = {}
        for standard_name, possible_names in mars_columns.items():
            matched_col = None
            for possible in possible_names:
                if possible in df.columns:
                    matched_col = possible
                    break
            if matched_col:
                standardized[standard_name] = df[matched_col]
                mapped_columns[standard_name] = matched_col
            else:
                standardized[standard_name] = np.nan
        
        # Show mapping results for debugging
        st.write("**Column mapping results:**", mapped_columns)
        
        standardized['source'] = 'MARS'
        
        # Auto-detect vanilla trades based on ticker content
        def detect_vanilla_trade(row):
            """Detect if this is a vanilla trade based on ticker content."""
            # Check various ticker fields for SPY or CDX
            ticker_fields = ['index', 'bbg_ticker']
            for field in ticker_fields:
                if field in row and pd.notna(row[field]):
                    ticker = str(row[field]).upper()
                    if 'SPY' in ticker or 'CDX' in ticker:
                        return True
            return False
        
        # Auto-detect payoff type for vanilla trades
        if not standardized.empty:
            vanilla_mask = standardized.apply(detect_vanilla_trade, axis=1)
            standardized.loc[vanilla_mask, 'payoff_type'] = standardized.loc[vanilla_mask, 'payoff_type'].fillna('Vanilla')
            
            # If payoff_type is still empty, try to infer from existing data
            standardized['payoff_type'] = standardized['payoff_type'].fillna('Unknown')
        
        # Convert data types
        if 'trade_date' in standardized.columns:
            standardized['trade_date'] = pd.to_datetime(standardized['trade_date'], errors='coerce')
        if 'expiry' in standardized.columns:
            standardized['expiry'] = pd.to_datetime(standardized['expiry'], errors='coerce')
        
        numeric_cols = ['notional_mm_or_contracts', 'strike', 'cost_bp_or_pt', 'cost_usd']
        for col in numeric_cols:
            if col in standardized.columns:
                standardized[col] = pd.to_numeric(standardized[col], errors='coerce')
        
        # Debug info
        if not standardized.empty:
            vanilla_count = len(standardized[standardized['payoff_type'] == 'Vanilla'])
            st.info(f"MARS parsing: {len(standardized)} total trades, {vanilla_count} detected as vanilla (SPY/CDX)")
            
            # Show sample of parsed data for debugging
            with st.expander("Debug: Parsed MARS Data Sample"):
                st.dataframe(standardized.head())
        
        return standardized
        
    except Exception as e:
        st.error(f"Error loading MARS data: {str(e)}")
        return pd.DataFrame()

def load_exotics_data(file) -> pd.DataFrame:
    """Load manual exotics from CSV."""
    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.lower().str.strip()
        
        # Expected exotics columns
        exotics_columns = {
            'trade_date': ['trade_date', 'date', 'trade date'],
            'trade_id': ['trade_id', 'tradeid', 'id', 'trade id'],
            'book': ['book', 'portfolio'],
            'strategy': ['strategy', 'strat'],
            'side': ['side', 'direction'],
            'notional_mm': ['notional_mm', 'notional', 'size'],
            'expiry': ['expiry', 'expiration', 'maturity'],
            'index1': ['index1', 'underlying1', 'ticker1'],
            'cond1': ['cond1', 'condition1', 'barrier_type1'],
            'strike1': ['strike1', 'strike_1', 'barrier1'],
            'index2': ['index2', 'underlying2', 'ticker2'],
            'cond2': ['cond2', 'condition2', 'barrier_type2'],
            'strike2': ['strike2', 'strike_2', 'barrier2'],
            'logic': ['logic', 'and_or', 'operator'],
            'cost_bp': ['cost_bp', 'premium_bp', 'cost'],
            'cost_usd': ['cost_usd', 'premium_usd', 'cost_dollars']
        }
        
        # Map columns
        standardized = pd.DataFrame()
        for standard_name, possible_names in exotics_columns.items():
            matched_col = None
            for possible in possible_names:
                if possible in df.columns:
                    matched_col = possible
                    break
            if matched_col:
                standardized[standard_name] = df[matched_col]
            else:
                standardized[standard_name] = np.nan
        
        standardized['source'] = 'Manual'
        standardized['payoff_type'] = 'Dual Digital'  # Assume dual digitals for exotics
        
        # Convert data types
        if 'trade_date' in standardized.columns:
            standardized['trade_date'] = pd.to_datetime(standardized['trade_date'], errors='coerce')
        if 'expiry' in standardized.columns:
            standardized['expiry'] = pd.to_datetime(standardized['expiry'], errors='coerce')
        
        numeric_cols = ['notional_mm', 'strike1', 'strike2', 'cost_bp', 'cost_usd']
        for col in numeric_cols:
            if col in standardized.columns:
                standardized[col] = pd.to_numeric(standardized[col], errors='coerce')
        
        return standardized
        
    except Exception as e:
        st.error(f"Error loading exotics data: {str(e)}")
        return pd.DataFrame()

# ------------------------------
# Bloomberg Functions
# ------------------------------

@st.cache_resource
def get_bloomberg_session(host: str = "", port: int = 8194):
    """Initialize Bloomberg session."""
    try:
        import blpapi
        options = blpapi.SessionOptions()
        if host:
            options.setServerHost(host)
        options.setServerPort(port)
        
        session = blpapi.Session(options)
        if not session.start():
            return None
        
        if not session.openService("//blp/refdata"):
            return None
            
        return session
    except ImportError:
        st.error("blpapi not installed. Run: pip install blpapi")
        return None
    except Exception as e:
        st.error(f"Bloomberg connection failed: {str(e)}")
        return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_bloomberg_history(tickers: List[str], host: str = "", port: int = 8194) -> pd.DataFrame:
    """Fetch 1-year price history from Bloomberg."""
    if not tickers:
        return pd.DataFrame()
    
    try:
        import blpapi
        session = get_bloomberg_session(host, port)
        if not session:
            return pd.DataFrame()
        
        service = session.getService("//blp/refdata")
        request = service.createRequest("HistoricalDataRequest")
        
        # Add securities
        securities = request.getElement("securities")
        for ticker in tickers:
            if ticker and str(ticker).strip():
                securities.appendValue(str(ticker).strip())
        
        # Add fields
        fields = request.getElement("fields")
        fields.appendValue("PX_LAST")
        
        # Set dates (1 year history)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        request.set("startDate", start_date.strftime("%Y%m%d"))
        request.set("endDate", end_date.strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")
        
        # Send request
        session.sendRequest(request)
        
        # Process response
        data = []
        while True:
            event = session.nextEvent(5000)  # 5 second timeout
            for msg in event:
                if msg.messageType() == blpapi.Name("HistoricalDataResponse"):
                    security_data = msg.getElement("securityData")
                    ticker = security_data.getElementAsString("security")
                    field_data = security_data.getElement("fieldData")
                    
                    for i in range(field_data.numValues()):
                        record = field_data.getValueAsElement(i)
                        date = record.getElementAsDatetime("date")
                        if record.hasElement("PX_LAST"):
                            price = record.getElementAsFloat("PX_LAST")
                            data.append({
                                'date': pd.Timestamp(date.date()),
                                'ticker': ticker,
                                'price': price
                            })
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Bloomberg data fetch failed: {str(e)}")
        return pd.DataFrame()

def create_price_chart(price_data: pd.DataFrame, ticker: str, strike: float = None, title: str = "") -> alt.Chart:
    """Create Altair chart for price history with optional strike line."""
    if price_data.empty:
        return alt.Chart(pd.DataFrame()).mark_text(text="No data available")
    
    ticker_data = price_data[price_data['ticker'] == ticker].copy()
    if ticker_data.empty:
        return alt.Chart(pd.DataFrame()).mark_text(text=f"No data for {ticker}")
    
    # Base line chart
    line_chart = alt.Chart(ticker_data).mark_line(color=PRIMARY_COLOR, strokeWidth=2).encode(
        x=alt.X('date:T', title='Date'),
        y=alt.Y('price:Q', title='Price'),
        tooltip=['date:T', 'price:Q']
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title=title or f"{ticker} - 1 Year History"
    )
    
    # Add strike line if provided
    if strike and not pd.isna(strike):
        strike_line = alt.Chart(pd.DataFrame({'strike': [strike]})).mark_rule(
            color='red', strokeDash=[5, 5], size=2
        ).encode(
            y='strike:Q',
            tooltip=alt.value(f"Strike: {strike}")
        )
        return line_chart + strike_line
    
    return line_chart

def get_rooting_description(trade_row: pd.Series, ticker: str) -> str:
    """Generate plain English description of what we're rooting for."""
    side = str(trade_row.get('side', '')).lower()
    payoff = str(trade_row.get('payoff_type', '')).lower()
    
    # For dual digitals
    if payoff == 'dual digital':
        if ticker == trade_row.get('index1'):
            cond = str(trade_row.get('cond1', '')).lower()
            if '>=' in cond or 'above' in cond:
                return f"Rooting for {ticker} to go HIGHER"
            elif '<=' in cond or 'below' in cond:
                return f"Rooting for {ticker} to go LOWER"
        elif ticker == trade_row.get('index2'):
            cond = str(trade_row.get('cond2', '')).lower()
            if '>=' in cond or 'above' in cond:
                return f"Rooting for {ticker} to go HIGHER"
            elif '<=' in cond or 'below' in cond:
                return f"Rooting for {ticker} to go LOWER"
    
    # For vanilla options
    elif 'call' in payoff.lower():
        if 'long' in side:
            return f"Rooting for {ticker} to go HIGHER"
        else:
            return f"Rooting for {ticker} to go LOWER"
    elif 'put' in payoff.lower():
        if 'long' in side:
            return f"Rooting for {ticker} to go LOWER"
        else:
            return f"Rooting for {ticker} to go HIGHER"
    
    # Default
    return f"Rooting for {ticker} favorable move"

# ------------------------------
# Recon Functions
# ------------------------------

def perform_recon(mars_df: pd.DataFrame, exotics_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Perform reconciliation between MARS and manual data by trade_id."""
    recon_results = {
        'matched': pd.DataFrame(),
        'only_mars': pd.DataFrame(),
        'only_manual': pd.DataFrame()
    }
    
    if mars_df.empty and exotics_df.empty:
        return recon_results
    
    # Check if trade_id column exists before accessing
    mars_ids = set()
    if not mars_df.empty and 'trade_id' in mars_df.columns:
        mars_ids = set(mars_df['trade_id'].dropna().astype(str))
    
    exotic_ids = set()
    if not exotics_df.empty and 'trade_id' in exotics_df.columns:
        exotic_ids = set(exotics_df['trade_id'].dropna().astype(str))
    
    matched_ids = mars_ids.intersection(exotic_ids)
    only_mars_ids = mars_ids - exotic_ids
    only_exotic_ids = exotic_ids - mars_ids
    
    if matched_ids and 'trade_id' in mars_df.columns and 'trade_id' in exotics_df.columns:
        mars_matched = mars_df[mars_df['trade_id'].astype(str).isin(matched_ids)]
        exotic_matched = exotics_df[exotics_df['trade_id'].astype(str).isin(matched_ids)]
        recon_results['matched'] = pd.concat([mars_matched, exotic_matched], ignore_index=True)
    
    if only_mars_ids and 'trade_id' in mars_df.columns:
        recon_results['only_mars'] = mars_df[mars_df['trade_id'].astype(str).isin(only_mars_ids)]
    
    if only_exotic_ids and 'trade_id' in exotics_df.columns:
        recon_results['only_manual'] = exotics_df[exotics_df['trade_id'].astype(str).isin(only_exotic_ids)]
    
    return recon_results

# ------------------------------
# Main Application
# ------------------------------

def test_bloomberg_connection():
    """Test Bloomberg API connection with SPY data."""
    st.header("🔍 Bloomberg API Test")

    if st.button("Test Bloomberg Connection", type="primary"):
        with st.spinner("Testing Bloomberg connection..."):
            try:
                # Test basic import
                import blpapi
                st.success("✅ blpapi module imported successfully")

                # Test session creation
                session = get_bloomberg_session()
                if session:
                    st.success("✅ Bloomberg session created successfully")

                    # Test with SPY data
                    spy_data = get_bloomberg_history(['SPY US Equity'])

                    if not spy_data.empty:
                        st.success(f"✅ Successfully fetched SPY data: {len(spy_data)} records")

                        # Show sample data
                        st.subheader("SPY Price Data Sample:")
                        st.dataframe(spy_data.head(10))

                        # Show latest price
                        latest_price = spy_data.iloc[-1]
                        st.metric("Latest SPY Price", f"${latest_price['price']:.2f}", delta=None)

                        # Create a simple chart
                        chart = create_price_chart(spy_data, 'SPY US Equity', title="SPY US Equity - Test Chart")
                        st.altair_chart(chart, use_container_width=True)

                    else:
                        st.warning("⚠️ No data returned from Bloomberg API")
                        st.info("This could mean: Bloomberg Terminal not running, API not properly configured, or no permissions for SPY data")

                else:
                    st.error("❌ Failed to create Bloomberg session")
                    st.info("Make sure: Bloomberg Terminal is running, API is properly installed and configured")

            except ImportError:
                st.error("❌ blpapi module not found")
                st.error("Please install Bloomberg API following the setup guide:")
                st.code("pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi", language="bash")
            except Exception as e:
                st.error(f"❌ Bloomberg test failed: {str(e)}")

def bloomberg_charting_page():
    """Dedicated page for Bloomberg charting functionality."""
    st.title("📈 Bloomberg Charting")
    st.caption("Live Bloomberg charts for any ticker")
    
    # Ticker input
    col1, col2 = st.columns([2, 1])
    
    with col1:
        ticker = st.text_input("Enter Bloomberg Ticker", "SPY US Equity", 
                              help="Examples: SPY US Equity, CDX HY CDSI S44 5Y PRC Corp, SPX Index")
    
    with col2:
        if st.button("Get Chart", type="primary"):
            st.rerun()
    
    # Date range selection
    col3, col4 = st.columns(2)
    with col3:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=365))
    with col4:
        end_date = st.date_input("End Date", value=datetime.now().date())
    
    # Fetch and display data
    if ticker:
        with st.spinner(f"Fetching data for {ticker}..."):
            try:
                # Convert dates to string format
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                
                # Get historical data using our Bloomberg client
                df = get_hist_data(ticker, ["PX_LAST"], start_str, end_str)
                
                if not df.empty:
                    st.success(f"✅ Successfully fetched {len(df)} records for {ticker}")
                    
                    # Display current price
                    current_price = get_current_price(ticker)
                    if current_price:
                        st.metric("Current Price", f"${current_price:.2f}")
                    
                    # Create and display chart
                    if 'date' in df.columns and 'price' in df.columns:
                        # Create Altair chart
                        chart = alt.Chart(df).mark_line(
                            color=PRIMARY_COLOR, 
                            strokeWidth=2
                        ).encode(
                            x=alt.X('date:T', title='Date'),
                            y=alt.Y('price:Q', title='Price'),
                            tooltip=['date:T', 'price:Q']
                        ).properties(
                            width=800,
                            height=400,
                            title=f"{ticker} - Price History"
                        )
                        
                        st.altair_chart(chart, use_container_width=True)
                        
                        # Show data table
                        with st.expander("View Raw Data"):
                            st.dataframe(df)
                    else:
                        st.error("Unexpected data format from Bloomberg API")
                        st.write("Data columns:", list(df.columns))
                        st.dataframe(df)
                        
                else:
                    st.warning(f"No data returned for {ticker}")
                    st.info("This could mean:")
                    st.write("- Bloomberg Terminal is not running")
                    st.write("- Invalid ticker format")
                    st.write("- No permissions for this ticker")
                    st.write("- Network connectivity issues")
                    
            except Exception as e:
                st.error(f"Error fetching data: {str(e)}")
                st.info("Make sure Bloomberg Terminal is running and the ticker format is correct")

def main():
    st.title("Cannae Hedge Blotter MVP")
    st.caption("Manual entry for all trades - vanilla options and exotic dual digitals with Bloomberg integration")

    # Page selection
    page = st.sidebar.selectbox(
        "Select Page",
        ["Main Blotter", "Bloomberg Charts", "Bloomberg Test"]
    )
    
    if page == "Bloomberg Charts":
        bloomberg_charting_page()
        return
    elif page == "Bloomberg Test":
        test_bloomberg_connection()
        return
    
    # Main blotter page continues here...
    # Test Bloomberg connection first
    test_bloomberg_connection()

    # Removed file uploads - everything is manual entry now
    
    # Bloomberg connection settings
    with st.sidebar.expander("Bloomberg Connection"):
        st.write("Desktop API works with defaults")
        bbg_host = st.text_input("Host (optional)", value="")
        bbg_port = st.number_input("Port", value=8194, step=1)
    
    # Manual Entry Forms
    st.sidebar.header("Manual Entry")
    
    # Vanilla Options Entry Form
    with st.sidebar.expander("Add Vanilla Option", expanded=True):
        with st.form("vanilla_entry_form"):
            vanilla_trade_id = st.text_input("Trade ID*", placeholder="EX-SPY-001", key="vanilla_trade_id")
            vanilla_book = st.selectbox("Book", ["Hedge", "Trading", "Prop"], key="vanilla_book")
            vanilla_strategy = st.text_input("Strategy", placeholder="Index Options", key="vanilla_strategy")
            vanilla_side = st.selectbox("Side", ["Long", "Short"], key="vanilla_side")
            
            vanilla_col1, vanilla_col2 = st.columns(2)
            with vanilla_col1:
                vanilla_notional = st.number_input("Notional (mm)*", min_value=0.0, step=0.1, format="%.1f", key="vanilla_notional")
            with vanilla_col2:
                vanilla_expiry = st.date_input("Expiry*", value=datetime.now().date() + timedelta(days=30), key="vanilla_expiry")
            
            vanilla_index = st.text_input("Index/Ticker*", placeholder="SPY US Equity", key="vanilla_index")
            vanilla_bbg_ticker = st.text_input("Bloomberg Ticker*", placeholder="SPY US Equity", key="vanilla_bbg_ticker")
            vanilla_payoff_type = st.selectbox("Payoff Type", ["Call", "Put", "Vanilla"], key="vanilla_payoff_type")
            vanilla_strike = st.number_input("Strike*", step=0.01, format="%.2f", key="vanilla_strike")
            
            vanilla_col3, vanilla_col4 = st.columns(2)
            with vanilla_col3:
                vanilla_cost_bp = st.number_input("Cost (bp)", min_value=0.0, step=0.1, format="%.1f", key="vanilla_cost_bp")
            with vanilla_col4:
                vanilla_cost_usd = st.number_input("Cost ($)", min_value=0.0, step=1000.0, format="%.0f", key="vanilla_cost_usd")
            
            vanilla_mars_id = st.text_input("MARS ID (for Bloomberg integration)", placeholder="Optional MARS reference", key="vanilla_mars_id")
            
            vanilla_submitted = st.form_submit_button("Add Vanilla Trade", type="primary")
            
            if vanilla_submitted:
                if vanilla_trade_id and vanilla_notional and vanilla_index and vanilla_bbg_ticker and vanilla_strike:
                    new_vanilla_trade = {
                        'trade_date': datetime.now().date(),
                        'trade_id': vanilla_trade_id,
                        'book': vanilla_book,
                        'strategy': vanilla_strategy,
                        'side': vanilla_side,
                        'index': vanilla_index,
                        'bbg_ticker': vanilla_bbg_ticker,
                        'notional_mm_or_contracts': vanilla_notional,
                        'expiry': vanilla_expiry,
                        'payoff_type': vanilla_payoff_type,
                        'strike': vanilla_strike,
                        'cost_bp_or_pt': vanilla_cost_bp if vanilla_cost_bp > 0 else None,
                        'cost_usd': vanilla_cost_usd if vanilla_cost_usd > 0 else None,
                        'mars_id': vanilla_mars_id if vanilla_mars_id else None,
                        'source': 'Manual',
                        'trade_type': 'Vanilla'
                    }
                    
                    if 'manual_vanilla_trades' not in st.session_state:
                        st.session_state.manual_vanilla_trades = []
                    st.session_state.manual_vanilla_trades.append(new_vanilla_trade)
                    st.success(f"Added vanilla trade {vanilla_trade_id}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields (marked with *)")
    
    # Exotics Entry Form
    with st.sidebar.expander("Add Exotic Trade", expanded=True):
        with st.form("manual_entry_form"):
            trade_id = st.text_input("Trade ID*", placeholder="EX-DD-001")
            book = st.selectbox("Book", ["Hedge", "Trading", "Prop"])
            strategy = st.text_input("Strategy", placeholder="Cross-Asset Digitals")
            side = st.selectbox("Side", ["Long", "Short"])

            col1, col2 = st.columns(2)
            with col1:
                notional_mm = st.number_input("Notional (mm)*", min_value=0.0, step=0.1, format="%.1f")
            with col2:
                expiry = st.date_input("Expiry*", value=datetime.now().date() + timedelta(days=90))

            st.subheader("Index 1")
            index1 = st.text_input("Index 1*", placeholder="SPX Index")
            cond1 = st.selectbox("Condition 1", ["<=", ">=", "<", ">", "=="])
            strike1 = st.number_input("Strike 1*", step=0.01, format="%.2f")

            st.subheader("Index 2")
            index2 = st.text_input("Index 2*", placeholder="CLA Comdty")
            cond2 = st.selectbox("Condition 2", ["<=", ">=", "<", ">", "=="])
            strike2 = st.number_input("Strike 2*", step=0.01, format="%.2f")

            logic = st.selectbox("Logic", ["AND", "OR"])

            col3, col4 = st.columns(2)
            with col3:
                cost_bp = st.number_input("Cost (bp)", min_value=0.0, step=0.1, format="%.1f")
            with col4:
                cost_usd = st.number_input("Cost ($)", min_value=0.0, step=1000.0, format="%.0f")

            mars_id = st.text_input("MARS ID (for Bloomberg integration)", placeholder="Optional MARS reference")

            submitted = st.form_submit_button("Add Trade", type="primary")

            if submitted:
                if trade_id and notional_mm and index1 and strike1 and index2 and strike2:
                    new_trade = {
                        'trade_date': datetime.now().date(),
                        'trade_id': trade_id,
                        'book': book,
                        'strategy': strategy,
                        'side': side,
                        'notional_mm': notional_mm,
                        'expiry': expiry,
                        'index1': index1,
                        'cond1': cond1,
                        'strike1': strike1,
                        'index2': index2,
                        'cond2': cond2,
                        'strike2': strike2,
                        'logic': logic,
                        'cost_bp': cost_bp if cost_bp > 0 else None,
                        'cost_usd': cost_usd if cost_usd > 0 else None,
                        'mars_id': mars_id if mars_id else None,
                        'source': 'Manual',
                        'payoff_type': 'Dual Digital',
                        'trade_type': 'Exotic'
                    }

                    if 'manual_trades' not in st.session_state:
                        st.session_state.manual_trades = []
                    st.session_state.manual_trades.append(new_trade)
                    st.success(f"Added trade {trade_id}")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields (marked with *)")
    
    # Initialize manual trades stores
    if 'manual_trades' not in st.session_state:
        st.session_state.manual_trades = []
    if 'manual_vanilla_trades' not in st.session_state:
        st.session_state.manual_vanilla_trades = []
    
    # Convert manual vanilla trades to DataFrame
    vanilla_data = pd.DataFrame()
    if st.session_state.manual_vanilla_trades:
        vanilla_data = pd.DataFrame(st.session_state.manual_vanilla_trades)
        st.sidebar.success(f"{len(st.session_state.manual_vanilla_trades)} vanilla trades entered")
    
    # Convert manual exotic trades to DataFrame
    exotics_data = pd.DataFrame()
    if st.session_state.manual_trades:
        exotics_data = pd.DataFrame(st.session_state.manual_trades)
        st.sidebar.success(f"{len(st.session_state.manual_trades)} exotic trades entered")
    
    # Show data overview
    if not vanilla_data.empty or not exotics_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Manual Vanilla Trades")
            if not vanilla_data.empty:
                st.dataframe(vanilla_data, height=300)
            else:
                st.info("No vanilla trades entered")
        
        with col2:
            st.subheader("Manual Exotics Trades")
            if not exotics_data.empty:
                st.dataframe(exotics_data, height=300)
                
                # Add edit/delete functionality for manual trades
                if st.session_state.manual_trades:
                    st.subheader("Manage Manual Trades")
                    for i, trade in enumerate(st.session_state.manual_trades):
                        with st.expander(f"Trade {trade['trade_id']} - {trade['index1']} / {trade['index2']}"):
                            col_edit, col_delete = st.columns(2)
                            
                            with col_edit:
                                if st.button(f"Edit", key=f"edit_{i}"):
                                    st.session_state[f"edit_trade_{i}"] = True
                            
                            with col_delete:
                                if st.button(f"Delete", key=f"delete_{i}"):
                                    del st.session_state.manual_trades[i]
                                    st.success(f"Deleted trade {trade['trade_id']}")
                                    st.rerun()
                            
                            # Edit form
                            if st.session_state.get(f"edit_trade_{i}", False):
                                st.write("**Edit Trade**")
                                with st.form(f"edit_form_{i}"):
                                    edit_trade_id = st.text_input("Trade ID*", value=trade['trade_id'], key=f"edit_id_{i}")
                                    edit_book = st.selectbox("Book", ["Hedge", "Trading", "Prop"], 
                                                           index=["Hedge", "Trading", "Prop"].index(trade['book']), 
                                                           key=f"edit_book_{i}")
                                    edit_strategy = st.text_input("Strategy", value=trade['strategy'], key=f"edit_strategy_{i}")
                                    edit_side = st.selectbox("Side", ["Long", "Short"], 
                                                           index=["Long", "Short"].index(trade['side']), 
                                                           key=f"edit_side_{i}")
                                    
                                    edit_col1, edit_col2 = st.columns(2)
                                    with edit_col1:
                                        edit_notional = st.number_input("Notional (mm)*", value=float(trade['notional_mm']), 
                                                                      min_value=0.0, step=0.1, format="%.1f", key=f"edit_notional_{i}")
                                    with edit_col2:
                                        edit_expiry = st.date_input("Expiry*", value=trade['expiry'], key=f"edit_expiry_{i}")
                                    
                                    st.write("**Index 1**")
                                    edit_index1 = st.text_input("Index 1*", value=trade['index1'], key=f"edit_index1_{i}")
                                    edit_cond1 = st.selectbox("Condition 1", ["<=", ">=", "<", ">", "=="], 
                                                            index=["<=", ">=", "<", ">", "=="].index(trade['cond1']), 
                                                            key=f"edit_cond1_{i}")
                                    edit_strike1 = st.number_input("Strike 1*", value=float(trade['strike1']), 
                                                                  step=0.01, format="%.2f", key=f"edit_strike1_{i}")
                                    
                                    st.write("**Index 2**")
                                    edit_index2 = st.text_input("Index 2*", value=trade['index2'], key=f"edit_index2_{i}")
                                    edit_cond2 = st.selectbox("Condition 2", ["<=", ">=", "<", ">", "=="], 
                                                            index=["<=", ">=", "<", ">", "=="].index(trade['cond2']), 
                                                            key=f"edit_cond2_{i}")
                                    edit_strike2 = st.number_input("Strike 2*", value=float(trade['strike2']), 
                                                                  step=0.01, format="%.2f", key=f"edit_strike2_{i}")
                                    
                                    edit_logic = st.selectbox("Logic", ["AND", "OR"], 
                                                            index=["AND", "OR"].index(trade['logic']), 
                                                            key=f"edit_logic_{i}")
                                    
                                    edit_col3, edit_col4 = st.columns(2)
                                    with edit_col3:
                                        edit_cost_bp = st.number_input("Cost (bp)", value=float(trade['cost_bp']) if trade['cost_bp'] else 0.0, 
                                                                      min_value=0.0, step=0.1, format="%.1f", key=f"edit_cost_bp_{i}")
                                    with edit_col4:
                                        edit_cost_usd = st.number_input("Cost ($)", value=float(trade['cost_usd']) if trade['cost_usd'] else 0.0, 
                                                                       min_value=0.0, step=1000.0, format="%.0f", key=f"edit_cost_usd_{i}")
                                    
                                    edit_col_save, edit_col_cancel = st.columns(2)
                                    with edit_col_save:
                                        if st.form_submit_button("Save Changes"):
                                            # Update the trade
                                            st.session_state.manual_trades[i] = {
                                                'trade_date': trade['trade_date'],
                                                'trade_id': edit_trade_id,
                                                'book': edit_book,
                                                'strategy': edit_strategy,
                                                'side': edit_side,
                                                'notional_mm': edit_notional,
                                                'expiry': edit_expiry,
                                                'index1': edit_index1,
                                                'cond1': edit_cond1,
                                                'strike1': edit_strike1,
                                                'index2': edit_index2,
                                                'cond2': edit_cond2,
                                                'strike2': edit_strike2,
                                                'logic': edit_logic,
                                                'cost_bp': edit_cost_bp if edit_cost_bp > 0 else None,
                                                'cost_usd': edit_cost_usd if edit_cost_usd > 0 else None,
                                                'source': 'Manual',
                                                'payoff_type': 'Dual Digital',
                                            }
                                            st.session_state[f"edit_trade_{i}"] = False
                                            st.success(f"Updated trade {edit_trade_id}")
                                            st.rerun()
                                    
                                    with edit_col_cancel:
                                        if st.form_submit_button("Cancel"):
                                            st.session_state[f"edit_trade_{i}"] = False
                                            st.rerun()
            else:
                st.info("No exotics data loaded")
        
        st.divider()
        
        # Recon section
        st.subheader("Reconciliation")
        recon_results = perform_recon(vanilla_data, exotics_data)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Matched", len(recon_results['matched']))
            if not recon_results['matched'].empty:
                with st.expander("View Matched Trades"):
                    st.dataframe(recon_results['matched'])
        
        with col2:
            st.metric("Only Vanilla", len(recon_results['only_mars']))
            if not recon_results['only_mars'].empty:
                with st.expander("View Vanilla Only"):
                    st.dataframe(recon_results['only_mars'])
        
        with col3:
            st.metric("Only Manual", len(recon_results['only_manual']))
            if not recon_results['only_manual'].empty:
                with st.expander("View Manual Only"):
                    st.dataframe(recon_results['only_manual'])
        
        st.divider()
        
        # Bloomberg Charts Section
        st.subheader("Bloomberg Charts")
        
        # Combine all data for charting
        all_trades = []
        if not vanilla_data.empty:
            all_trades.append(vanilla_data)
        if not exotics_data.empty:
            all_trades.append(exotics_data)
        
        if all_trades:
            combined_data = pd.concat(all_trades, ignore_index=True)
            
            # Trade selection
            trade_options = []
            for idx, row in combined_data.iterrows():
                trade_id = row.get('trade_id', 'N/A')
                trade_type = row.get('trade_type', 'Unknown')
                payoff = row.get('payoff_type', 'N/A')
                
                if trade_type == 'Exotic' or payoff == 'Dual Digital':
                    ticker1 = row.get('index1', 'N/A')
                    ticker2 = row.get('index2', 'N/A')
                    label = f"{trade_id} - {payoff} ({ticker1}, {ticker2})"
                else:
                    # Vanilla trade
                    ticker = row.get('bbg_ticker', row.get('index', 'N/A'))
                    label = f"{trade_id} - {payoff} ({ticker})"
                trade_options.append((label, idx))
            
            selected_trades = st.multiselect(
                "Select trades to chart",
                options=trade_options,
                format_func=lambda x: x[0],
                default=trade_options[:3] if len(trade_options) >= 3 else trade_options
            )
            
            if selected_trades:
                # Collect tickers needed
                tickers_needed = set()
                for _, idx in selected_trades:
                    row = combined_data.iloc[idx]
                    trade_type = row.get('trade_type', 'Unknown')
                    
                    if trade_type == 'Exotic' or row.get('payoff_type') == 'Dual Digital':
                        if pd.notna(row.get('index1')):
                            tickers_needed.add(row.get('index1'))
                        if pd.notna(row.get('index2')):
                            tickers_needed.add(row.get('index2'))
                    else:
                        # Vanilla trade
                        ticker = row.get('bbg_ticker', row.get('index'))
                        if pd.notna(ticker):
                            tickers_needed.add(ticker)
                
                # Fetch Bloomberg data using new client
                if tickers_needed:
                    with st.spinner("Fetching Bloomberg data..."):
                        # Use our new Bloomberg client for each ticker
                        all_price_data = []
                        for ticker in tickers_needed:
                            try:
                                # Get 1 year of data
                                end_date = datetime.now().date()
                                start_date = end_date - timedelta(days=365)
                                
                                df = get_hist_data(ticker, ["PX_LAST"], 
                                                  start_date.strftime("%Y-%m-%d"), 
                                                  end_date.strftime("%Y-%m-%d"))
                                
                                if not df.empty and 'date' in df.columns and 'price' in df.columns:
                                    df['ticker'] = ticker
                                    all_price_data.append(df)
                                    
                            except Exception as e:
                                st.warning(f"Could not fetch data for {ticker}: {str(e)}")
                        
                        # Combine all data
                        if all_price_data:
                            price_data = pd.concat(all_price_data, ignore_index=True)
                        else:
                            price_data = pd.DataFrame()
                    
                    if not price_data.empty:
                        # Create charts for selected trades
                        for _, idx in selected_trades:
                            row = combined_data.iloc[idx]
                            trade_id = row.get('trade_id', 'N/A')
                            trade_type = row.get('trade_type', 'Unknown')
                            payoff = row.get('payoff_type', 'N/A')
                            
                            st.subheader(f"Trade {trade_id} - {payoff}")
                            
                            if trade_type == 'Exotic' or payoff == 'Dual Digital':
                                # Dual digital - show two charts
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    ticker1 = row.get('index1')
                                    strike1 = row.get('strike1')
                                    if ticker1:
                                        title1 = get_rooting_description(row, ticker1)
                                        chart1 = create_price_chart(price_data, ticker1, strike1, title1)
                                        st.altair_chart(chart1, use_container_width=True)
                                
                                with col2:
                                    ticker2 = row.get('index2')
                                    strike2 = row.get('strike2')
                                    if ticker2:
                                        title2 = get_rooting_description(row, ticker2)
                                        chart2 = create_price_chart(price_data, ticker2, strike2, title2)
                                        st.altair_chart(chart2, use_container_width=True)
                            
                            else:
                                # Vanilla option - single chart
                                ticker = row.get('bbg_ticker', row.get('index'))
                                strike = row.get('strike')
                                if ticker:
                                    title = get_rooting_description(row, ticker)
                                    chart = create_price_chart(price_data, ticker, strike, title)
                                    st.altair_chart(chart, use_container_width=True)
                            
                            st.divider()
                    else:
                        st.warning("Could not fetch Bloomberg data. Check connection and ensure Terminal is running.")
            else:
                st.info("Select trades to view charts")
        else:
            st.info("Upload trade data to view charts")
    
    else:
        st.info("Add vanilla options and/or exotic trades manually to begin")
        
        # Show manual entry instructions
        with st.expander("How to Use"):
            st.write("**1. Add Vanilla Options:** Use the 'Add Vanilla Option' form in the sidebar")
            st.write("**2. Add Exotic Trades:** Use the 'Add Exotic Trade' form in the sidebar") 
            st.write("**3. MARS ID:** Optional field for Bloomberg integration and reconciliation")
            st.write("**4. Charts:** Select trades from the dropdown to view Bloomberg price charts")

def test_bloomberg_standalone():
    """Standalone test function for Bloomberg API."""
    try:
        import blpapi
        print("✅ blpapi imported successfully")

        # Test session
        session = get_bloomberg_session()
        if session:
            print("✅ Bloomberg session created")

            # Test SPY data
            spy_data = get_bloomberg_history(['SPY US Equity'])
            if not spy_data.empty:
                print(f"✅ Successfully fetched {len(spy_data)} SPY records")
                print("Latest SPY price:", spy_data.iloc[-1]['price'])
                return True
            else:
                print("⚠️ No SPY data returned")
                return False
        else:
            print("❌ Failed to create session")
            return False
    except ImportError:
        print("❌ blpapi not installed")
        print("Install with: pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Create standalone test script
BLOOMBERG_TEST_SCRIPT = '''
import sys
sys.path.append(".")

# Import the functions from app.py
from app import test_bloomberg_standalone

if __name__ == "__main__":
    print("🔍 Bloomberg API Test")
    print("=" * 50)
    success = test_bloomberg_standalone()
    print("=" * 50)
    if success:
        print("✅ Bloomberg API test PASSED!")
        sys.exit(0)
    else:
        print("❌ Bloomberg API test FAILED!")
        sys.exit(1)
'''

if __name__ == "__main__":
    # Run standalone test if called directly
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running Bloomberg API test...")
        success = test_bloomberg_standalone()
        sys.exit(0 if success else 1)
    else:
        main()