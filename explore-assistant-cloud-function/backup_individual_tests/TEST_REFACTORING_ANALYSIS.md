# Test Refactoring Analysis & Plan

## Current Test Landscape

### ✅ **Well-Structured Tests (Keep & Migrate)**
1. **`tests/test_suite.py`** - Comprehensive unit test suite
   - Tests golden query filtering
   - Tests semantic model filtering  
   - Tests retry mechanisms
   - Tests model limits
   - Tests conversation processing
   - **Status**: ✅ Keep and update for modular architecture

2. **`tests/unit/core/`** - Modern unit tests for new modules
   - `test_auth.py` - JWT token parsing tests
   - `test_config.py` - Configuration management tests
   - `test_models.py` - Pydantic model validation tests
   - **Status**: ✅ Keep - already aligned with modular architecture

3. **`tests/unit/vertex/`** - Vertex AI module tests
   - `test_response_parser.py` - Response parsing tests
   - **Status**: ✅ Keep - already aligned with modular architecture

### ⚠️ **Integration Tests (Refactor)**
4. **`test_olympic_mcp_integration.py`** - Olympic system integration
   - Tests MCP tool calls to Olympic migration system
   - **Status**: 🔄 Refactor to use new REST API endpoints

5. **`test_live_vector_search.py`** - Live backend testing
   - Tests against actual deployed service
   - **Status**: 🔄 Update to test new REST backend

6. **`test_enhanced_integration.py`** - Vector search integration
   - **Status**: 🔄 Migrate to test new vector_search module

### 🗑️ **One-Off/Deprecated Tests (Archive or Remove)**
7. **Legacy Feature Tests**:
   - `test_product_codes.py` - Product code testing (one-off)
   - `test_dimension_query.py` - Specific query testing (one-off)
   - `test_exact_feedback_payload.py` - Feedback payload testing (one-off)
   - `test_explore_fields.py` - Field exploration testing (one-off)
   - `test_obscure_vector_search.py` - Obscure search cases (one-off)
   - `test_mcp_feedback_sequence.py` - Feedback sequence testing (one-off)
   - `test_vector_search_notification.py` - Notification testing (one-off)
   - `test_semantic_search.py` - Semantic search testing (one-off)
   - `test_mcp_server.py` - Legacy server testing (one-off)
   - **Status**: 🗑️ Archive or remove (most were debugging/one-off tests)

## Refactoring Plan

### Phase 1: Update Core Test Infrastructure ✅

**Update `tests/test_config.py`** to import from new modular architecture:
```python
# OLD
from mcp_server import filter_golden_queries_by_explores

# NEW  
from explore_selection.filters import filter_golden_queries_by_explores
from parameter_generation import generate_explore_params_from_query
from vertex.client import call_vertex_ai_with_retry
```

### Phase 2: Migrate Main Test Suite

**Update `tests/test_suite.py`**:
- ✅ Keep all existing test logic (it's well-structured)
- 🔄 Update imports to use new modular structure
- 🔄 Add tests for new REST API endpoints
- 🔄 Add tests for new production backend

### Phase 3: Create New Test Categories

**Create `tests/integration/test_rest_api.py`**:
```python
class TestRestAPI(unittest.TestCase):
    """Test the new REST API endpoints"""
    
    def test_query_endpoint(self):
        # Test POST /api/v1/query
        
    def test_health_endpoint(self):
        # Test GET /api/v1/health
        
    def test_admin_endpoints(self):
        # Test admin query promotion endpoints
```

**Create `tests/unit/parameter_generation/`**:
- Test new parameter generation module
- Test validation logic
- Test fallback mechanisms

**Create `tests/unit/explore_selection/`**:
- Test explore determination logic
- Test context synthesis
- Test filtering utilities

**Create `tests/unit/vector_search/`**:
- Test vector search client
- Test enhanced integration
- Test field lookup service

### Phase 4: Archive Legacy Tests

**Create `tests/archived/`** directory and move:
- All one-off debugging tests
- Legacy integration tests that are no longer relevant
- Keep them for historical reference but don't run them

### Phase 5: Update Test Runner

**Update `tests/run_tests.py`** to:
- Run only the new structured tests
- Skip archived tests
- Generate better test reports
- Test both unit and integration layers

## Test Categories by Purpose

### 🎯 **Critical Tests (Must Maintain)**
1. **Core functionality** - Parameter generation, explore selection
2. **REST API endpoints** - All new API endpoints
3. **Integration flows** - End-to-end user flows
4. **Authentication** - Token parsing and validation
5. **Error handling** - Fallbacks and error responses

### 🔧 **Development Tests (Useful)**
1. **Model limits** - Token calculations
2. **Retry mechanisms** - Vertex AI retries
3. **Configuration** - Environment setup
4. **Data validation** - Pydantic models

### 🗑️ **Deprecated Tests (Archive)**
1. **One-off debugging** - Specific bug investigations
2. **Legacy features** - spaCy noun extraction tests
3. **Experimental features** - Features that were removed
4. **Manual testing scripts** - Ad-hoc test scripts

## Benefits of Refactoring

### ✅ **Improved Test Organization**
- Clear separation of unit vs integration tests  
- Modular test structure matches code structure
- Better test discoverability and maintenance

### ✅ **Better CI/CD Integration**
- Faster test execution (skip archived tests)
- Clear test categories for different pipeline stages
- Better test reporting and coverage metrics

### ✅ **Easier Onboarding**
- New developers can understand test structure
- Clear examples of how to test each module
- Separation of production-critical vs debugging tests

## Implementation Priority

1. **High Priority** - Update core test infrastructure and main test suite
2. **Medium Priority** - Create new modular tests for new architecture  
3. **Low Priority** - Archive legacy tests (can be done gradually)

The existing test suite has good coverage of core functionality, but needs to be updated for the new modular architecture and REST API.