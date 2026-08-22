#!/bin/bash
# One-time VPS setup: installs Docker + Compose, clones repo, starts stack.
set -e
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo apt-get install -y docker-compose-plugin
git clone https://github.com/Issamonge/proconnect-hub.git
cd proconnect-hub
cp .env.example .env
echo ">>> EDIT .env with your DB password: nano .env"
echo ">>> then run: bash scripts/start.sh"
