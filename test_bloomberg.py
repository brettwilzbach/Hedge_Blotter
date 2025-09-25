#!/usr/bin/env python3
"""
Standalone Bloomberg API Test Script
Tests the Bloomberg API connection and fetches SPY data
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path to import from app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_bloomberg_import():
    """Test if blpapi can be imported."""
    try:
        import blpapi
        print("✅ blpapi imported successfully")
        return True, blpapi
    except ImportError as e:
        print(f"❌ blpapi import failed: {e}")
        print("\nTo install Bloomberg API:")
        print("1. Download Bloomberg C++ SDK from: https://www.bloomberg.com/professional/api-library/")
        print("2. Install the C++ SDK on your system")
        print("3. Set BLPAPI_ROOT environment variable")
        print("4. Run: pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi")
        return False, None

def test_bloomberg_session(blpapi):
    """Test Bloomberg session creation."""
    try:
        options = blpapi.SessionOptions()
        options.setServerHost("localhost")
        options.setServerPort(8194)

        session = blpapi.Session(options)
        if not session.start():
            print("❌ Failed to start Bloomberg session")
            print("Make sure Bloomberg Terminal is running and API is configured")
            return None

        if not session.openService("//blp/refdata"):
            print("❌ Failed to open Bloomberg reference data service")
            session.stop()
            return None

        print("✅ Bloomberg session created successfully")
        return session

    except Exception as e:
        print(f"❌ Session creation failed: {e}")
        return None

def test_spy_data(session, blpapi):
    """Test fetching SPY data."""
    try:
        service = session.getService("//blp/refdata")
        request = service.createRequest("HistoricalDataRequest")

        # Add SPY security
        securities = request.getElement("securities")
        securities.appendValue("SPY US Equity")

        # Add price field
        fields = request.getElement("fields")
        fields.appendValue("PX_LAST")

        # Set date range (1 year)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        request.set("startDate", start_date.strftime("%Y%m%d"))
        request.set("endDate", end_date.strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")

        # Send request
        session.sendRequest(request)

        # Process response
        data = []
        timeout_ms = 5000

        while True:
            event = session.nextEvent(timeout_ms)
            if event.eventType() == blpapi.Event.RESPONSE:
                break

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
                                'date': date.date(),
                                'ticker': ticker,
                                'price': price
                            })

        if data:
            print(f"✅ Successfully fetched {len(data)} SPY records")
            latest = data[-1]
            print(f"📈 Latest SPY price: ${latest['price']:.2f} (as of {latest['date']})")
            return data
        else:
            print("⚠️ No SPY data returned")
            return []

    except Exception as e:
        print(f"❌ SPY data fetch failed: {e}")
        return []

def main():
    """Main test function."""
    print("🔍 Bloomberg API Connection Test")
    print("=" * 50)

    # Step 1: Test import
    success, blpapi = test_bloomberg_import()
    if not success:
        return False

    print()

    # Step 2: Test session
    session = test_bloomberg_session(blpapi)
    if not session:
        return False

    print()

    # Step 3: Test SPY data
    data = test_spy_data(session, blpapi)

    # Cleanup
    session.stop()

    print("=" * 50)
    if data:
        print("✅ Bloomberg API test PASSED!")
        print("🎉 Your hedge blotter app should work with Bloomberg charts!")
        return True
    else:
        print("❌ Bloomberg API test FAILED!")
        print("\nTroubleshooting steps:")
        print("1. Ensure Bloomberg Terminal is running")
        print("2. Check Bloomberg API installation")
        print("3. Verify network connectivity to Bloomberg")
        print("4. Confirm you have permissions for SPY data")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
