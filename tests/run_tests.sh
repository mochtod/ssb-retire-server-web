#!/bin/bash

# Test Runner for SSB Retire Server Web Application
# Comprehensive testing suite using pytest

# Color codes for better readability
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test configuration
BASE_DIR="/mnt/c/Users/mochtod/Desktop/ssb-retire-server-soruce/ssb-retire-server-web"
TEST_DIR="${BASE_DIR}/tests"

# Print header
echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}              PYTEST TESTING FOR SSB RETIRE SERVER WEB          ${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo

# Function to install test dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    
    cd "$BASE_DIR"
    
    if [ -f "requirements-test.txt" ]; then
        pip install -r requirements-test.txt
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Test dependencies installed successfully${NC}"
        else
            echo -e "${RED}❌ Failed to install test dependencies${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ requirements-test.txt not found${NC}"
        return 1
    fi
    
    echo
}

# Function to run unit tests
run_unit_tests() {
    echo -e "${YELLOW}Running unit tests...${NC}"
    
    cd "$BASE_DIR"
    
    if pytest tests/unit/ -v --tb=short --cov=app --cov-report=term-missing; then
        echo -e "${GREEN}✅ Unit tests passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    echo -e "${YELLOW}Running integration tests...${NC}"
    
    cd "$BASE_DIR"
    
    if pytest tests/integration/ -v --tb=short; then
        echo -e "${GREEN}✅ Integration tests passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Integration tests failed${NC}"
        return 1
    fi
}

# Function to run security tests
run_security_tests() {
    echo -e "${YELLOW}Running security tests...${NC}"
    
    cd "$BASE_DIR"
    
    # Run security-specific tests
    if pytest tests/unit/test_security.py -v --tb=short -m "not skip"; then
        echo -e "${GREEN}✅ Security tests passed${NC}"
    else
        echo -e "${RED}❌ Security tests failed${NC}"
        return 1
    fi
    
    # Run bandit security linting
    echo -e "${YELLOW}Running bandit security scan...${NC}"
    if bandit -r app.py -f json > bandit_report.json 2>/dev/null; then
        echo -e "${GREEN}✅ Bandit security scan completed${NC}"
    else
        echo -e "${YELLOW}⚠️ Bandit security scan completed with findings${NC}"
    fi
    
    # Run safety dependency check
    echo -e "${YELLOW}Running safety dependency check...${NC}"
    if safety check -r requirements.txt > safety_report.txt 2>/dev/null; then
        echo -e "${GREEN}✅ Safety dependency check passed${NC}"
    else
        echo -e "${YELLOW}⚠️ Safety dependency check completed with findings${NC}"
    fi
    
    return 0
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${YELLOW}Running performance tests...${NC}"
    
    cd "$BASE_DIR"
    
    if pytest tests/unit/test_performance_metrics.py -v --tb=short; then
        echo -e "${GREEN}✅ Performance tests passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Performance tests failed${NC}"
        return 1
    fi
}

# Function to run coverage analysis
run_coverage_analysis() {
    echo -e "${YELLOW}Running coverage analysis...${NC}"
    
    cd "$BASE_DIR"
    
    # Generate HTML coverage report
    pytest tests/ --cov=app --cov-report=html --cov-report=term-missing > coverage_output.txt 2>&1
    
    if [ -d "htmlcov" ]; then
        echo -e "${GREEN}✅ Coverage report generated in htmlcov/index.html${NC}"
    else
        echo -e "${YELLOW}⚠️ Coverage report generation incomplete${NC}"
    fi
    
    # Extract coverage percentage
    if grep -q "TOTAL" coverage_output.txt; then
        coverage_line=$(grep "TOTAL" coverage_output.txt)
        echo -e "${BLUE}Coverage Summary: ${coverage_line}${NC}"
    fi
    
    return 0
}

# Function to run linting
run_linting() {
    echo -e "${YELLOW}Running code linting...${NC}"
    
    cd "$BASE_DIR"
    
    # Run flake8 linting
    if flake8 app.py tests/ --max-line-length=100 --extend-ignore=E203,W503; then
        echo -e "${GREEN}✅ Flake8 linting passed${NC}"
    else
        echo -e "${YELLOW}⚠️ Flake8 linting completed with issues${NC}"
    fi
    
    return 0
}

