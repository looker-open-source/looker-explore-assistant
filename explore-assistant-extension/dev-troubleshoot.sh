#!/bin/bash

echo "🔧 Frontend Development Troubleshooting"
echo "======================================="

echo ""
echo "1. System Resources:"
echo "-------------------"
echo "Memory:"
free -h 2>/dev/null || echo "free command not available"

echo ""
echo "CPU cores:"
nproc 2>/dev/null || echo "nproc command not available"

echo ""
echo "Node.js version:"
node --version 2>/dev/null || echo "Node.js not found"

echo ""
echo "npm version:" 
npm --version 2>/dev/null || echo "npm not found"

echo ""
echo "2. Cleaning Development Environment:"
echo "-----------------------------------"

echo "Cleaning webpack cache..."
rm -rf .webpack_cache
echo "✅ Webpack cache cleared"

echo "Cleaning node_modules cache..."
rm -rf node_modules/.cache
echo "✅ Node modules cache cleared"

echo "Cleaning dist directory..."
rm -rf dist
echo "✅ Dist directory cleared"

echo ""
echo "3. Checking for memory issues:"
echo "-----------------------------"
echo "Checking for running Node processes..."
ps aux | grep -E "(node|npm)" | grep -v grep || echo "No Node.js processes running"

echo ""
echo "4. Available npm scripts:"
echo "------------------------"
echo "🚀 npm run start          - Default start (4GB memory limit)"
echo "💾 npm run start:low-memory - Low memory mode (2GB limit)"  
echo "⚡ npm run start:basic     - Basic mode (no hot reload)"

echo ""
echo "5. Troubleshooting Steps:"
echo "------------------------"
echo "If npm run start fails:"
echo "  1. Try: npm run start:low-memory"
echo "  2. Try: npm run start:basic"
echo "  3. Check if port 8080 is in use: lsof -i :8080"
echo "  4. Try a different port: npm run start -- --port 8081"

echo ""
echo "6. Memory Optimization Applied:"
echo "------------------------------"
echo "✅ Added --max-old-space-size=4096 to start script"
echo "✅ Added memory-optimized webpack config"
echo "✅ Disabled some webpack optimizations in dev mode"
echo "✅ Added minimal stats output"

echo ""
echo "🎯 Ready to start development!"
echo "Try: npm run start"
