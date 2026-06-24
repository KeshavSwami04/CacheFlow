#!/bin/bash
set -e

echo "=== CacheFlow VPS Provisioning Script ==="
echo "Updating package lists..."
sudo apt-get update -y

# 1. Configure 4GB Swap Space (Crucial to prevent Out-Of-Memory crashes on 1GB RAM instances like AWS t2.micro)
if [ -f /swapfile ]; then
    echo "Swap file already exists. Skipping allocation."
else
    echo "Allocating 2GB Swap space..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap space successfully configured."
fi

# 2. Install Docker
if command -v docker &> /dev/null; then
    echo "Docker is already installed."
else
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    echo "Docker installed successfully."
fi

# 3. Configure User Permissions
echo "Configuring permissions for user $USER..."
sudo usermod -aG docker $USER || true

echo "========================================="
echo "Setup Complete!"
echo "Please log out of your SSH session and log back in for docker group changes to take effect."
echo ""
echo "Then, run these commands to start CacheFlow:"
echo "  git clone https://github.com/KeshavSwami04/CacheFlow.git"
echo "  cd CacheFlow"
echo "  cp .env.example .env"
echo "  docker compose up --build -d"
echo "========================================="