# Function to run all tests
run_all_tests() {
    local failed=0
    local passed=0
    local test_results=()
    
    echo -e "${BLUE}Running complete test suite...${NC}"
    echo
    
    # Install dependencies
    if install_dependencies; then
        ((passed++))
        test_results+=("✅ Dependencies installation")
    else
        ((failed++))
        test_results+=("❌ Dependencies installation")
    fi
    
    # Run linting
    if run_linting; then
        ((passed++))
        test_results+=("✅ Code linting")
    else
        ((failed++))
        test_results+=("❌ Code linting")
    fi
    
    # Run unit tests
    if run_unit_tests; then
        ((passed++))
        test_results+=("✅ Unit tests")
    else
        ((failed++))
        test_results+=("❌ Unit tests")
    fi
    
    # Run integration tests
    if run_integration_tests; then
        ((passed++))
        test_results+=("✅ Integration tests")
    else
        ((failed++))
        test_results+=("❌ Integration tests")
    fi
    
    # Run security tests
    if run_security_tests; then
        ((passed++))
        test_results+=("✅ Security tests")
    else
        ((failed++))
        test_results+=("❌ Security tests")
    fi
    
    # Run performance tests
    if run_performance_tests; then
        ((passed++))
        test_results+=("✅ Performance tests")
    else
        ((failed++))
        test_results+=("❌ Performance tests")
    fi
    
    # Run coverage analysis
    if run_coverage_analysis; then
        ((passed++))
        test_results+=("✅ Coverage analysis")
    else
        ((failed++))
        test_results+=("❌ Coverage analysis")
    fi
    
    # Print summary
    echo
    echo -e "${BLUE}=================================================================${NC}"
    echo -e "${BLUE}                         TEST SUMMARY                           ${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    echo -e "Total test categories: $((passed + failed))"
    echo -e "${GREEN}Passed: ${passed}${NC}"
    echo -e "${RED}Failed: ${failed}${NC}"
    echo
    
    echo -e "${BLUE}Test Results:${NC}"
    for result in "${test_results[@]}"; do
        echo -e "  $result"
    done
    
    echo
    if [ ${failed} -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
        return 0
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        return 1
    fi
}

# Function to run specific test file
run_specific_test() {
    local test_file=$1
    echo -e "${YELLOW}Running specific test: ${test_file}${NC}"
    
    cd "$BASE_DIR"
    
    if [ -f "$test_file" ]; then
        if pytest "$test_file" -v --tb=short; then
            echo -e "${GREEN}✅ Test ${test_file} passed${NC}"
        else
            echo -e "${RED}❌ Test ${test_file} failed${NC}"
        fi
    else
        echo -e "${RED}❌ Test file ${test_file} not found${NC}"
        return 1
    fi
}

# Main script logic
case "${1:-all}" in
    "all")
        run_all_tests
        ;;
    "unit")
        install_dependencies && run_unit_tests
        ;;
    "integration")
        install_dependencies && run_integration_tests
        ;;
    "security")
        install_dependencies && run_security_tests
        ;;
    "performance")
        install_dependencies && run_performance_tests
        ;;
    "coverage")
        install_dependencies && run_coverage_analysis
        ;;
    "lint")
        install_dependencies && run_linting
        ;;
    "install")
        install_dependencies
        ;;
    "clean")
        echo -e "${YELLOW}Cleaning test artifacts...${NC}"
        cd "$BASE_DIR"
        rm -rf htmlcov/
        rm -f coverage_output.txt
        rm -f bandit_report.json
        rm -f safety_report.txt
        rm -f .coverage
        echo -e "${GREEN}✅ Test artifacts cleaned${NC}"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  all            Run complete test suite (default)"
        echo "  unit           Run unit tests only"
        echo "  integration    Run integration tests only"
        echo "  security       Run security tests and scans"
        echo "  performance    Run performance tests only"
        echo "  coverage       Run coverage analysis"
        echo "  lint           Run code linting"
        echo "  install        Install test dependencies"
        echo "  clean          Clean test artifacts"
        echo "  help           Show this help message"
        echo
        echo "Specific test files:"
        echo "  tests/unit/test_app.py"
        echo "  tests/unit/test_security.py"
        echo "  tests/unit/test_performance_metrics.py"
        echo "  tests/integration/test_aap_integration.py"
        ;;
    tests/*)
        install_dependencies && run_specific_test "$1"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

exit $?