#!/bin/bash

# Area Selector Test Runner
# This script runs all tests related to the area selector feature from the correct directory

# Change to the explore-assistant-extension directory
cd /home/colin/looker-explore-assistant/explore-assistant-extension

echo "🧪 Running Area Selector Tests..."
echo "================================"
echo "Working directory: $(pwd)"
echo ""

# Run all area-related tests
npm test -- --testPathPattern="unit_tests/(assistantSlice.simple|agentPageHelpers|areaBackendIntegration|useAreas)" --passWithNoTests

echo ""
echo "✅ Area Selector Tests Complete"
echo ""
echo "Available test commands:"
echo "  npm test                     # Run all tests"
echo "  npm run test:watch          # Run all tests in watch mode"
echo "  npm run test:coverage       # Run tests with coverage"
echo "  ./run-area-tests.sh         # Run area selector tests"
echo ""
echo "To run area tests continuously:"
echo "  npm test -- --testPathPattern=\"unit_tests/(assistantSlice.simple|agentPageHelpers|areaBackendIntegration|useAreas)\" --watch"
