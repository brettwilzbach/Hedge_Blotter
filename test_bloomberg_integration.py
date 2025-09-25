#!/usr/bin/env python3
"""
Test script for Bloomberg API integration.
Run this to verify the Bloomberg setup is working correctly.
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_bloomberg_client():
    """Test the Bloomberg client functions."""
    print("🔍 Testing Bloomberg API Integration")
    print("=" * 50)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from utils.bloomberg_client import get_hist_data, get_current_price
        print("   ✅ Successfully imported Bloomberg client")
        
        # Test historical data
        print("\n2. Testing historical data fetch...")
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)  # Just 30 days for testing
        
        df = get_hist_data("SPY US Equity", ["PX_LAST"], 
                          start_date.strftime("%Y-%m-%d"), 
                          end_date.strftime("%Y-%m-%d"))
        
        if not df.empty:
            print(f"   ✅ Successfully fetched {len(df)} records for SPY US Equity")
            print(f"   📊 Data columns: {list(df.columns)}")
            print(f"   📅 Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"   💰 Price range: ${df['price'].min():.2f} to ${df['price'].max():.2f}")
        else:
            print("   ⚠️ No data returned for SPY US Equity")
            print("   This could mean Bloomberg Terminal is not running")
            return False
        
        # Test current price
        print("\n3. Testing current price fetch...")
        current_price = get_current_price("SPY US Equity")
        if current_price:
            print(f"   ✅ Current SPY price: ${current_price:.2f}")
        else:
            print("   ⚠️ Could not fetch current price")
        
        print("\n" + "=" * 50)
        print("✅ Bloomberg API integration test PASSED!")
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("   Make sure to install: pip install blpapi xbbg")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   Make sure Bloomberg Terminal is running")
        return False

def test_streamlit_app():
    """Test that the Streamlit app can be imported."""
    print("\n4. Testing Streamlit app import...")
    try:
        import app
        print("   ✅ Successfully imported main app")
        return True
    except Exception as e:
        print(f"   ❌ Error importing app: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Bloomberg Integration Test")
    print("Make sure Bloomberg Terminal is running before proceeding...")
    print()
    
    # Test Bloomberg client
    bloomberg_success = test_bloomberg_client()
    
    # Test app import
    app_success = test_streamlit_app()
    
    print("\n" + "=" * 50)
    if bloomberg_success and app_success:
        print("🎉 ALL TESTS PASSED!")
        print("You can now run: streamlit run app.py")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        if not bloomberg_success:
            print("- Bloomberg API integration needs attention")
        if not app_success:
            print("- App import failed")
        sys.exit(1)
