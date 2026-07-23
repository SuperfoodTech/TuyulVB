#!/usr/bin/env bash
# ==============================================================================
# Superfood Automation Suite (TuyulVB) - High-Speed Installer using UV
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🚀 Starting Ultra-Fast Setup for Superfood Automation Suite"
echo "======================================================================"

# 1. System Package Installation (Debian/Ubuntu/Raspberry Pi OS)
if command -v apt &> /dev/null; then
    echo "📦 Checking and installing system packages (Python, Chromium, Chromedriver)..."
    sudo apt update -y
    sudo apt install -y python3 python3-pip python3-venv python3-full curl \
                        chromium-browser chromium-chromedriver || \
    sudo apt install -y python3 python3-pip python3-venv python3-full curl \
                        chromium chromium-driver || true
fi

# 2. Check / Install 'uv' for ultra-fast environment & package resolution
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

if ! command -v uv &> /dev/null; then
    echo "⚡ 'uv' not detected. Installing 'uv' package manager..."
    if command -v pip3 &> /dev/null; then
        pip3 install uv --break-system-packages 2>/dev/null || pip3 install uv || true
    fi
    if ! command -v uv &> /dev/null; then
        curl -sSf https://astral.sh/uv/install.sh | sh || true
        export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    fi
fi

# 3. Setup Virtual Environment using UV (or fallback to standard venv)
VENV_DIR="$SCRIPT_DIR/venv"
if command -v uv &> /dev/null; then
    echo "⚡ Using 'uv' to manage virtual environment & dependencies..."
    if [ ! -d "$VENV_DIR" ]; then
        uv venv "$VENV_DIR"
    fi
    echo "📥 Installing Python dependencies with 'uv'..."
    uv pip install --python "$VENV_DIR/bin/python3" -r requirements.txt
else
    echo "🐍 'uv' unavailable, falling back to standard venv..."
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r requirements.txt
fi

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
echo "🎉 Setup completed successfully!"
echo "======================================================================"
echo ""
echo "Next Steps:"
echo "1. Edit '.env' to fill in your MONDAY_API_KEY and DISCORD_WEBHOOK_URL."
echo "2. Run the application:"
echo "   ./\"1. run_master.sh\""
echo "3. Run the scheduler:"
echo "   ./\"2. run_force_open_scheduler.sh\""
echo "======================================================================"
