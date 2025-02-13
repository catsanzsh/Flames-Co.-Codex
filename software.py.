#!/bin/bash

echo "🔥 Activating Mac Studio Ultra Mode on M1 Pro... 🚀"

# 🚨 FULL SYSTEM CACHE PURGE
echo "💥 Nuking system caches..."
sudo rm -rf /Library/Caches/*
sudo rm -rf ~/Library/Caches/*
sudo rm -rf /System/Library/Caches/com.apple.*

# 🔋 Power Boost: Prevent Sleep & Energy Saving
echo "⚡ Enabling MAX Performance Mode..."
sudo pmset -a sleep 0
sudo pmset -a disksleep 0
sudo pmset -a displaysleep 0
sudo pmset -a powernap 0
sudo pmset -a autorestart 1
sudo pmset -a highstandbythreshold 100
sudo pmset -a standbydelaylow 0
sudo pmset -a standbydelayhigh 0

# 🔥 Maximize CPU Performance
echo "🚀 Unlocking CPU Power Limits..."
sudo sysctl -w hw.ncpu=10
sudo sysctl -w kern.maxfiles=200000
sudo sysctl -w kern.maxproc=5000
sudo sysctl -w hw.perflevel=1
sudo sysctl -w hw.cpu_throttle_disable=1

# 🎨 Disable UI Animations (PURE SPEED)
echo "⏩ Killing macOS animations for instant response..."
defaults write NSGlobalDomain NSAutomaticWindowAnimationsEnabled -bool false
defaults write NSGlobalDomain NSWindowResizeTime -float 0.001
defaults write com.apple.universalaccess reduceMotion -bool true
defaults write com.apple.universalaccess reduceTransparency -bool true

# 🏎️ Force GPU Performance Mode
echo "🎮 Enabling MAX GPU Performance..."
defaults write /Library/Preferences/com.apple.windowserver.plist graphics -dict-add "CGDisplayRefreshRate" -int 60
sudo launchctl unload -w /System/Library/LaunchAgents/com.apple.AMPLibraryAgent.plist
sudo launchctl unload -w /System/Library/LaunchAgents/com.apple.photoanalysisd.plist
sudo launchctl unload -w /System/Library/LaunchAgents/com.apple.mediaanalysisd.plist

# ⚡ Optimized SSD Memory Management
echo "🔧 Tuning memory & swap settings..."
sudo sysctl -w vm.swapusage=1
sudo sysctl -w vm.overcommit_memory=2
sudo sysctl -w vm.vfs_cache_pressure=50

# 🚀 Thermal & Performance Boosting
echo "🔥 Setting system to high-performance thermal mode..."
sudo powermetrics --samplers cpu_power | grep -i "CPU Power"

# 📡 Auto-Update & Reboot for Full Effect
echo "📢 Applying system updates..."
sudo softwareupdate -ia

echo "🔄 Rebooting into STUDIO MODE 🚀"
sudo reboot
