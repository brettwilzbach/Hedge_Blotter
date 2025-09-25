"""
Mock Bloomberg client for testing when Bloomberg API is not available.
This simulates the Bloomberg API responses for development and testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

def get_hist_data(ticker: str, flds: List[str], start: str, end: str) -> pd.DataFrame:
    """
    Mock historical data fetch - simulates Bloomberg API response.
    """
    try:
        logger.info(f"Mock: Fetching Bloomberg data for {ticker} from {start} to {end}")
        
        # Generate mock data
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        
        # Create date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate realistic price data based on ticker
        if "SPY" in ticker.upper():
            base_price = 450.0
            volatility = 0.02
        elif "CDX" in ticker.upper():
            base_price = 100.0
            volatility = 0.01
        elif "SPX" in ticker.upper():
            base_price = 4500.0
            volatility = 0.02
        else:
            base_price = 100.0
            volatility = 0.015
        
        # Generate random walk price data
        np.random.seed(42)  # For reproducible results
        returns = np.random.normal(0, volatility, len(date_range))
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
        
        # Create DataFrame
        df = pd.DataFrame({
            'date': date_range,
            'price': prices
        })
        
        logger.info(f"Mock: Successfully generated {len(df)} records for {ticker}")
        return df
        
    except Exception as e:
        logger.error(f"Mock: Error generating data for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_current_price(ticker: str) -> Optional[float]:
    """
    Mock current price fetch - simulates Bloomberg API response.
    """
    try:
        # Generate mock current price based on ticker
        if "SPY" in ticker.upper():
            base_price = 450.0
        elif "CDX" in ticker.upper():
            base_price = 100.0
        elif "SPX" in ticker.upper():
            base_price = 4500.0
        else:
            base_price = 100.0
        
        # Add some random variation
        np.random.seed(int(datetime.now().timestamp()) % 1000)
        variation = np.random.normal(0, 0.01)
        current_price = base_price * (1 + variation)
        
        logger.info(f"Mock: Current price for {ticker}: ${current_price:.2f}")
        return current_price
        
    except Exception as e:
        logger.error(f"Mock: Error generating current price for {ticker}: {str(e)}")
        return None

def get_greeks(ticker: str) -> pd.DataFrame:
    """
    Mock Greeks fetch - simulates Bloomberg API response.
    """
    try:
        # Mock Greeks data
        greeks_data = {
            'DELTA': 0.5,
            'GAMMA': 0.01,
            'VEGA': 0.1,
            'THETA': -0.05,
            'RHO': 0.02
        }
        
        df = pd.DataFrame([greeks_data])
        logger.info(f"Mock: Generated Greeks for {ticker}")
        return df
        
    except Exception as e:
        logger.error(f"Mock: Error generating Greeks for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_market_value(mars_id: str) -> Optional[float]:
    """
    Mock Market Value fetch - simulates Bloomberg API response.
    """
    try:
        # Mock market value
        np.random.seed(hash(mars_id) % 1000)
        market_value = np.random.uniform(100000, 1000000)
        
        logger.info(f"Mock: Market value for MARS ID {mars_id}: ${market_value:,.2f}")
        return market_value
        
    except Exception as e:
        logger.error(f"Mock: Error generating market value for MARS ID {mars_id}: {str(e)}")
        return None
