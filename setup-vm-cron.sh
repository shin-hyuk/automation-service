#!/bin/bash

# Automation Service Setup
# Sets up cron job to run gary_wealth.py every hour

set -e

echo "🤖 Setting up Automation Service..."

# Get current directory
REPO_DIR=$(pwd)
SCRIPT_PATH="$REPO_DIR/services/gary_wealth.py"

# Check if gary_wealth.py exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: gary_wealth.py not found at $SCRIPT_PATH"
    exit 1
fi

# Check if service-account.json exists
SERVICE_ACCOUNT_PATH="$REPO_DIR/services/utils/service-account.json"
if [ ! -f "$SERVICE_ACCOUNT_PATH" ]; then
    echo "❌ Error: service-account.json not found at $SERVICE_ACCOUNT_PATH"
    exit 1
fi

# Install system dependencies if needed
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv cron

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Create logs directory
mkdir -p logs

# Set proper permissions for service account
chmod 600 "$SERVICE_ACCOUNT_PATH"

# Get current crontab and add our job
echo "⏰ Setting up cron job for Automation Service..."

# Create temporary crontab file
crontab -l > temp_crontab 2>/dev/null || touch temp_crontab

# Remove any existing gary_wealth entries
grep -v "gary_wealth" temp_crontab > temp_crontab_clean || touch temp_crontab_clean

# Add new cron job (every hour at minute 0)
cat >> temp_crontab_clean << EOF

# Automation Service - runs every hour
0 * * * * cd $REPO_DIR && $REPO_DIR/venv/bin/python $SCRIPT_PATH >> logs/gary_wealth.log 2>&1

EOF

# Install the new crontab
crontab temp_crontab_clean
rm temp_crontab temp_crontab_clean

# Check if cron service is running
echo "🔧 Ensuring cron service is running..."
sudo systemctl enable cron
sudo systemctl start cron
sudo systemctl status cron --no-pager

echo ""
echo "🎉 Automation Service Setup Complete!"
echo ""
echo "📋 Setup Summary:"
echo "   • Script Location: $SCRIPT_PATH"
echo "   • Service Account: $SERVICE_ACCOUNT_PATH"
echo "   • Schedule: Every hour (0 * * * *)"
echo "   • Logs: logs/gary_wealth.log"
echo ""
echo "📊 Management Commands:"
echo "   • View cron jobs: crontab -l"
echo "   • Check logs: tail -f logs/gary_wealth.log"
echo "   • Test script: cd $REPO_DIR && venv/bin/python services/gary_wealth.py"
echo "   • Edit cron: crontab -e"
echo ""
echo "⏰ Current Cron Jobs:"
crontab -l | grep -E "(gary_wealth|^#|^$)" || echo "   No cron jobs found"
echo ""
echo "💡 The automation service will run every hour and collect wealth data automatically!"
