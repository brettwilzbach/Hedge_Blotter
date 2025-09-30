import pandas as pd
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import Bloomberg libraries
BLOOMBERG_AVAILABLE = False
blp = None

try:
    import xbbg
    from xbbg import blp
    BLOOMBERG_AVAILABLE = True
    logger.info("Bloomberg libraries loaded successfully")
except ImportError as e:
    logger.warning(f"Bloomberg libraries not available: {e}")
    BLOOMBERG_AVAILABLE = False
    # Create a dummy blp object to prevent errors
    class DummyBlp:
        def bdh(self, *args, **kwargs):
            return pd.DataFrame()
        def bdp(self, *args, **kwargs):
            return pd.DataFrame()
    blp = DummyBlp()

def get_hist_data(ticker: str, flds: List[str], start: str, end: str) -> pd.DataFrame:
    """
    Fetch historical data from Bloomberg.
    
    Args:
        ticker: Bloomberg ticker (e.g. 'SPY US Equity')
        flds: list of fields (e.g. ['PX_LAST'])
        start: start date in YYYY-MM-DD format
        end: end date in YYYY-MM-DD format
    
    Returns:
        pandas DataFrame with historical data
    """
    if not BLOOMBERG_AVAILABLE:
        logger.warning("Bloomberg API not available - returning empty DataFrame")
        return pd.DataFrame()
        
    try:
        logger.info(f"Fetching Bloomberg data for {ticker} from {start} to {end}")
        
        # Use xbbg to fetch historical data
        df = blp.bdh(tickers=ticker, flds=flds, start_date=start, end_date=end)
        
        # Clean up the data format
        if not df.empty:
            # Reset index to make date a column
            df = df.reset_index()
            
            # Rename columns for consistency
            if 'date' in df.columns:
                df = df.rename(columns={'date': 'date'})
            
            # Ensure we have the expected structure
            if len(df.columns) > 1:
                # Get the price column (should be the last column)
                price_col = df.columns[-1]
                df = df.rename(columns={price_col: 'price'})
            
            logger.info(f"Successfully fetched {len(df)} records for {ticker}")
        else:
            logger.warning(f"No data returned for {ticker}")
            
        return df
        
    except Exception as e:
        logger.error(f"Error fetching Bloomberg data for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_current_price(ticker: str) -> Optional[float]:
    """
    Get current price for a ticker.
    
    Args:
        ticker: Bloomberg ticker (e.g. 'SPY US Equity')
    
    Returns:
        Current price as float, or None if error
    """
    if not BLOOMBERG_AVAILABLE:
        logger.warning("Bloomberg API not available - returning None")
        return None
        
    try:
        df = blp.bdp(tickers=ticker, flds=['PX_LAST'])
        if not df.empty:
            return float(df.iloc[0, 0])
        return None
    except Exception as e:
        logger.error(f"Error fetching current price for {ticker}: {str(e)}")
        return None

def get_greeks(ticker: str) -> pd.DataFrame:
    """
    Get Greeks for options (future extension).
    
    Args:
        ticker: Bloomberg ticker for options
    
    Returns:
        pandas DataFrame with Greeks data
    """
    if not BLOOMBERG_AVAILABLE:
        logger.warning("Bloomberg API not available - returning empty DataFrame")
        return pd.DataFrame()
        
    try:
        # This is a placeholder for future MARS integration
        # Will be implemented when extending to pull Greeks from MARS
        greeks_fields = ['DELTA', 'GAMMA', 'VEGA', 'THETA', 'RHO']
        df = blp.bdp(tickers=ticker, flds=greeks_fields)
        return df
    except Exception as e:
        logger.error(f"Error fetching Greeks for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_market_value(mars_id: str) -> Optional[float]:
    """
    Get Market Value from MARS via Bloomberg ID (future extension).
    
    Args:
        mars_id: MARS Bloomberg ID
    
    Returns:
        Market value as float, or None if error
    """
    if not BLOOMBERG_AVAILABLE:
        logger.warning("Bloomberg API not available - returning None")
        return None
        
    try:
        # This is a placeholder for future MARS integration
        # Will be implemented when extending to pull MV from MARS
        df = blp.bdp(tickers=mars_id, flds=['MV'])
        if not df.empty:
            return float(df.iloc[0, 0])
        return None
    except Exception as e:
        logger.error(f"Error fetching market value for MARS ID {mars_id}: {str(e)}")
        return None
