# F&O Trading App - Complete Setup Guide

## Prerequisites

### 1. System Requirements
- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)
- 4GB RAM minimum
- Internet connection for API access

### 2. Upstox Account Setup

1. **Create Developer Account**
   - Visit: https://upstox.com/developer/
   - Sign up or log in with your Upstox account
   - Navigate to "My Apps"

2. **Create New App**
   - Click "Create New App"
   - Fill in details:
     - App Name: "F&O Trading App"
     - Redirect URI: `http://localhost:8080`
     - App Type: "Web Application"
   - Note down your **API Key** and **API Secret**

## Installation Steps

### Step 1: Clone/Download the Application

```bash
cd fno_trading_app
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you encounter issues installing `ta-lib`, you may need to install it separately:

**Windows:**
```bash
# Download TA-Lib wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib‑0.4.XX‑cpXX‑cpXX‑win_amd64.whl
```

**macOS:**
```bash
brew install ta-lib
pip install ta-lib
```

**Linux:**
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install ta-lib
```

### Step 4: Configure Environment Variables

1. **Copy the example environment file:**
```bash
cp .env.example .env
```

2. **Edit `.env` file and add your credentials:**
```bash
# Open .env in your text editor
nano .env  # or use any text editor
```

3. **Add your Upstox credentials:**
```env
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_REDIRECT_URI=http://localhost:8080
ENVIRONMENT=sandbox
LOG_LEVEL=INFO
```

### Step 5: Configure Application Settings

Edit `config/config.yaml` to customize:

```yaml
# Set to false for live trading (be careful!)
upstox:
  sandbox_mode: true

# Add your preferred instruments
trading:
  instruments:
    - "NIFTY"
    - "BANKNIFTY"
    - "FINNIFTY"

# Adjust risk parameters
  risk:
    max_position_size: 100000  # in INR
    stop_loss_percentage: 2.0
    take_profit_percentage: 4.0
```

### Step 6: Test Installation

Run the basic example to verify everything is working:

```bash
python examples/basic_usage.py
```

You should see output showing signal generation and screening examples.

## Authentication Setup

### Getting Your Access Token

The Upstox API uses OAuth 2.0 for authentication. Here's how to get your access token:

#### Method 1: Using the Application

```python
from fno_trading_app import FNOTradingApp

# Initialize app
app = FNOTradingApp()

# Get authorization URL
app.setup_authentication()
# This will print an authorization URL
```

#### Method 2: Manual Authorization

1. **Generate Authorization URL:**
```
https://api-v2.upstox.com/login/authorization/dialog?response_type=code&client_id=YOUR_API_KEY&redirect_uri=http://localhost:8080
```

2. **Visit the URL in your browser:**
   - Log in to your Upstox account
   - Authorize the application
   - You'll be redirected to: `http://localhost:8080?code=AUTHORIZATION_CODE`

3. **Exchange Code for Access Token:**
```python
import requests

url = "https://api-v2.upstox.com/login/authorization/token"
data = {
    "code": "AUTHORIZATION_CODE",
    "client_id": "YOUR_API_KEY",
    "client_secret": "YOUR_API_SECRET",
    "redirect_uri": "http://localhost:8080",
    "grant_type": "authorization_code"
}

response = requests.post(url, data=data)
access_token = response.json()["access_token"]
```

4. **Set Access Token:**
```python
app.setup_authentication(access_token=access_token)
```

**Important:** Access tokens expire after 24 hours. You'll need to refresh or regenerate them daily.

## Running the Application

### 1. Quick Test (Demo Mode)

Run examples without live API connection:

```bash
# Basic usage examples
python examples/basic_usage.py

# Live trading demonstrations
python examples/live_trading_demo.py
```

### 2. Interactive Mode

```bash
python main.py
```

This will show you the available features and usage instructions.

### 3. Live Monitoring

Create a script for live monitoring:

```python
from fno_trading_app import FNOTradingApp

# Initialize
app = FNOTradingApp()

# Authenticate (use your access token)
app.setup_authentication(access_token='your_token')

# Define instruments to monitor
instruments = [
    'NSE_INDEX|Nifty 50',
    'NSE_INDEX|Nifty Bank'
]

# Start monitoring (updates every 5 minutes)
app.live_monitoring(instruments, interval_seconds=300)
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem:** `ModuleNotFoundError: No module named 'upstox_client'`

**Solution:**
```bash
pip install upstox-python-sdk
```

#### 2. TA-Lib Installation Issues

**Problem:** `error: command 'gcc' failed with exit status 1`

**Solution:** Install system dependencies first (see Step 3 above)

#### 3. API Authentication Errors

**Problem:** `ApiException: 401 Unauthorized`

**Solution:**
- Check your API credentials in `.env`
- Ensure access token is valid (not expired)
- Regenerate access token if needed

#### 4. Configuration File Not Found

**Problem:** `Config file not found at config/config.yaml`

**Solution:**
- Ensure you're running from the correct directory
- Check that `config/config.yaml` exists
- The app will use defaults if config is missing

#### 5. Rate Limiting

**Problem:** `ApiException: 429 Too Many Requests`

**Solution:**
- Increase the monitoring interval
- Reduce the number of instruments
- Implement exponential backoff

### Getting Help

1. **Check Logs:**
```bash
tail -f logs/trading.log
```

2. **Enable Debug Logging:**
Edit `config/config.yaml`:
```yaml
logging:
  level: "DEBUG"
```

3. **Test Individual Components:**
```python
# Test signal generator
from fno_trading_app import SignalGenerator
signal_gen = SignalGenerator()
print("Signal generator initialized successfully")

# Test screener
from fno_trading_app import FNOScreener
screener = FNOScreener()
print("Screener initialized successfully")
```

## Best Practices

### 1. Start with Sandbox Mode

Always test in sandbox mode first:
```yaml
upstox:
  sandbox_mode: true
```

### 2. Use Small Position Sizes

Start with minimal position sizes:
```yaml
trading:
  risk:
    max_position_size: 10000  # Small amount
```

### 3. Monitor Logs

Always keep logs enabled:
```yaml
logging:
  level: "INFO"
  file: "logs/trading.log"
  console: true
```

### 4. Regular Backups

Backup your configuration and trading data regularly.

### 5. Keep Credentials Secure

- Never commit `.env` file to version control
- Use environment variables in production
- Rotate API keys regularly

## Next Steps

1. **Read the Full Documentation:** `README.md`
2. **Run Examples:** Explore `examples/` directory
3. **Customize Configuration:** Adjust `config/config.yaml`
4. **Test Strategies:** Use historical data for backtesting
5. **Start Small:** Begin with paper trading or small positions

## Production Deployment

### For Production Use:

1. **Disable Sandbox Mode:**
```yaml
upstox:
  sandbox_mode: false
```

2. **Set Up Proper Logging:**
```yaml
logging:
  level: "INFO"
  file: "/var/log/fno_trading_app/trading.log"
```

3. **Use Environment Variables:**
```bash
export UPSTOX_API_KEY=xxx
export UPSTOX_API_SECRET=xxx
export ENVIRONMENT=production
```

4. **Set Up Monitoring:**
- Use systemd or supervisor for process management
- Set up log rotation
- Implement alerting

5. **Security:**
- Use HTTPS for all communications
- Implement IP whitelisting
- Regular security audits

## Support

For issues and questions:
- Check the documentation
- Review example scripts
- Test in sandbox mode first
- Check Upstox API status: https://upstox.com/developer/api-documentation/

---

**Ready to Trade?** Remember to always test thoroughly and use proper risk management!
