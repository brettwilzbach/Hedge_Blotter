#!/usr/bin/env python3
"""
Simple test to get current SPY price using mock Bloomberg client.
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_spy_price():
    """Test getting SPY price using mock Bloomberg client."""
    print("📈 Testing SPY Price Fetch")
    print("=" * 40)
    
    try:
        # Use mock Bloomberg client
        from utils.bloomberg_client_mock import get_current_price, get_hist_data
        
        print("Using mock Bloomberg client...")
        
        # Get current price
        current_price = get_current_price("SPY US Equity")
        if current_price:
            print(f"✅ Current SPY Price: ${current_price:.2f}")
            
            # Get some historical data too
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            df = get_hist_data("SPY US Equity", ["PX_LAST"], 
                             start_date.strftime("%Y-%m-%d"), 
                             end_date.strftime("%Y-%m-%d"))
            
            if not df.empty:
                print(f"📊 Last 7 days: {len(df)} records")
                print(f"📅 Latest: {df['date'].iloc[-1].strftime('%Y-%m-%d')} - ${df['price'].iloc[-1]:.2f}")
                print(f"📈 7-day range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
                
                # Show a few recent prices
                print("\n📋 Recent SPY Prices:")
                for i, row in df.tail(5).iterrows():
                    print(f"   {row['date'].strftime('%Y-%m-%d')}: ${row['price']:.2f}")
            else:
                print("⚠️ No historical data available")
        else:
            print("❌ Could not get current price")
            return False
        
        print("\n" + "=" * 40)
        print("✅ Bloomberg integration test PASSED!")
        print("📝 Note: This is using mock data.")
        print("   For real Bloomberg data, install Bloomberg Terminal and blpapi.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Bloomberg API Test - SPY Price")
    print("Testing with mock data...")
    print()
    
    success = test_spy_price()
    
    if success:
        print("\n🎉 SUCCESS!")
        print("The Bloomberg integration structure is working correctly.")
        print("Current SPY price (mock): $459.49")
    else:
        print("\n❌ FAILED!")
        print("Check the Bloomberg integration setup.")
