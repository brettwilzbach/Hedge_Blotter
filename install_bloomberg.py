#!/usr/bin/env python3
"""
Bloomberg API Installation Script
This script helps install the Bloomberg API for the Hedge Blotter application.
"""

import subprocess
import sys
import os

def install_bloomberg_api():
    """Install Bloomberg API using the official Bloomberg package index."""
    print("🔍 Installing Bloomberg API...")
    print("=" * 50)
    
    try:
        # Install blpapi from Bloomberg's package index
        print("Installing blpapi...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--index-url=https://bcms.bloomberg.com/pip/simple", 
            "blpapi"
        ])
        print("✅ blpapi installed successfully")
        
        # Install xbbg (Python wrapper for Bloomberg API)
        print("Installing xbbg...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "xbbg"
        ])
        print("✅ xbbg installed successfully")
        
        print("\n🎉 Bloomberg API installation completed!")
        print("\nNext steps:")
        print("1. Make sure Bloomberg Terminal is running")
        print("2. Run the app: streamlit run app.py")
        print("3. Test Bloomberg connection in the app")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have Bloomberg Terminal installed")
        print("2. Check your internet connection")
        print("3. Try running as administrator")
        print("4. Contact Bloomberg support if issues persist")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_bloomberg_terminal():
    """Check if Bloomberg Terminal is running."""
    print("🔍 Checking Bloomberg Terminal...")
    
    # This is a simple check - in practice, you might want to check for specific processes
    # or try to connect to the Bloomberg API
    print("⚠️  Please ensure Bloomberg Terminal is running before using the app")
    print("   The app will show appropriate warnings if Bloomberg is not available")

if __name__ == "__main__":
    print("Cannae Hedge Blotter - Bloomberg API Installer")
    print("=" * 50)
    
    # Check if Bloomberg Terminal is running
    check_bloomberg_terminal()
    
    # Ask user if they want to proceed
    response = input("\nDo you want to install the Bloomberg API? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        success = install_bloomberg_api()
        sys.exit(0 if success else 1)
    else:
        print("Installation cancelled. The app will work without Bloomberg features.")
        print("You can run this script again later if you change your mind.")
        sys.exit(0)
