#!/usr/bin/env python3
"""
Test script for Mock Bloomberg API integration.
This tests the functionality when Bloomberg API is not available.
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_mock_bloomberg():
    """Test the mock Bloomberg client functions."""
    print("🔍 Testing Mock Bloomberg API Integration")
    print("=" * 50)
    
    try:
        # Test imports
        print("1. Testing mock imports...")
        from utils.bloomberg_client_mock import get_hist_data, get_current_price
        print("   ✅ Successfully imported mock Bloomberg client")
        
        # Test historical data
        print("\n2. Testing mock historical data fetch...")
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        df = get_hist_data("SPY US Equity", ["PX_LAST"], 
                          start_date.strftime("%Y-%m-%d"), 
                          end_date.strftime("%Y-%m-%d"))
        
        if not df.empty:
            print(f"   ✅ Successfully generated {len(df)} mock records for SPY US Equity")
            print(f"   📊 Data columns: {list(df.columns)}")
            print(f"   📅 Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"   💰 Price range: ${df['price'].min():.2f} to ${df['price'].max():.2f}")
        else:
            print("   ❌ No mock data generated")
            return False
        
        # Test current price
        print("\n3. Testing mock current price fetch...")
        current_price = get_current_price("SPY US Equity")
        if current_price:
            print(f"   ✅ Mock current SPY price: ${current_price:.2f}")
        else:
            print("   ❌ Could not generate mock current price")
            return False
        
        # Test other tickers
        print("\n4. Testing other tickers...")
        test_tickers = ["CDX HY CDSI S44 5Y PRC Corp", "SPX Index", "CLA Comdty"]
        for ticker in test_tickers:
            price = get_current_price(ticker)
            if price:
                print(f"   ✅ {ticker}: ${price:.2f}")
            else:
                print(f"   ❌ {ticker}: Failed")
        
        print("\n" + "=" * 50)
        print("✅ Mock Bloomberg API integration test PASSED!")
        print("📝 Note: This is using mock data. For real Bloomberg data:")
        print("   1. Install Bloomberg Terminal")
        print("   2. Install blpapi: pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi")
        print("   3. Replace mock imports with real Bloomberg client")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Mock Bloomberg Integration Test")
    print("This tests the functionality with simulated data...")
    print()
    
    success = test_mock_bloomberg()
    
    if success:
        print("\n🎉 MOCK TEST PASSED!")
        print("The Bloomberg integration structure is working correctly.")
        print("To use real Bloomberg data, follow the setup instructions.")
        sys.exit(0)
    else:
        print("\n❌ MOCK TEST FAILED!")
        sys.exit(1)
