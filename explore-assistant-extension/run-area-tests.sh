#!/bin/bash

# Area Selector Test Runner
# This script runs all tests related to the area selector feature

echo "🧪 Running Area Selector Tests..."
echo "================================"

# Run all area-related tests
npm test -- --testPathPattern="unit_tests/(assistantSlice.simple|agentPageHelpers|areaBackendIntegration|useAreas)" --passWithNoTests

echo ""
echo "✅ Area Selector Tests Complete"
echo ""
echo "To run tests continuously, use:"
echo "npm test -- --testPathPattern=\"unit_tests/(assistantSlice.simple|agentPageHelpers|areaBackendIntegration|useAreas)\" --watch"
