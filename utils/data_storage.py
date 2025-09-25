"""
Data storage utilities for the Hedge Blotter app.
Handles saving and loading trades to/from CSV files.
"""

import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = "data"
LIVE_TRADES_FILE = os.path.join(DATA_DIR, "live_trades.csv")
TRADE_HISTORY_FILE = os.path.join(DATA_DIR, "trade_history.csv")

def ensure_data_directory():
    """Create data directory if it doesn't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.info(f"Created data directory: {DATA_DIR}")

def save_live_trades(vanilla_trades: List[Dict], exotic_trades: List[Dict]):
    """Save live trades to CSV files."""
    try:
        ensure_data_directory()
        
        # Combine all live trades
        all_trades = []
        
        # Add vanilla trades
        for trade in vanilla_trades:
            trade_copy = trade.copy()
            trade_copy['trade_type'] = 'Vanilla'
            all_trades.append(trade_copy)
        
        # Add exotic trades
        for trade in exotic_trades:
            trade_copy = trade.copy()
            trade_copy['trade_type'] = 'Exotic'
            all_trades.append(trade_copy)
        
        if all_trades:
            df = pd.DataFrame(all_trades)
            df.to_csv(LIVE_TRADES_FILE, index=False)
            logger.info(f"Saved {len(all_trades)} live trades to {LIVE_TRADES_FILE}")
        else:
            # Create empty file if no trades
            pd.DataFrame().to_csv(LIVE_TRADES_FILE, index=False)
            logger.info("Created empty live trades file")
            
    except Exception as e:
        logger.error(f"Error saving live trades: {str(e)}")
        raise

def save_trade_history(trade_history: List[Dict]):
    """Save trade history to CSV file."""
    try:
        ensure_data_directory()
        
        if trade_history:
            df = pd.DataFrame(trade_history)
            df.to_csv(TRADE_HISTORY_FILE, index=False)
            logger.info(f"Saved {len(trade_history)} trades to history")
        else:
            # Create empty file if no history
            pd.DataFrame().to_csv(TRADE_HISTORY_FILE, index=False)
            logger.info("Created empty trade history file")
            
    except Exception as e:
        logger.error(f"Error saving trade history: {str(e)}")
        raise

def load_live_trades():
    """Load live trades from CSV files."""
    try:
        ensure_data_directory()
        
        vanilla_trades = []
        exotic_trades = []
        
        if os.path.exists(LIVE_TRADES_FILE):
            df = pd.read_csv(LIVE_TRADES_FILE)
            
            if not df.empty:
                # Convert date columns back to datetime
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
                if 'expiry' in df.columns:
                    df['expiry'] = pd.to_datetime(df['expiry']).dt.date
                
                # Split by trade type
                vanilla_df = df[df['trade_type'] == 'Vanilla']
                exotic_df = df[df['trade_type'] == 'Exotic']
                
                vanilla_trades = vanilla_df.to_dict('records')
                exotic_trades = exotic_df.to_dict('records')
                
                logger.info(f"Loaded {len(vanilla_trades)} vanilla trades and {len(exotic_trades)} exotic trades")
        
        return vanilla_trades, exotic_trades
        
    except Exception as e:
        logger.error(f"Error loading live trades: {str(e)}")
        return [], []

def load_trade_history():
    """Load trade history from CSV file."""
    try:
        ensure_data_directory()
        
        trade_history = []
        
        if os.path.exists(TRADE_HISTORY_FILE):
            df = pd.read_csv(TRADE_HISTORY_FILE)
            
            if not df.empty:
                # Convert date columns back to datetime
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
                if 'expiry' in df.columns:
                    df['expiry'] = pd.to_datetime(df['expiry']).dt.date
                if 'unwind_date' in df.columns:
                    df['unwind_date'] = pd.to_datetime(df['unwind_date']).dt.date
                
                trade_history = df.to_dict('records')
                logger.info(f"Loaded {len(trade_history)} trades from history")
        
        return trade_history
        
    except Exception as e:
        logger.error(f"Error loading trade history: {str(e)}")
        return []

def backup_data():
    """Create a backup of all data files."""
    try:
        ensure_data_directory()
        backup_dir = os.path.join(DATA_DIR, "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup live trades
        if os.path.exists(LIVE_TRADES_FILE):
            backup_file = os.path.join(backup_dir, f"live_trades_{timestamp}.csv")
            df = pd.read_csv(LIVE_TRADES_FILE)
            df.to_csv(backup_file, index=False)
            logger.info(f"Backed up live trades to {backup_file}")
        
        # Backup trade history
        if os.path.exists(TRADE_HISTORY_FILE):
            backup_file = os.path.join(backup_dir, f"trade_history_{timestamp}.csv")
            df = pd.read_csv(TRADE_HISTORY_FILE)
            df.to_csv(backup_file, index=False)
            logger.info(f"Backed up trade history to {backup_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return False

def get_data_summary():
    """Get summary of stored data."""
    try:
        vanilla_trades, exotic_trades = load_live_trades()
        trade_history = load_trade_history()
        
        return {
            'live_vanilla_trades': len(vanilla_trades),
            'live_exotic_trades': len(exotic_trades),
            'total_live_trades': len(vanilla_trades) + len(exotic_trades),
            'trade_history_count': len(trade_history),
            'data_files_exist': {
                'live_trades': os.path.exists(LIVE_TRADES_FILE),
                'trade_history': os.path.exists(TRADE_HISTORY_FILE)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting data summary: {str(e)}")
        return {}
