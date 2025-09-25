#!/usr/bin/env python3
"""
Simple script to get current SPY price using Bloomberg client.
This demonstrates the Bloomberg API integration.
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_spy_price():
    """Get current SPY price using Bloomberg client."""
    print("📈 Getting Current SPY Price")
    print("=" * 40)
    
    try:
        # Try real Bloomberg client first
        try:
            from utils.bloomberg_client import get_current_price, get_hist_data
            print("Using real Bloomberg API...")
            
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
                else:
                    print("⚠️ No historical data available")
            else:
                print("❌ Could not get current price")
                return False
                
        except (ImportError, Exception) as e:
            print(f"Bloomberg API not available ({e}), using mock data...")
            from utils.bloomberg_client_mock import get_current_price, get_hist_data
            
            # Get current price
            current_price = get_current_price("SPY US Equity")
            if current_price:
                print(f"✅ Mock SPY Price: ${current_price:.2f}")
                
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
                else:
                    print("⚠️ No historical data available")
            else:
                print("❌ Could not get mock current price")
                return False
        
        print("\n" + "=" * 40)
        print("✅ Bloomberg integration is working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Bloomberg API Test - SPY Price")
    print("Make sure Bloomberg Terminal is running for real data...")
    print()
    
    success = get_spy_price()
    
    if success:
        print("\n🎉 SUCCESS!")
        print("The Bloomberg integration is working correctly.")
        if "mock" in str(sys.modules.get('utils.bloomberg_client_mock', '')):
            print("Note: Using mock data. Install Bloomberg Terminal for real data.")
    else:
        print("\n❌ FAILED!")
        print("Check Bloomberg Terminal installation and API setup.")
