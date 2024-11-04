import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
import time
import logging
import os
import pickle
import bs4
from bs4 import BeautifulSoup
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='buffett_tracker.log'
)
logger = logging.getLogger(__name__)

class BuffettTracker:
    def __init__(self):
        """Initialize the tracker."""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.holdings_file = 'previous_holdings.pkl'
        self.sold_positions_file = 'sold_positions.pkl'
        self.stock_cache_file = 'stock_cache.pkl'
        self.stock_cache_duration = timedelta(days=1)  # Cache stocks for 1 day
        self.load_previous_holdings()
        self.load_sold_positions()
        self.load_stock_cache()

    def load_previous_holdings(self):
        """Load previous holdings data from file."""
        try:
            if os.path.exists(self.holdings_file):
                with open(self.holdings_file, 'rb') as f:
                    self.previous_holdings = pickle.load(f)
            else:
                self.previous_holdings = {}
        except Exception as e:
            logger.error(f"Error loading previous holdings: {str(e)}")
            self.previous_holdings = {}

    def load_sold_positions(self):
        """Load historical sold positions data from file."""
        try:
            if os.path.exists(self.sold_positions_file):
                with open(self.sold_positions_file, 'rb') as f:
                    self.sold_positions = pickle.load(f)
            else:
                self.sold_positions = []
        except Exception as e:
            logger.error(f"Error loading sold positions: {str(e)}")
            self.sold_positions = []

    def load_stock_cache(self):
        """Load cached stock list if it exists and is not expired."""
        try:
            if os.path.exists(self.stock_cache_file):
                with open(self.stock_cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                cache_time = cache_data.get('timestamp')
                if cache_time and datetime.now() - cache_time < self.stock_cache_duration:
                    self.cached_stocks = cache_data.get('stocks', [])
                    return
            self.cached_stocks = None
        except Exception as e:
            logger.error(f"Error loading stock cache: {str(e)}")
            self.cached_stocks = None

    def save_stock_cache(self, stocks: List[str]):
        """Save stock list to cache with timestamp."""
        try:
            cache_data = {
                'timestamp': datetime.now(),
                'stocks': stocks
            }
            with open(self.stock_cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.error(f"Error saving stock cache: {str(e)}")

    def save_current_holdings(self, holdings):
        """Save current holdings data to file."""
        try:
            with open(self.holdings_file, 'wb') as f:
                pickle.dump(holdings, f)
        except Exception as e:
            logger.error(f"Error saving holdings: {str(e)}")

    def save_sold_positions(self):
        """Save sold positions data to file."""
        try:
            with open(self.sold_positions_file, 'wb') as f:
                pickle.dump(self.sold_positions, f)
        except Exception as e:
            logger.error(f"Error saving sold positions: {str(e)}")

    def record_sold_position(self, symbol: str, sale_data: Dict):
        """Record details of a sold position."""
        sale_record = {
            'symbol': symbol,
            'sale_date': datetime.now().strftime("%Y-%m-%d"),
            'shares_sold': sale_data['shares_sold'],
            'sale_value': sale_data['value'],
            'sale_type': 'complete' if sale_data.get('complete_sale', False) else 'partial',
            'remaining_shares': sale_data.get('remaining_shares', 0)
        }
        self.sold_positions.append(sale_record)
        self.save_sold_positions()

    def get_latest_13f_holdings(self) -> List[str]:
        """
        Fetch Berkshire's latest 13F holdings from SEC EDGAR.
        Returns a list of stock symbols.
        """
        try:
            # First, get the latest 13F filing
            cik = '0001067983'  # Berkshire's CIK
            url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F-HR&dateb=&owner=exclude&count=1'
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the latest 13F filing document link
            filing_link = soup.find('a', {'href': re.compile(r'.*\.xml$')})
            if not filing_link:
                logger.error("Could not find latest 13F XML filing")
                return []

            # Get the XML content
            xml_url = 'https://www.sec.gov' + filing_link['href']
            xml_response = requests.get(xml_url, headers=self.headers)
            xml_soup = BeautifulSoup(xml_response.content, 'xml')

            # Extract stock holdings
            holdings = []
            for holding in xml_soup.find_all('infoTable'):
                try:
                    cusip = holding.find('cusip').text
                    shares = int(holding.find('sshPrnamt').text)
                    if shares > 0:  # Only include current holdings
                        # Convert CUSIP to ticker symbol using yfinance
                        stock = yf.Ticker(cusip)
                        if stock.info and 'symbol' in stock.info:
                            holdings.append(stock.info['symbol'])
                except Exception as e:
                    logger.warning(f"Error processing holding: {str(e)}")
                    continue

            return holdings

        except Exception as e:
            logger.error(f"Error fetching 13F holdings: {str(e)}")
            return []

    def get_institutional_holdings(self) -> Dict:
        """Get Berkshire's institutional holdings from latest 13F filings."""
        try:
            brk = yf.Ticker("BRK-B")
            holdings = brk.institutional_holders

            if holdings is not None:
                holdings_dict = holdings.to_dict('records')
                formatted_holdings = {}

                for holding in holdings_dict:
                    formatted_holdings[holding.get('Holder', 'Unknown')] = {
                        'shares': holding.get('Shares', 0),
                        'date_reported': holding.get('Date Reported', ''),
                        'value': holding.get('Value', 0)
                    }

                return formatted_holdings
            return {}

        except Exception as e:
            logger.error(f"Error fetching institutional holdings: {str(e)}")
            return {}

    def get_stock_data(self, symbol: str) -> Dict:
        """Get detailed stock data including ownership information."""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            history = stock.history(period="1mo")

            inst_holders = stock.institutional_holders
            berkshire_holding = 0
            
            if inst_holders is not None:
                berkshire_rows = inst_holders[inst_holders['Holder'].str.contains('BERKSHIRE', case=False, na=False)]
                if not berkshire_rows.empty:
                    berkshire_holding = berkshire_rows['Shares'].sum()

            return {
                'current_price': info.get('currentPrice', 0),
                'day_high': info.get('dayHigh', 0),
                'day_low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'shares_held': berkshire_holding,
                'price_change_1m': (
                    ((history['Close'][-1] - history['Close'][0]) / history['Close'][0] * 100)
                    if not history.empty else 0
                )
            }
        except Exception as e:
            logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            return {}

    def get_buffett_stocks(self) -> List[str]:
        """
        Get list of Buffett stocks from latest 13F filing and historical records.
        Uses caching to avoid frequent SEC API calls.
        """
        try:
            # Check cache first
            if self.cached_stocks is not None:
                return self.cached_stocks

            # Fetch current holdings from 13F
            current_stocks = self.get_latest_13f_holdings()
            
            # If 13F fetch fails, use backup hardcoded list
            if not current_stocks:
                logger.warning("Using backup stock list due to 13F fetch failure")
                current_stocks = [
                    "KO", "AXP", "AAPL", "BAC", "CVX", "HPQ", "KHC", "MCO",
                    "OXY", "USB", "BK", "ALLY", "CE", "MKL", "PG", "JEF",
                    "ATVI", "LNC", "GL", "UPS", "DVA", "MMC", "TEVA", "STNE"
                ]

            # Add historical stocks from sold positions
            historical_stocks = [pos['symbol'] for pos in self.sold_positions]
            
            # Combine current and historical stocks
            all_stocks = list(set(current_stocks + historical_stocks))
            
            # Cache the results
            self.save_stock_cache(all_stocks)
            self.cached_stocks = all_stocks
            
            return all_stocks

        except Exception as e:
            logger.error(f"Error in get_buffett_stocks: {str(e)}")
            return []

    def detect_position_changes(self, current_holdings: Dict, previous_holdings: Dict) -> Dict:
        """Detect changes in positions between current and previous holdings."""
        changes = {
            'new_positions': [],
            'closed_positions': [],
            'increased_positions': [],
            'decreased_positions': [],
            'unchanged_positions': []
        }

        all_symbols = set(list(current_holdings.keys()) + list(previous_holdings.keys()))

        for symbol in all_symbols:
            current = current_holdings.get(symbol, {})
            previous = previous_holdings.get(symbol, {})

            current_shares = current.get('shares_held', 0)
            previous_shares = previous.get('shares_held', 0)

            if symbol not in previous_holdings and current_shares > 0:
                changes['new_positions'].append({
                    'symbol': symbol,
                    'shares': current_shares,
                    'value': current_shares * current.get('current_price', 0)
                })
            elif symbol not in current_holdings and previous_shares > 0:
                sale_data = {
                    'symbol': symbol,
                    'shares_sold': previous_shares,
                    'value': previous_shares * previous.get('current_price', 0),
                    'complete_sale': True
                }
                changes['closed_positions'].append(sale_data)
                self.record_sold_position(symbol, sale_data)
            elif current_shares > previous_shares:
                changes['increased_positions'].append({
                    'symbol': symbol,
                    'shares_added': current_shares - previous_shares,
                    'new_total_shares': current_shares,
                    'value_change': (current_shares - previous_shares) * current.get('current_price', 0)
                })
            elif current_shares < previous_shares:
                sale_data = {
                    'symbol': symbol,
                    'shares_sold': previous_shares - current_shares,
                    'value': (previous_shares - current_shares) * current.get('current_price', 0),
                    'complete_sale': False,
                    'remaining_shares': current_shares
                }
                changes['decreased_positions'].append(sale_data)
                self.record_sold_position(symbol, sale_data)
            else:
                changes['unchanged_positions'].append({
                    'symbol': symbol,
                    'shares': current_shares,
                    'value': current_shares * current.get('current_price', 0)
                })

        return changes

    def analyze_holdings(self) -> Dict:
        """Analyze current holdings and changes."""
        current_holdings = {}

        try:
            stocks = self.get_buffett_stocks()

            for symbol in stocks:
                stock_data = self.get_stock_data(symbol)
                if stock_data:
                    current_holdings[symbol] = stock_data

            changes = self.detect_position_changes(current_holdings, self.previous_holdings)
            self.save_current_holdings(current_holdings)

            return {
                'holdings': current_holdings,
                'changes': changes,
                'sold_positions': self.sold_positions
            }

        except Exception as e:
            logger.error(f"Error analyzing holdings: {str(e)}")
            return {'holdings': {}, 'changes': {}, 'sold_positions': []}

    def generate_report(self) -> str:
        """Generate a comprehensive report with position changes and historical sales."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = f"Warren Buffett Portfolio Analysis Report - {timestamp}\n"
        report += "=" * 60 + "\n\n"

        try:
            analysis = self.analyze_holdings()
            changes = analysis['changes']
            holdings = analysis['holdings']

            # Completely Sold Positions Section (New)
            report += "COMPLETELY SOLD POSITIONS (NO LONGER HELD):\n"
            report += "=" * 40 + "\n\n"
            
            completely_sold = [pos for pos in self.sold_positions 
                             if pos['sale_type'] == 'complete' and 
                             pos['symbol'] not in holdings]
            
            if completely_sold:
                for sale in sorted(completely_sold, key=lambda x: x['sale_date'], reverse=True):
                    report += f"Stock: {sale['symbol']}\n"
                    report += f"Exit Date: {sale['sale_date']}\n"
                    report += f"Total Shares Sold: {sale['shares_sold']:,}\n"
                    report += f"Exit Value: ${sale['sale_value']:,.2f}\n"
                    report += "-" * 30 + "\n"
            else:
                report += "No completely sold positions recorded yet.\n\n"

            # Recent Sales Activity Section
            report += "\nRECENT SALES ACTIVITY:\n"
            report += "=" * 40 + "\n\n"
            
            recent_sales = [pos for pos in self.sold_positions 
                          if (datetime.now() - datetime.strptime(pos['sale_date'], "%Y-%m-%d")).days <= 30]
            
            if recent_sales:
                for sale in sorted(recent_sales, key=lambda x: x['sale_date'], reverse=True):
                    report += f"Stock: {sale['symbol']}\n"
                    report += f"Sale Date: {sale['sale_date']}\n"
                    report += f"Type: {sale['sale_type'].title()} Sale\n"
                    report += f"Shares Sold: {sale['shares_sold']:,}\n"
                    report += f"Sale Value: ${sale['sale_value']:,.2f}\n"
                    if sale['sale_type'] == 'partial':
                        report += f"Remaining Shares: {sale['remaining_shares']:,}\n"
                    report += "-" * 30 + "\n"
            else:
                report += "No sales in the last 30 days.\n\n"

            # All Historical Sales Section
            report += "\nALL HISTORICAL SALES:\n"
            report += "=" * 40 + "\n\n"
            
            if self.sold_positions:
                for sale in sorted(self.sold_positions, key=lambda x: x['sale_date'], reverse=True):
                    report += f"Stock: {sale['symbol']}\n"
                    report += f"Sale Date: {sale['sale_date']}\n"
                    report += f"Type: {sale['sale_type'].title()} Sale\n"
                    report += f"Shares Sold: {sale['shares_sold']:,}\n"
                    report += f"Sale Value: ${sale['sale_value']:,.2f}\n"
                    if sale['sale_type'] == 'partial':
                        report += f"Remaining Shares: {sale['remaining_shares']:,}\n"
                    report += "-" * 30 + "\n"
            else:
                report += "No historical sales recorded yet.\n\n"

            # Recent Position Changes Section
            report += "\nRECENT POSITION CHANGES:\n"
            report += "=" * 40 + "\n\n"

            if changes['new_positions']:
                report += "NEW POSITIONS:\n"
                for pos in changes['new_positions']:
                    report += f"+ {pos['symbol']}: {pos['shares']:,} shares (${pos['value']:,.2f})\n"
                report += "\n"

            if changes['closed_positions']:
                report += "NEWLY CLOSED POSITIONS (COMPLETE SALES):\n"
                for pos in changes['closed_positions']:
                    report += f"- {pos['symbol']}: Sold all {pos['shares_sold']:,} shares (${pos['value']:,.2f})\n"
                report += "\n"

            if changes['decreased_positions']:
                report += "DECREASED POSITIONS (PARTIAL SALES):\n"
                for pos in changes['decreased_positions']:
                    report += f"↓ {pos['symbol']}: Reduced by {pos['shares_sold']:,} shares\n"
                    report += f"  New position: {pos['remaining_shares']:,} shares\n"
                    report += f"  Value of sold shares: ${pos['value']:,.2f}\n"
                report += "\n"

            if changes['increased_positions']:
                report += "INCREASED POSITIONS:\n"
                for pos in changes['increased_positions']:
                    report += f"↑ {pos['symbol']}: Added {pos['shares_added']:,} shares\n"
                    report += f"  New position: {pos['new_total_shares']:,} shares\n"
                    report += f"  Value change: ${pos['value_change']:,.2f}\n"
                report += "\n"

            # Current Holdings Section
            report += "\nCURRENT HOLDINGS SUMMARY:\n"
            report += "=" * 40 + "\n"

            for symbol, data in holdings.items():
                if data.get('shares_held', 0) > 0:  # Only show current holdings
                    report += f"\n{symbol}:\n"
                    report += f"Shares Held: {data.get('shares_held', 0):,}\n"
                    report += f"Current Price: ${data.get('current_price', 0):,.2f}\n"
                    report += f"Position Value: ${data.get('shares_held', 0) * data.get('current_price', 0):,.2f}\n"
                    report += f"1-Month Change: {data.get('price_change_1m', 0):.2f}%\n"
                    report += "-" * 30 + "\n"

            return report

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return f"Error generating report: {str(e)}"
        
def main():
    tracker = BuffettTracker()

    try:
        while True:
            # Clear stock cache if it's expired
            if tracker.cached_stocks is None or \
               (hasattr(tracker, 'stock_cache') and datetime.now() - tracker.stock_cache.get('timestamp', datetime.min) > tracker.stock_cache_duration):
                logger.info("Refreshing stock list from 13F filings...")
                tracker.cached_stocks = None

            report = tracker.generate_report()

            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"buffett_analysis_{timestamp}.txt"

            with open(filename, 'w') as f:
                f.write(report)

            print(report)
            print(f"\nReport saved to {filename}")

            print("\nWaiting for next update (Press Ctrl+C to stop)...")
            time.sleep(3600)  # Update every hour

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
