# Area Selector Feature Tests

This document describes the automated tests for the area selector feature in the Looker Explore Assistant.

## Test Coverage

The area selector feature tests are organized into 4 test suites:

### 1. Assistant Slice Tests (`assistantSlice.simple.test.ts`)

Tests the Redux state management for area selection:

- **setSelectedArea reducer**
  - ✅ Sets the selected area correctly
  - ✅ Clears the selected area when empty string is passed
  - ✅ Handles null values properly

- **setSelectedExplores reducer**
  - ✅ Sets selected explores array
  - ✅ Clears selected explores when empty array is passed
  - ✅ Replaces existing explores with new selection

- **State immutability**
  - ✅ Maintains state immutability when setting area
  - ✅ Maintains state immutability when setting explores

- **Area interface validation**
  - ✅ Validates correct structure for Area type

**Total: 9 tests**

### 2. Agent Page Helpers Tests (`agentPageHelpers.test.ts`)

Tests the helper functions used in the AgentPage component:

- **getExploresForSelectedArea**
  - ✅ Returns explores for selected area
  - ✅ Returns empty array when no area is selected
  - ✅ Returns empty array when area is not found

- **getExploreDetails**
  - ✅ Returns explore details when area and explore exist
  - ✅ Returns fallback display name when no area is selected
  - ✅ Returns fallback display name when explore details are missing
  - ✅ Handles malformed explore keys gracefully
  - ✅ Handles missing explore_details gracefully

- **Display name generation**
  - ✅ Properly formats explore keys to display names
  - ✅ Handles edge cases in formatting

- **Area and explore validation**
  - ✅ Validates area exists in available areas
  - ✅ Validates explore exists in selected area

**Total: 12 tests**

### 3. Backend Integration Tests (`areaBackendIntegration.test.ts`)

Tests the integration between frontend area selection and backend processing:

- **restrictedExploreKeys logic**
  - ✅ Prioritizes selectedExplores over area-wide restrictions
  - ✅ Handles missing area data gracefully

- **Payload construction for backend**
  - ✅ Constructs correct payload with area restrictions

- **Backend response handling**
  - ✅ Handles explore determination with restrictions

- **Conversation context with areas**
  - ✅ Includes area context in conversation messages
  - ✅ Formats explore names correctly for messages

**Total: 6 tests**

### 4. useAreas Hook Tests (`useAreas.test.ts`)

Tests the core logic of the useAreas hook:

- **Hook importability**
  - ✅ Hook exists and is importable

- **Data processing logic**
  - ✅ Handles area data processing logic correctly
  - ✅ Handles empty data gracefully
  - ✅ Handles malformed data gracefully

**Total: 4 tests**

## Running Tests

### Individual Test Suites

```bash
# Run Redux state tests
npm test tests/unit_tests/assistantSlice.simple.test.ts

# Run helper function tests  
npm test tests/unit_tests/agentPageHelpers.test.ts

# Run backend integration tests
npm test tests/unit_tests/areaBackendIntegration.test.ts

# Run hook tests
npm test tests/unit_tests/useAreas.test.ts
```

### All Area Selector Tests

```bash
# Run all area selector tests once
npm test -- --testPathPattern="unit_tests/(assistantSlice.simple|agentPageHelpers|areaBackendIntegration|useAreas)"

# Run area selector tests with watch mode (continuous)
npm test -- --testPathPattern="unit_tests/(assistantSlice.simple|agentPageHelpers|areaBackendIntegration|useAreas)" --watch

# Use the convenience script
./run-area-tests-fixed.sh
```

### All Tests

```bash
# Run all tests once
npm test

# Run all tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## Test Summary

- **Total Area Selector Tests**: 31
- **All Tests Passing**: ✅
- **Coverage Areas**:
  - Redux state management
  - UI helper functions
  - Backend integration
  - Data processing logic
  - Error handling
  - Edge cases

## Continuous Testing

The area selector tests are designed to run continuously during development. Use the watch mode to automatically re-run tests when code changes:

```bash
npm test -- --testPathPattern="unit_tests/(assistantSlice.simple|agentPageHelpers|areaBackendIntegration|useAreas)" --watch
```

This provides immediate feedback when making changes to the area selector functionality.

## Test Dependencies

The tests use the following testing libraries:
- **Jest**: Test runner and assertions
- **@testing-library/react-hooks**: For testing React hooks (partially used)
- **@testing-library/jest-dom**: For DOM testing utilities

All dependencies are installed and configured in `package.json`.
