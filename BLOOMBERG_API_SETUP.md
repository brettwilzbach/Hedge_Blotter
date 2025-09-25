# Bloomberg API (blpapi) Installation Guide

## Overview
The Bloomberg API (`blpapi`) requires special installation steps as it's not available through standard PyPI repositories. This guide provides step-by-step instructions for setting up Bloomberg API in your Python environment.

## Prerequisites
- Bloomberg Terminal or Bloomberg Anywhere subscription
- Python 3.7+ installed
- Administrative privileges on your system

## Installation Steps

### 1. Download Bloomberg C++ SDK
1. Go to [Bloomberg API Library](http://www.bloomberg.com/professional/api-library)
2. Log in with your Bloomberg credentials
3. Download the latest Bloomberg C++ SDK for your operating system
4. Extract the SDK to a directory (e.g., `C:\bloomberg\`)

### 2. Install the C++ SDK
1. Run the Bloomberg C++ SDK installer
2. Follow the installation wizard
3. Note the installation directory (typically `C:\bloomberg\API\v3\`)

### 3. Test Installation
After installation, test if the Bloomberg API works by running the test script:

```bash
python test_bloomberg.py
```

This will:
- Test if `blpapi` can be imported
- Test session creation with Bloomberg Terminal
- Test fetching actual SPY price data

### 4. Set Environment Variables
Add the following environment variables to your system:

**Windows:**
```cmd
set BLPAPI_ROOT=C:\bloomberg\API\v3
set PATH=%PATH%;%BLPAPI_ROOT%\bin
```

**Linux/Mac:**
```bash
export BLPAPI_ROOT=/path/to/bloomberg/api/v3
export PATH=$PATH:$BLPAPI_ROOT/bin
```

### 5. Install Python Package
Install the `blpapi` Python package from Bloomberg's private repository:

```bash
python -m pip install --index-url=https://bcms.bloomberg.com/pip/simple blpapi
```

### 6. Verify Installation
Test the installation by running:

```python
import blpapi
print("Bloomberg API successfully installed!")
```

### 7. Run Test Script
Test the complete setup by running the test script:

```bash
python test_bloomberg.py
```

This will:
- Test if `blpapi` can be imported
- Test session creation with Bloomberg Terminal
- Test fetching actual SPY price data

### 8. Test in Streamlit App
Once the API is working, you can test it in the Streamlit app:

```bash
streamlit run app.py
```

In the app:
1. Look for the "🔍 Bloomberg API Test" section at the top
2. Click "Test Bloomberg Connection"
3. The app will test the connection and show SPY price data if successful

## Troubleshooting

### Common Issues:

1. **"Could not find a version that satisfies the requirement blpapi"**
   - Ensure you're using Bloomberg's private repository
   - Verify you have Bloomberg Terminal access

2. **Import errors after installation**
   - Check that `BLPAPI_ROOT` environment variable is set correctly
   - Ensure the Bloomberg C++ SDK is properly installed
   - Restart your Python environment after installation

3. **Permission errors**
   - Run the installation commands as administrator (Windows)
   - Ensure you have write permissions to the Python installation directory

### Alternative Installation (if standard method fails):
```bash
# Try with additional flags
python -m pip install --index-url=https://bcms.bloomberg.com/pip/simple --trusted-host=bcms.bloomberg.com blpapi
```

## Usage Example
```python
import blpapi

# Initialize Bloomberg session
options = blpapi.SessionOptions()
options.setServerHost("localhost")
options.setServerPort(8194)

session = blpapi.Session(options)
if not session.start():
    print("Failed to start session")
```

## Notes
- Bloomberg API requires an active Bloomberg Terminal connection
- The API is only available to Bloomberg subscribers
- Version compatibility between C++ SDK and Python package is important
- For production use, consider using Bloomberg's official documentation and support

## Support
- Bloomberg API Documentation: [Official Bloomberg API Docs](https://bloomberg.github.io/blpapi-docs/)
- Bloomberg Support: Contact your Bloomberg representative for technical support

