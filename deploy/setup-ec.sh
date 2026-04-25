#!/usr/bin/env bash
set -euo pipefail

# Install Python 3.10, pip, and nginx on common EC2 Linux distros.
if [[ -f /etc/os-release ]]; then
  . /etc/os-release
else
  echo "Cannot detect operating system: /etc/os-release not found."
  exit 1
fi

echo "Detected OS: ${ID:-unknown} ${VERSION_ID:-unknown}"

case "${ID:-}" in
  ubuntu|debian)
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python3-venv python3.10 python3.10-venv python3.10-distutils python3-pip nginx
    ;;
  amzn)
    # Amazon Linux 2023 and newer
    if command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y python3.10 python3.10-pip nginx
    else
      # Amazon Linux 2 fallback
      sudo yum install -y python3 python3-pip nginx
    fi
    ;;
  rhel|centos|rocky|almalinux|fedora)
    if command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y python3.10 python3.10-pip nginx
    else
      sudo yum install -y python3 python3-pip nginx
    fi
    ;;
  *)
    echo "Unsupported Linux distro: ${ID:-unknown}"
    exit 1
    ;;
esac

if command -v python3.10 >/dev/null 2>&1; then
  python3.10 --version
else
  python3 --version
fi

if command -v pip3 >/dev/null 2>&1; then
  pip3 --version
else
  echo "pip3 not found after installation."
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "nginx not found after installation."
  exit 1
fi

sudo systemctl enable --now nginx
sudo systemctl is-active --quiet nginx
echo "nginx is installed and running."

echo "To apply repo nginx config:"
echo "  sudo cp deploy/nginx/tngd-defence.conf /etc/nginx/sites-available/tngd-defence.conf"
echo "  sudo ln -sf /etc/nginx/sites-available/tngd-defence.conf /etc/nginx/sites-enabled/tngd-defence.conf"
echo "  sudo rm -f /etc/nginx/sites-enabled/default"
echo "  sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "To create backend virtual environment (run from repo root):"
echo "  cd ~/tngd-defence"
echo "  rm -rf backend/.venv"
echo "  python3 -m venv backend/.venv"
echo "  source backend/.venv/bin/activate"
echo "  python -m pip install --upgrade pip"
