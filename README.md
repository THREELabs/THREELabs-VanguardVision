# 🎯 Buffett Portfolio Tracker

A sophisticated Python tool that monitors and analyzes Warren Buffett's Berkshire Hathaway investment portfolio in real-time. This tracker automatically fetches data from SEC EDGAR 13F filings and provides comprehensive analysis of portfolio changes, position movements, and historical transactions.

## 🌟 Features

### 📊 Real-Time Portfolio Monitoring
- Automatically fetches the latest 13F filings from SEC EDGAR
- Tracks current holdings and portfolio changes
- Updates stock data hourly using Yahoo Finance API
- Caches stock data to minimize API calls and improve performance

### 📈 Comprehensive Analysis
- **Position Change Detection:**
  - New positions
  - Closed positions
  - Increased holdings
  - Decreased holdings
  - Unchanged positions

- **Historical Transaction Tracking:**
  - Complete position exits
  - Partial sales
  - Position increases
  - Detailed sale records with dates and values

### 📑 Detailed Reporting
- Generates comprehensive reports including:
  - Currently held positions with valuations
  - Recent sales activity (last 30 days)
  - Complete historical sales record
  - Position changes and movements
  - Price performance metrics

### 💾 Data Persistence
- Maintains historical data across sessions
- Caches stock information to reduce API calls
- Stores:
  - Previous holdings
  - Sold positions
  - Stock information cache

### 🔄 Automated Updates
- Runs continuously with hourly updates
- Automatically refreshes stock cache when expired
- Saves reports with timestamps
- Maintains detailed logging for monitoring and debugging

## 🛠️ Technical Features
- **Error Handling:** Robust error handling and logging system
- **Data Caching:** Intelligent caching system with configurable duration
- **API Integration:** 
  - SEC EDGAR for 13F filings
  - Yahoo Finance for real-time stock data
- **File Management:** Automated report generation and data persistence

## 📋 Prerequisites
```
python 3.x
pandas
yfinance
requests
beautifulsoup4
```

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/buffett-tracker.git
cd buffett-tracker
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## 💻 Usage

Run the tracker:
```bash
python buffett_tracker.py
```

The program will:
1. Start monitoring Berkshire's portfolio
2. Generate hourly reports
3. Save analysis to timestamped files
4. Continue running until interrupted (Ctrl+C)

## 📁 Output Files
- `buffett_analysis_[timestamp].txt`: Detailed portfolio analysis reports
- `buffett_tracker.log`: Program execution logs
- `previous_holdings.pkl`: Cached holdings data
- `sold_positions.pkl`: Historical transaction records
- `stock_cache.pkl`: Cached stock information

## 🔍 Sample Report Structure
- Complete Position Exits
- Recent Sales Activity (30-day window)
- Historical Sales Record
- Recent Position Changes
  - New Positions
  - Closed Positions
  - Increased/Decreased Positions
- Current Holdings Summary

## ⚠️ Limitations
- Depends on SEC EDGAR website availability
- Yahoo Finance API rate limits may apply
- 13F filings are published quarterly
- Some small positions might not be reported in 13F filings

## 📝 Logging
The program maintains detailed logs in `buffett_tracker.log`, including:
- Information messages
- Warning messages
- Error messages
- Debug information

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments
- SEC EDGAR for providing 13F filing data
- Yahoo Finance for real-time stock information
- Beautiful Soup for web scraping capabilities
