#!/usr/bin/env bash
set -euo pipefail

# Runtime verification host only; no trading account or strategy is configured.
test "$(uname -m)" = x86_64
mkdir -p "$HOME/mt5-verification"

if ! sudo swapon --show=NAME --noheadings | grep -q .; then
  if [ ! -e /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
  fi
  sudo swapon /swapfile
  if ! grep -q '^/swapfile ' /etc/fstab; then
    printf '/swapfile none swap sw 0 0\n' | sudo tee -a /etc/fstab >/dev/null
  fi
fi
printf 'vm.swappiness=10\n' | sudo tee /etc/sysctl.d/60-mt5-swap.conf >/dev/null
sudo sysctl -p /etc/sysctl.d/60-mt5-swap.conf

sudo dpkg --add-architecture i386
sudo install -d -m 755 /etc/apt/keyrings
curl -fsSL https://dl.winehq.org/wine-builds/winehq.key -o "$HOME/mt5-verification/winehq.key"
sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/winehq-archive.key "$HOME/mt5-verification/winehq.key"
sudo curl -fsSL https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources -o /etc/apt/sources.list.d/winehq-noble.sources
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --install-recommends winehq-staging xvfb xauth sysstat fonts-liberation
wine --version
free -m
df -h /
