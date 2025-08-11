#!/bin/bash
#
# Run all Python tests for the Looker Explore Assistant Cloud Function
# This script provides multiple options for running tests
#

echo "========================================"
echo "Looker Explore Assistant - Test Runner"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default to unified test suite
TEST_MODE="unified"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --individual|-i)
      TEST_MODE="individual"
      shift
      ;;
    --unified|-u)
      TEST_MODE="unified"
      shift
      ;;
    --all|-a)
      TEST_MODE="all"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -u, --unified     Run unified test suite (default)"
      echo "  -i, --individual  Run individual test files"
      echo "  -a, --all         Run both unified and individual tests"
      echo "  -h, --help        Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                # Run unified test suite"
      echo "  $0 --individual   # Run individual test files"
      echo "  $0 --all          # Run all tests"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Check if we're in the right directory
if [ ! -f "mcp_server.py" ]; then
    echo -e "${RED}❌ Error: mcp_server.py not found. Please run this from the explore-assistant-cloud-function directory${NC}"
    exit 1
fi

# Function to run individual tests
run_individual_tests() {
    echo -e "${BLUE}Running individual test files...${NC}"
    echo ""
    
    TEST_FILES=("test_filtering.py" "test_optimization.py" "test_retry_mechanism.py" "test_query_links.py")
    PASSED=0
    FAILED=0
    
    for test_file in "${TEST_FILES[@]}"; do
        if [ -f "$test_file" ]; then
            echo -e "${YELLOW}📋 Running: $test_file${NC}"
            if python3 "$test_file"; then
                echo -e "${GREEN}✅ $test_file - PASSED${NC}"
                ((PASSED++))
            else
                echo -e "${RED}❌ $test_file - FAILED${NC}"
                ((FAILED++))
            fi
            echo ""
        else
            echo -e "${YELLOW}⚠️  $test_file not found, skipping...${NC}"
        fi
    done
    
    echo -e "${BLUE}Individual Tests Summary:${NC}"
    echo -e "  ${GREEN}✅ Passed: $PASSED${NC}"
    echo -e "  ${RED}❌ Failed: $FAILED${NC}"
    echo ""
    
    return $FAILED
}

# Function to run unified test suite
run_unified_tests() {
    echo -e "${BLUE}Running unified test suite...${NC}"
    echo ""
    
    if [ -f "test_suite.py" ]; then
        python3 test_suite.py --verbose
        return $?
    else
        echo -e "${RED}❌ test_suite.py not found${NC}"
        return 1
    fi
}

# Main execution
case $TEST_MODE in
    "individual")
        run_individual_tests
        exit_code=$?
        ;;
    "unified")
        run_unified_tests
        exit_code=$?
        ;;
    "all")
        echo -e "${BLUE}Running ALL tests (individual + unified)...${NC}"
        echo ""
        
        run_individual_tests
        individual_exit=$?
        
        echo -e "${BLUE}Now running unified test suite...${NC}"
        echo ""
        
        run_unified_tests
        unified_exit=$?
        
        # Overall success if both passed
        if [ $individual_exit -eq 0 ] && [ $unified_exit -eq 0 ]; then
            echo -e "${GREEN}🎉 All test suites passed successfully!${NC}"
            exit_code=0
        else
            echo -e "${RED}⚠️  Some test suites failed. Check output above for details.${NC}"
            exit_code=1
        fi
        ;;
esac

exit $exit_code
