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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Bloomberg client
from utils.bloomberg_client_simple import get_hist_data, get_current_price, BLOOMBERG_AVAILABLE

# Import data storage
from utils.data_storage import (
    save_live_trades, save_trade_history, 
    load_live_trades, load_trade_history,
    backup_data, get_data_summary
)

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
    page_title="Cannae Hedge Blotter",
    page_icon="📘",
    layout="wide",
)

st.markdown(
    f"""
    <style>
        .metric-label {{ color: {PRIMARY_COLOR}; font-weight: 600; }}
        .chart-container {{ margin: 10px 0; }}
        .recon-section {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        
        /* Disable Enter key submission for forms */
        .stForm input[type="text"],
        .stForm input[type="number"],
        .stForm textarea,
        .stForm select {{
            pointer-events: auto;
        }}
        
        .stForm input[type="text"]:focus,
        .stForm input[type="number"]:focus,
        .stForm textarea:focus,
        .stForm select:focus {{
            outline: 2px solid {PRIMARY_COLOR};
            outline-offset: 2px;
        }}
        
        /* Hide the "Press Enter to Submit Form" message */
        .stForm .stMarkdown {{
            display: none;
        }}
        
        /* Ensure form elements don't submit on Enter */
        .stForm form {{
            pointer-events: auto;
        }}
    </style>
    
    <script>
    // Disable Enter key submission for all forms
    document.addEventListener('keydown', function(event) {{
        if (event.key === 'Enter') {{
            // Check if the target is inside a form
            const form = event.target.closest('form');
            if (form) {{
                // Prevent default Enter behavior
                event.preventDefault();
                event.stopPropagation();
                return false;
            }}
        }}
    }});
    </script>
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
    if not BLOOMBERG_AVAILABLE:
        return None
        
    try:
        import blpapi  # type: ignore
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
    if not tickers or not BLOOMBERG_AVAILABLE:
        return pd.DataFrame()
    
    try:
        import blpapi  # type: ignore
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
# Helper Functions
# ------------------------------

def auto_save_data():
    """Auto-save all data to files."""
    try:
        save_live_trades(st.session_state.manual_vanilla_trades, st.session_state.manual_trades)
        save_trade_history(st.session_state.trade_history)
    except Exception as e:
        st.warning(f"Could not save data: {str(e)}")

# ------------------------------
# Main Application
# ------------------------------

def test_bloomberg_connection():
    """Test Bloomberg API connection with SPY data."""
    st.header("🔍 Bloomberg API Test")

    if not BLOOMBERG_AVAILABLE:
        st.warning("⚠️ Bloomberg API not available")
        st.info("Bloomberg functionality requires proper installation. The app will work without it, but Bloomberg charts and data will not be available.")
        st.code("pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi", language="bash")
        return

    if st.button("Test Bloomberg Connection", type="primary"):
        with st.spinner("Testing Bloomberg connection..."):
            try:
                # Test basic import
                import blpapi  # type: ignore
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
    
    if not BLOOMBERG_AVAILABLE:
        st.warning("⚠️ Bloomberg API not available")
        st.info("Bloomberg functionality requires proper installation. Please install the Bloomberg API to use this feature.")
        st.code("pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi", language="bash")
        return
    
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
    # Header with logo and title
    col1, col2 = st.columns([1, 3])
    
    with col1:
        try:
            st.image("assets/cannae-logo.png", width=120)
        except:
            # Fallback if logo file not found
            st.markdown("""
            <div style="width: 120px; height: 120px; background: linear-gradient(135deg, #45606B, #90A4AE); 
                        border-radius: 8px; display: flex; align-items: center; justify-content: center; 
                        color: white; font-weight: bold; font-size: 36px;">C</div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.title("Cannae Hedge Blotter")
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
    
    # Welcome section
    st.markdown("---")
    st.subheader("📊 Trade Management")
    st.write("Use the sidebar to add new trades or manage existing ones.")
    
    # Optional Bloomberg connection test (only show if user wants to test)
    with st.expander("🔍 Bloomberg API Test (Optional)", expanded=False):
        test_bloomberg_connection()

    # Removed file uploads - everything is manual entry now
    
    # Data Management
    with st.sidebar.expander("💾 Data Management"):
        # Show data summary
        try:
            summary = get_data_summary()
            st.write(f"**Live Trades:** {summary.get('total_live_trades', 0)}")
            st.write(f"**Trade History:** {summary.get('trade_history_count', 0)}")
        except:
            st.write("**Data:** Loading...")
        
        # Manual save button
        if st.button("💾 Save Data Now"):
            auto_save_data()
            st.success("Data saved!")
        
        # Backup button
        if st.button("📦 Create Backup"):
            if backup_data():
                st.success("Backup created!")
            else:
                st.error("Backup failed!")
        
        # Data location info
        st.caption("Data is automatically saved to CSV files in the `data/` folder")
    
    # Bloomberg connection settings
    with st.sidebar.expander("Bloomberg Connection"):
        st.write("Desktop API works with defaults")
        bbg_host = st.text_input("Host (optional)", value="")
        bbg_port = st.number_input("Port", value=8194, step=1)
    
    # Trade Entry Forms
    st.sidebar.header("Trade Entry")
    
    # Vanilla Options Entry Form
    with st.sidebar.expander("Add Vanilla Option", expanded=True):
        with st.form("vanilla_entry_form"):
            vanilla_trade_id = st.text_input("Trade ID*", placeholder="EX-SPY-001", key="vanilla_trade_id")
            vanilla_trade_date = st.date_input("Trade Date*", value=datetime.now().date(), key="vanilla_trade_date")
            vanilla_book = st.selectbox("Book", ["Hedge", "Trading", "Prop"], key="vanilla_book")
            vanilla_strategy = st.text_input("Strategy", placeholder="Index Options", key="vanilla_strategy")
            vanilla_side = st.selectbox("Side", ["Long", "Short"], key="vanilla_side")
            
            vanilla_col1, vanilla_col2 = st.columns(2)
            with vanilla_col1:
                vanilla_notional = st.number_input("Notional (mm)", min_value=0.0, step=0.1, format="%.1f", key="vanilla_notional")
            with vanilla_col2:
                vanilla_contracts = st.number_input("Contracts", min_value=0, step=1, format="%d", key="vanilla_contracts")
            
            # Either/or validation message
            if vanilla_notional <= 0 and vanilla_contracts <= 0:
                st.warning("Please enter either Notional (mm) or Contracts")
            
            vanilla_col3, vanilla_col4 = st.columns(2)
            with vanilla_col3:
                vanilla_expiry = st.date_input("Expiry*", value=datetime.now().date() + timedelta(days=30), key="vanilla_expiry")
            with vanilla_col4:
                vanilla_payoff_type = st.selectbox("Payoff Type", ["Call", "Put", "Call Spread", "Put Spread", "Vanilla"], key="vanilla_payoff_type")
            
            vanilla_index = st.text_input("Index/Ticker*", placeholder="SPY US Equity", key="vanilla_index")
            vanilla_bbg_ticker = st.text_input("Bloomberg Ticker*", placeholder="SPY US Equity", key="vanilla_bbg_ticker")
            
            # Strike fields - show second strike for spreads
            if vanilla_payoff_type in ["Call Spread", "Put Spread"]:
                vanilla_col_strike1, vanilla_col_strike2 = st.columns(2)
                with vanilla_col_strike1:
                    vanilla_strike = st.number_input("Long Strike*", step=0.01, format="%.2f", key="vanilla_strike", help="Strike price for the long leg")
                with vanilla_col_strike2:
                    vanilla_strike2 = st.number_input("Short Strike*", step=0.01, format="%.2f", key="vanilla_strike2", help="Strike price for the short leg")
            else:
                vanilla_strike = st.number_input("Strike*", step=0.01, format="%.2f", key="vanilla_strike")
                vanilla_strike2 = None
            
            vanilla_col5, vanilla_col6 = st.columns(2)
            with vanilla_col5:
                vanilla_cost_bp = st.number_input("Cost (bp/pt)", min_value=0.0, step=0.1, format="%.1f", key="vanilla_cost_bp")
            with vanilla_col6:
                vanilla_cost_usd = st.number_input("Cost ($)", min_value=0.0, step=1000.0, format="%.0f", key="vanilla_cost_usd")
            
            vanilla_mars_id = st.text_input("MARS ID (for Bloomberg integration)", placeholder="Optional MARS reference", key="vanilla_mars_id")
            vanilla_notes = st.text_area("Notes", placeholder="Optional notes about this trade", key="vanilla_notes", height=60)
            
            # Radio button for submission instead of auto-submit on enter
            vanilla_submitted = st.form_submit_button("Add Vanilla Trade", type="primary")
            
            if vanilla_submitted:
                # Show warnings for missing required fields but don't block submission
                warnings = []
                if not vanilla_trade_id:
                    warnings.append("Trade ID is recommended")
                if not vanilla_index:
                    warnings.append("Index/Ticker is recommended")
                if not vanilla_bbg_ticker:
                    warnings.append("Bloomberg Ticker is recommended")
                if vanilla_strike == 0:
                    warnings.append("Strike should be non-zero")
                if vanilla_payoff_type in ["Call Spread", "Put Spread"] and vanilla_strike2 == 0:
                    warnings.append("Short Strike should be non-zero for spreads")
                if vanilla_notional <= 0 and vanilla_contracts <= 0:
                    warnings.append("Either Notional or Contracts should be > 0")
                
                if warnings:
                    for warning in warnings:
                        st.warning(warning)
                
                # Always allow submission - user can fix later if needed
                new_vanilla_trade = {
                        'trade_date': vanilla_trade_date,
                        'trade_id': vanilla_trade_id,
                        'book': vanilla_book,
                        'strategy': vanilla_strategy,
                        'side': vanilla_side,
                        'index': vanilla_index,
                        'bbg_ticker': vanilla_bbg_ticker,
                        'notional_mm': vanilla_notional,
                        'contracts': vanilla_contracts if vanilla_contracts > 0 else None,
                        'expiry': vanilla_expiry,
                        'payoff_type': vanilla_payoff_type,
                        'strike': vanilla_strike,
                        'strike2': vanilla_strike2 if vanilla_strike2 else None,
                        'cost_bp': vanilla_cost_bp if vanilla_cost_bp > 0 else None,
                        'cost_usd': vanilla_cost_usd if vanilla_cost_usd > 0 else None,
                        'mars_id': vanilla_mars_id if vanilla_mars_id else None,
                        'notes': vanilla_notes if vanilla_notes else None,
                        'source': 'Manual',
                        'trade_type': 'Vanilla'
                    }
                    
                if 'manual_vanilla_trades' not in st.session_state:
                    st.session_state.manual_vanilla_trades = []
                st.session_state.manual_vanilla_trades.append(new_vanilla_trade)
                
                # Auto-save data
                auto_save_data()
                
                st.success(f"Added vanilla trade {vanilla_trade_id}")
                st.rerun()
    
    # Exotics Entry Form - moved to main area for more horizontal space
    st.sidebar.markdown("---")
    st.sidebar.caption("Exotic trades form moved to main area below for better layout")
    
    # Initialize manual trades stores and load existing data
    if 'manual_trades' not in st.session_state:
        st.session_state.manual_trades = []
    if 'manual_vanilla_trades' not in st.session_state:
        st.session_state.manual_vanilla_trades = []
    if 'trade_history' not in st.session_state:
        st.session_state.trade_history = []
    
    # Load existing data on first run
    if 'data_loaded' not in st.session_state:
        try:
            vanilla_trades, exotic_trades = load_live_trades()
            trade_history = load_trade_history()
            
            st.session_state.manual_vanilla_trades = vanilla_trades
            st.session_state.manual_trades = exotic_trades
            st.session_state.trade_history = trade_history
            st.session_state.data_loaded = True
            
            if vanilla_trades or exotic_trades or trade_history:
                st.success(f"📁 Loaded existing data: {len(vanilla_trades)} vanilla, {len(exotic_trades)} exotic, {len(trade_history)} history")
        except Exception as e:
            st.warning(f"Could not load existing data: {str(e)}")
            st.session_state.data_loaded = True
    
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
    
    
    # Exotic Trades Entry Form - moved below vanilla for better layout
    with st.sidebar.expander("Add Exotic Trade", expanded=False):
        with st.form("exotic_entry_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Basic Info")
                trade_id = st.text_input("Trade ID*", placeholder="EX-DD-001", key="exotic_trade_id")
                trade_date = st.date_input("Trade Date*", value=datetime.now().date(), key="exotic_trade_date")
                book = st.selectbox("Book", ["Hedge", "Trading", "Prop"], key="exotic_book")
                strategy = st.text_input("Strategy", placeholder="Cross-Asset Digitals", key="exotic_strategy")
                side = st.selectbox("Side", ["Long", "Short"], key="exotic_side")
                
                notional_mm = st.number_input("Notional (mm)*", min_value=0.0, step=0.1, format="%.1f", key="exotic_notional")
                expiry = st.date_input("Expiry*", value=datetime.now().date() + timedelta(days=90), key="exotic_expiry")
            
            with col2:
                st.subheader("Index 1")
                index1 = st.text_input("Index 1*", placeholder="SPX Index", key="exotic_index1")
                cond1 = st.selectbox("Condition 1", ["<=", ">=", "<", ">", "=="], key="exotic_cond1")
                strike1 = st.number_input("Strike 1*", step=0.01, format="%.2f", key="exotic_strike1")
                
                st.subheader("Index 2")
                index2 = st.text_input("Index 2*", placeholder="CLA Comdty", key="exotic_index2")
                cond2 = st.selectbox("Condition 2", ["<=", ">=", "<", ">", "=="], key="exotic_cond2")
                strike2 = st.number_input("Strike 2*", step=0.01, format="%.2f", key="exotic_strike2")
                
                logic = st.selectbox("Logic", ["AND", "OR"], key="exotic_logic")
            
            with col3:
                st.subheader("Pricing")
                cost_bp = st.number_input("Cost (bp)", min_value=0.0, step=0.1, format="%.1f", key="exotic_cost_bp")
                cost_usd = st.number_input("Cost ($)", min_value=0.0, step=1000.0, format="%.0f", key="exotic_cost_usd")
            
            # Full width fields
            mars_id = st.text_input("MARS ID (for Bloomberg integration)", placeholder="Optional MARS reference", key="exotic_mars_id")
            notes = st.text_area("Notes", placeholder="Optional notes about this trade", height=60, key="exotic_notes")

            # Submit button
            submitted = st.form_submit_button("Add Exotic Trade", type="primary")

            if submitted:
                # Show warnings for missing required fields but don't block submission
                warnings = []
                if not trade_id:
                    warnings.append("Trade ID is recommended")
                if not trade_date:
                    warnings.append("Trade Date is recommended")
                if not notional_mm:
                    warnings.append("Notional (mm) is recommended")
                if not index1:
                    warnings.append("Index 1 is recommended")
                if not strike1:
                    warnings.append("Strike 1 is recommended")
                if not index2:
                    warnings.append("Index 2 is recommended")
                if not strike2:
                    warnings.append("Strike 2 is recommended")
                
                if warnings:
                    for warning in warnings:
                        st.warning(warning)
                
                # Always allow submission - user can fix later if needed
                new_trade = {
                    'trade_date': trade_date,
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
                    'notes': notes if notes else None,
                    'source': 'Manual',
                    'payoff_type': 'Dual Digital',
                    'trade_type': 'Exotic'
                }

                if 'manual_trades' not in st.session_state:
                    st.session_state.manual_trades = []
                st.session_state.manual_trades.append(new_trade)
                
                # Auto-save data
                auto_save_data()
                
                st.success(f"Added exotic trade {trade_id}")
                st.rerun()
    
    # Master Portfolio Spreadsheet View
    st.subheader("📊 Live Trades - Portfolio View")
    
    # Get all live trades from session state
    all_live_trades = []
    if hasattr(st.session_state, 'manual_vanilla_trades') and st.session_state.manual_vanilla_trades:
        all_live_trades.extend(st.session_state.manual_vanilla_trades)
    if hasattr(st.session_state, 'manual_exotic_trades') and st.session_state.manual_exotic_trades:
        all_live_trades.extend(st.session_state.manual_exotic_trades)
    
    if all_live_trades:
        # Create master spreadsheet with all trades
        portfolio_data = []
        
        for i, trade in enumerate(all_live_trades):
            if trade.get('trade_type') == 'Vanilla' or trade.get('payoff_type') in ['Call', 'Put', 'Straddle', 'Strangle']:
                portfolio_data.append({
                    'Trade ID': trade.get('trade_id', f'V{i+1}'),
                    'Type': 'Vanilla',
                    'Side': trade.get('side', 'N/A'),
                    'Underlying': trade.get('bbg_ticker', trade.get('index1', 'N/A')),
                    'Strike': trade.get('strike', trade.get('strike1', 'N/A')),
                    'Expiry': trade.get('expiry', 'N/A'),
                    'Notional (mm)': trade.get('notional_mm', 0),
                    'Contracts': trade.get('contracts', 0),
                    'Cost ($)': trade.get('cost_usd', 0),
                    'Delta': trade.get('delta', 0) or 0,
                    'Gamma': trade.get('gamma', 0) or 0,
                    'Theta': trade.get('theta', 0) or 0,
                    'Vega': trade.get('vega', 0) or 0,
                    'Market Value ($)': trade.get('market_value', 0) or 0,
                    'Mark ($)': trade.get('mark', 0) or 0,
                    'MTD P&L ($)': trade.get('mtd_pnl', 0) or 0,
                    'Inception P&L ($)': trade.get('inception_pnl', 0) or 0,
                    'Book': trade.get('book', 'N/A')
                })
            elif trade.get('trade_type') == 'Exotic' or trade.get('payoff_type') == 'Dual Digital':
                portfolio_data.append({
                    'Trade ID': trade.get('trade_id', f'E{i+1}'),
                    'Type': 'Exotic',
                    'Side': trade.get('side', 'N/A'),
                    'Underlying': f"{trade.get('index1', 'N/A')} vs {trade.get('index2', 'N/A')}",
                    'Strike': f"{trade.get('strike1', 'N/A')} / {trade.get('strike2', 'N/A')}",
                    'Expiry': trade.get('expiry', 'N/A'),
                    'Notional (mm)': trade.get('notional_mm', 0),
                    'Contracts': 'N/A',
                    'Cost ($)': trade.get('cost_usd', 0),
                    'Delta': trade.get('delta', 0) or 0,
                    'Gamma': trade.get('gamma', 0) or 0,
                    'Theta': trade.get('theta', 0) or 0,
                    'Vega': trade.get('vega', 0) or 0,
                    'Market Value ($)': trade.get('market_value', 0) or 0,
                    'Mark ($)': trade.get('mark', 0) or 0,
                    'MTD P&L ($)': trade.get('mtd_pnl', 0) or 0,
                    'Inception P&L ($)': trade.get('inception_pnl', 0) or 0,
                    'Book': trade.get('book', 'N/A')
                })
        
        if portfolio_data:
            # Create DataFrame
            df = pd.DataFrame(portfolio_data)
            
            # Add totals row
            totals_row = {
                'Trade ID': 'TOTAL',
                'Type': '',
                'Side': '',
                'Underlying': '',
                'Strike': '',
                'Expiry': '',
                'Notional (mm)': df['Notional (mm)'].sum(),
                'Contracts': df['Contracts'].sum() if df['Contracts'].dtype != 'object' else 'N/A',
                'Cost ($)': df['Cost ($)'].sum(),
                'Delta': df['Delta'].sum(),
                'Gamma': df['Gamma'].sum(),
                'Theta': df['Theta'].sum(),
                'Vega': df['Vega'].sum(),
                'Market Value ($)': df['Market Value ($)'].sum(),
                'Mark ($)': df['Mark ($)'].sum(),
                'MTD P&L ($)': df['MTD P&L ($)'].sum(),
                'Inception P&L ($)': df['Inception P&L ($)'].sum(),
                'Book': ''
            }
            
            # Add totals row to DataFrame
            df_with_totals = pd.concat([df, pd.DataFrame([totals_row])], ignore_index=True)
            
            # Display the master spreadsheet
            st.dataframe(
                df_with_totals,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Refresh button
            col_refresh, col_spacer = st.columns([1, 4])
            with col_refresh:
                if st.button("🔄 Refresh All Market Data", type="secondary"):
                    st.info("Market data refresh would be implemented here with Bloomberg API")
    else:
        st.info("No live trades found. Add some trades using the forms above.")
    
    # Legacy data display (if any)
    if not vanilla_data.empty or not exotics_data.empty:
        st.subheader("📈 Legacy Data")
        
        # Vanilla Trades - Full Width for better visibility
        if not vanilla_data.empty:
            st.subheader("Vanilla Trades")
            st.dataframe(vanilla_data, use_container_width=True, height=400)
        
        # Exotic Trades - Below vanilla
        if not exotics_data.empty:
            st.subheader("Exotic Trades")
            st.dataframe(exotics_data, use_container_width=True, height=300)
                
        # Note: Individual trade management is now handled in the master spreadsheet above
                            
                            with col_market:
                                # Get market data values
                                delta_val = trade.get('delta', 0) or 0
                                gamma_val = trade.get('gamma', 0) or 0
                                theta_val = trade.get('theta', 0) or 0
                                vega_val = trade.get('vega', 0) or 0
                                market_value_val = trade.get('market_value', 0) or 0
                                mark_val = trade.get('mark', 0) or 0
                                mtd_pnl_val = trade.get('mtd_pnl', 0) or 0
                                inception_pnl_val = trade.get('inception_pnl', 0) or 0
                                
                                # Create spreadsheet-style table
                                market_data = {
                                    'Greeks': ['Delta', 'Gamma', 'Theta', 'Vega'],
                                    'Values': [f"{delta_val:.2f}", f"{gamma_val:.2f}", f"{theta_val:.2f}", f"{vega_val:.2f}"],
                                    'P&L': ['Mkt Val', 'Mark', 'MTD', 'Total'],
                                    'P&L Values': [f"${market_value_val:,.0f}", f"${mark_val:,.0f}", f"${mtd_pnl_val:,.0f}", f"${inception_pnl_val:,.0f}"]
                                }
                                
                                # Display as a simple table
                                st.dataframe(
                                    pd.DataFrame(market_data),
                                    use_container_width=True,
                                    hide_index=True,
                                    height=100
                                )
                            
                            st.divider()
                            
                            # Management buttons
                            col_edit, col_unwind, col_expire, col_delete = st.columns(4)
                            
                            with col_edit:
                                if st.button(f"Edit", key=f"edit_vanilla_{i}"):
                                    st.session_state[f"edit_vanilla_trade_{i}"] = True
                            
                            with col_unwind:
                                if st.button(f"Unwind", key=f"unwind_vanilla_{i}"):
                                    st.session_state[f"unwind_vanilla_trade_{i}"] = True
                            
                            with col_expire:
                                if st.button(f"Expire", key=f"expire_vanilla_{i}"):
                                    # Move to trade history as expired worthless
                                    trade_copy = trade.copy()
                                    trade_copy['status'] = 'Expired Worthless'
                                    trade_copy['unwind_date'] = datetime.now().date()
                                    trade_copy['unwind_price'] = 0.0
                                    trade_copy['pnl_usd'] = -float(trade.get('cost_usd', 0)) if trade.get('cost_usd') else 0
                                    
                                    if 'trade_history' not in st.session_state:
                                        st.session_state.trade_history = []
                                    st.session_state.trade_history.append(trade_copy)
                                    
                                    del st.session_state.manual_vanilla_trades[i]
                                    auto_save_data()
                                    st.success(f"Marked trade {trade['trade_id']} as expired worthless")
                                    st.rerun()
                            
                            with col_delete:
                                if st.button(f"Delete", key=f"delete_vanilla_{i}"):
                                    del st.session_state.manual_vanilla_trades[i]
                                    auto_save_data()
                                    st.success(f"Deleted trade {trade['trade_id']}")
                                    st.rerun()
                            
                            # Unwind form
                            if st.session_state.get(f"unwind_vanilla_trade_{i}", False):
                                st.write("**Unwind Vanilla Trade**")
                                with st.form(f"unwind_vanilla_form_{i}"):
                                    unwind_vanilla_date = st.date_input("Unwind Date*", value=datetime.now().date(), key=f"unwind_vanilla_date_{i}")
                                    unwind_vanilla_price = st.number_input("Unwind Price*", step=0.01, format="%.2f", key=f"unwind_vanilla_price_{i}")
                                    unwind_vanilla_notes = st.text_area("Notes", placeholder="Optional notes about the unwind", key=f"unwind_vanilla_notes_{i}")
                                    
                                    unwind_vanilla_col_save, unwind_vanilla_col_cancel = st.columns(2)
                                    with unwind_vanilla_col_save:
                                        if st.form_submit_button("Unwind Trade"):
                                            # Calculate PnL
                                            original_cost = float(trade.get('cost_usd', 0)) if trade.get('cost_usd') else 0
                                            # Use contracts if available, otherwise use notional
                                            if trade.get('contracts'):
                                                unwind_value = unwind_vanilla_price * float(trade.get('contracts', 0))
                                            else:
                                                unwind_value = unwind_vanilla_price * float(trade.get('notional_mm', trade.get('notional_mm_or_contracts', 0)))
                                            pnl = unwind_value - original_cost
                                            
                                            # Move to trade history
                                            trade_copy = trade.copy()
                                            trade_copy['status'] = 'Unwound'
                                            trade_copy['unwind_date'] = unwind_vanilla_date
                                            trade_copy['unwind_price'] = unwind_vanilla_price
                                            trade_copy['unwind_value'] = unwind_value
                                            trade_copy['pnl_usd'] = pnl
                                            trade_copy['unwind_notes'] = unwind_vanilla_notes
                                            
                                            if 'trade_history' not in st.session_state:
                                                st.session_state.trade_history = []
                                            st.session_state.trade_history.append(trade_copy)
                                            
                                            del st.session_state.manual_vanilla_trades[i]
                                            auto_save_data()
                                            st.success(f"Unwound trade {trade['trade_id']} - PnL: ${pnl:,.2f}")
                                            st.rerun()
                                    
                                    with unwind_vanilla_col_cancel:
                                        if st.form_submit_button("Cancel"):
                                            st.session_state[f"unwind_vanilla_trade_{i}"] = False
                                            st.rerun()
                            
                            # Edit form
                            if st.session_state.get(f"edit_vanilla_trade_{i}", False):
                                st.write("**Edit Vanilla Trade**")
                                with st.form(f"edit_vanilla_form_{i}"):
                                    edit_trade_id = st.text_input("Trade ID*", value=trade['trade_id'], key=f"edit_id_{i}")
                                    edit_trade_date = st.date_input("Trade Date*", value=trade['trade_date'], key=f"edit_trade_date_{i}")
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
                                    
                                    edit_notes = st.text_area("Notes", value=trade.get('notes', ''), key=f"edit_notes_{i}", height=60)
                                    
                                    # Radio button for submission
                                    edit_submit_option = st.radio(
                                        "Ready to save changes?",
                                        ["No, keep editing", "Yes, save changes"],
                                        key=f"edit_submit_radio_{i}"
                                    )
                                    
                                    edit_col_save, edit_col_cancel = st.columns(2)
                                    with edit_col_save:
                                        if st.form_submit_button("Save Changes", disabled=(edit_submit_option != "Yes, save changes")):
                                            # Update the trade
                                            st.session_state.manual_trades[i] = {
                                                'trade_date': edit_trade_date,
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
                                                'notes': edit_notes if edit_notes else None,
                                                'source': 'Manual',
                                                'payoff_type': 'Dual Digital',
                                            }
                                            st.session_state[f"edit_trade_{i}"] = False
                                            auto_save_data()
                                            st.success(f"Updated trade {edit_trade_id}")
                                            st.rerun()
                                    
                                    with edit_col_cancel:
                                        if st.form_submit_button("Cancel"):
                                            st.session_state[f"edit_trade_{i}"] = False
                                            st.rerun()
        
        with col2:
            st.subheader("Manual Exotics Trades")
            if not exotics_data.empty:
                st.dataframe(exotics_data, height=300)
                
                # Add edit/delete functionality for exotic trades
                if st.session_state.manual_trades:
                    st.subheader("Manage Exotic Trades")
                    for i, trade in enumerate(st.session_state.manual_trades):
                        with st.expander(f"Trade {trade['trade_id']} - {trade['index1']} / {trade['index2']}"):
                            # Display basic trade info
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.write(f"**Side:** {trade['side']} | **Book:** {trade['book']}")
                                st.write(f"**Index1:** {trade['index1']} {trade['cond1']} {trade['strike1']}")
                            with col_info2:
                                st.write(f"**Index2:** {trade['index2']} {trade['cond2']} {trade['strike2']}")
                                st.write(f"**Logic:** {trade['logic']} | **Notional:** {trade['notional_mm']}mm")
                            
                            # Market Data Section (Spreadsheet Style)
                            col_refresh, col_market = st.columns([1, 4])
                            
                            with col_refresh:
                                if st.button("🔄", key=f"refresh_exotic_{i}", type="secondary", help="Refresh Market Data"):
                                    st.info("Market data refresh would be implemented here with Bloomberg API")
                            
                            with col_market:
                                # Get market data values
                                delta_val = trade.get('delta', 0) or 0
                                gamma_val = trade.get('gamma', 0) or 0
                                theta_val = trade.get('theta', 0) or 0
                                vega_val = trade.get('vega', 0) or 0
                                market_value_val = trade.get('market_value', 0) or 0
                                mark_val = trade.get('mark', 0) or 0
                                mtd_pnl_val = trade.get('mtd_pnl', 0) or 0
                                inception_pnl_val = trade.get('inception_pnl', 0) or 0
                                
                                # Create spreadsheet-style table
                                market_data = {
                                    'Greeks': ['Delta', 'Gamma', 'Theta', 'Vega'],
                                    'Values': [f"{delta_val:.2f}", f"{gamma_val:.2f}", f"{theta_val:.2f}", f"{vega_val:.2f}"],
                                    'P&L': ['Mkt Val', 'Mark', 'MTD', 'Total'],
                                    'P&L Values': [f"${market_value_val:,.0f}", f"${mark_val:,.0f}", f"${mtd_pnl_val:,.0f}", f"${inception_pnl_val:,.0f}"]
                                }
                                
                                # Display as a simple table
                                st.dataframe(
                                    pd.DataFrame(market_data),
                                    use_container_width=True,
                                    hide_index=True,
                                    height=100
                                )
                            
                            st.divider()
                            
                            # Management buttons
                            col_edit, col_unwind, col_expire, col_delete = st.columns(4)
                            
                            with col_edit:
                                if st.button(f"Edit", key=f"edit_exotic_{i}"):
                                    st.session_state[f"edit_exotic_trade_{i}"] = True
                            
                            with col_unwind:
                                if st.button(f"Unwind", key=f"unwind_exotic_{i}"):
                                    st.session_state[f"unwind_exotic_trade_{i}"] = True
                            
                            with col_expire:
                                if st.button(f"Expire", key=f"expire_exotic_{i}"):
                                    # Move to trade history as expired worthless
                                    trade_copy = trade.copy()
                                    trade_copy['status'] = 'Expired Worthless'
                                    trade_copy['unwind_date'] = datetime.now().date()
                                    trade_copy['unwind_price'] = 0.0
                                    trade_copy['pnl_usd'] = -float(trade.get('cost_usd', 0)) if trade.get('cost_usd') else 0
                                    
                                    if 'trade_history' not in st.session_state:
                                        st.session_state.trade_history = []
                                    st.session_state.trade_history.append(trade_copy)
                                    
                                    del st.session_state.manual_trades[i]
                                    auto_save_data()
                                    st.success(f"Marked trade {trade['trade_id']} as expired worthless")
                                    st.rerun()
                            
                            with col_delete:
                                if st.button(f"Delete", key=f"delete_exotic_{i}"):
                                    del st.session_state.manual_trades[i]
                                    auto_save_data()
                                    st.success(f"Deleted trade {trade['trade_id']}")
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
    
    # Trade History Section
    st.divider()
    st.subheader("📚 Trade History")
    
    # Initialize trade history if it doesn't exist
    if 'trade_history' not in st.session_state:
        st.session_state.trade_history = []
    
    if st.session_state.trade_history:
        # Summary metrics
        total_trades = len(st.session_state.trade_history)
        unwound_trades = len([t for t in st.session_state.trade_history if t.get('status') == 'Unwound'])
        expired_trades = len([t for t in st.session_state.trade_history if t.get('status') == 'Expired Worthless'])
        total_pnl = sum([t.get('pnl_usd', 0) for t in st.session_state.trade_history])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Trades", total_trades)
        with col2:
            st.metric("Unwound", unwound_trades)
        with col3:
            st.metric("Expired", expired_trades)
        with col4:
            st.metric("Total PnL", f"${total_pnl:,.2f}", delta=f"{total_pnl:+,.2f}")
        
        # Trade history table
        history_df = pd.DataFrame(st.session_state.trade_history)
        
        # Reorder columns for better display
        display_columns = ['trade_id', 'trade_date', 'status', 'unwind_date', 'book', 'strategy', 'side']
        if 'bbg_ticker' in history_df.columns:
            display_columns.extend(['bbg_ticker', 'payoff_type', 'strike'])
        else:
            display_columns.extend(['index1', 'index2', 'payoff_type'])
        display_columns.extend(['cost_usd', 'unwind_price', 'unwind_value', 'pnl_usd', 'unwind_notes'])
        
        # Only show columns that exist
        available_columns = [col for col in display_columns if col in history_df.columns]
        history_display = history_df[available_columns]
        
        st.dataframe(history_display, height=400, use_container_width=True)
        
        # PnL analysis
        if unwound_trades > 0:
            st.subheader("PnL Analysis")
            
            # PnL by book
            pnl_by_book = history_df.groupby('book')['pnl_usd'].sum().reset_index()
            pnl_by_book = pnl_by_book.sort_values('pnl_usd', ascending=False)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**PnL by Book**")
                st.dataframe(pnl_by_book, use_container_width=True)
            
            # PnL by strategy
            if 'strategy' in history_df.columns:
                pnl_by_strategy = history_df.groupby('strategy')['pnl_usd'].sum().reset_index()
                pnl_by_strategy = pnl_by_strategy.sort_values('pnl_usd', ascending=False)
                
                with col2:
                    st.write("**PnL by Strategy**")
                    st.dataframe(pnl_by_strategy, use_container_width=True)
            
            # PnL chart
            if len(history_df) > 1:
                pnl_chart_data = history_df.copy()
                pnl_chart_data['cumulative_pnl'] = pnl_chart_data['pnl_usd'].cumsum()
                pnl_chart_data['trade_number'] = range(1, len(pnl_chart_data) + 1)
                
                chart = alt.Chart(pnl_chart_data).mark_line(
                    color=PRIMARY_COLOR, 
                    strokeWidth=2
                ).encode(
                    x=alt.X('trade_number:Q', title='Trade Number'),
                    y=alt.Y('cumulative_pnl:Q', title='Cumulative PnL ($)'),
                    tooltip=['trade_id', 'pnl_usd', 'cumulative_pnl']
                ).properties(
                    width=800,
                    height=300,
                    title="Cumulative PnL Over Time"
                )
                
                st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No trades in history yet. Unwind or expire trades to see them here.")
        
        # Show manual entry instructions
        with st.expander("How to Use"):
            st.write("**1. Add Vanilla Options:** Use the 'Add Vanilla Option' form in the sidebar")
            st.write("**2. Add Exotic Trades:** Use the 'Add Exotic Trade' form in the sidebar") 
            st.write("**3. MARS ID:** Optional field for Bloomberg integration and reconciliation")
            st.write("**4. Charts:** Select trades from the dropdown to view Bloomberg price charts")
            st.write("**5. Unwind/Expire:** Use the Unwind or Expire buttons to close trades and move them to Trade History")
            st.write("**6. PnL Tracking:** Unwound trades automatically calculate PnL and show in Trade History section")

def test_bloomberg_standalone():
    """Standalone test function for Bloomberg API."""
    if not BLOOMBERG_AVAILABLE:
        print("❌ Bloomberg API not available")
        print("Install with: pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi")
        return False
        
    try:
        import blpapi  # type: ignore
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