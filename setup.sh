#!/usr/bin/env bash
# ==============================================================================
# Superfood Automation Suite (TuyulVB) - Seamless Installer for Linux / Raspberry Pi
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🚀 Starting Seamless Installation for Superfood Automation Suite"
echo "======================================================================"

# 1. System Package Installation (Debian/Ubuntu/Raspberry Pi OS)
if command -v apt &> /dev/null; then
    echo "📦 Updating system package list..."
    sudo apt update -y

    echo "📦 Installing required system packages (Python, Chromium, Chromedriver)..."
    sudo apt install -y python3 python3-pip python3-venv python3-full \
                        chromium-browser chromium-chromedriver || \
    sudo apt install -y python3 python3-pip python3-venv python3-full \
                        chromium chromium-driver
else
    echo "⚠️ 'apt' package manager not found. Please ensure Python 3, Chromium, and Chromedriver are installed."
fi

# 2. Setup Virtual Environment (Recommended on modern Linux OS like Debian 12 / Pi OS)
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Creating Python virtual environment in '$VENV_DIR'..."
    python3 -m venv "$VENV_DIR"
else
    echo "🐍 Existing virtual environment found in '$VENV_DIR'."
fi

# Activate venv for installation
PYTHON_BIN="$VENV_DIR/bin/python3"
PIP_BIN="$VENV_DIR/bin/pip"

# 3. Upgrade Pip & Install Dependencies
echo "⚡ Upgrading pip..."
"$PIP_BIN" install --upgrade pip

echo "📥 Installing Python dependencies from requirements.txt..."
"$PIP_BIN" install -r requirements.txt

# 4. Initialize .env file if missing
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        echo "📝 Creating initial .env from .env.example..."
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    fi
else
    echo "✅ Existing .env file found."
fi

# 5. Make shell scripts executable
echo "🔑 Granting executable permissions to runner scripts..."
chmod +x "$SCRIPT_DIR/1. run_master.sh" "$SCRIPT_DIR/2. run_force_open_scheduler.sh" "$SCRIPT_DIR/setup.sh"

echo "======================================================================"
echo "🎉 Installation completed successfully!"
echo "======================================================================"
echo ""
echo "Next Steps:"
echo "1. Edit '.env' to fill in your MONDAY_API_KEY and DISCORD_WEBHOOK_URL."
echo "2. Run the application:"
echo "   ./\"1. run_master.sh\""
echo "3. Run the scheduler:"
echo "   ./\"2. run_force_open_scheduler.sh\""
echo "======================================================================"
