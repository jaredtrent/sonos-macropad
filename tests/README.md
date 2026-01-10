# Development Tools

This directory contains testing infrastructure and development utilities for sonos-macropad.

## Test Suite

The test suite includes 85 tests covering all functionality:

```bash
# Run all tests
cd tests
python3 -m pytest -v

# Run tests quietly
python3 -m pytest --tb=no -q

# Run specific test file
python3 -m pytest test_04_security_hardening.py -v
```

## Test Categories

- **Basic Functionality** - Configuration validation and core logic
- **Security Hardening** - Path traversal protection and input validation  
- **Validation Accuracy** - Error message accuracy and validation logic
- **Script Generation** - Action script creation and templating
- **HTTP Response Handling** - API communication and error handling
- **Key Mappings** - Input device mapping and action routing
- **Grouping & Volume** - Multi-room audio control logic
- **Edge Cases** - Boundary conditions and error scenarios
- **Behavioral Integration** - End-to-end functionality testing
- **Production Readiness** - Security fixes and code quality

## Test Runner

Run tests directly with pytest:

## Coverage

The test suite validates:
- All validation functions and error conditions
- Security vulnerabilities and fixes
- Volume accumulation and multi-room logic
- Device discovery and Bluetooth reconnection
- Script generation and execution paths
- Configuration parsing and validation accuracy
