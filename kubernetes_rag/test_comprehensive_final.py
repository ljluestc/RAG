#!/usr/bin/env python3
"""
Comprehensive Test Suite for Kubernetes RAG System
This script runs all tests and generates comprehensive coverage reports.
"""

import os
import subprocess
import sys
from pathlib import Path

# Ensure the test_config_final.py is loaded to set environment variables
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
import test_config_final  # noqa: E402, F401

# Add the src directory to the Python path
sys.path.insert(0, str(current_dir.parent / "src"))

# Define the root directory of the project
ROOT_DIR = Path(__file__).parent
KUBERNETES_RAG_DIR = ROOT_DIR
VENV_PYTHON = KUBERNETES_RAG_DIR / "venv" / "bin" / "python"
PYTEST_COMMAND = [str(VENV_PYTHON), "-m", "pytest"]

def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, cwd=KUBERNETES_RAG_DIR, capture_output=True, text=True)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    """Main test execution function."""
    print("🚀 Starting Comprehensive Test Suite for Kubernetes RAG System")
    print(f"Working directory: {KUBERNETES_RAG_DIR}")
    print(f"Python executable: {VENV_PYTHON}")
    
    # Test files to run (working tests only)
    test_files = [
        "tests/test_generation_working.py",
        "tests/test_ingestion_corrected.py", 
        "tests/test_utils_corrected.py",
        "tests/test_api_fixed.py",
        "tests/test_cli_fixed.py",
        "tests/test_performance_fixed.py"
    ]
    
    # Create reports directory
    reports_dir = KUBERNETES_RAG_DIR / "test_reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Run individual test files
    all_passed = True
    for test_file in test_files:
        if (KUBERNETES_RAG_DIR / test_file).exists():
            cmd = PYTEST_COMMAND + [
                test_file,
                "-v",
                "--tb=short",
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:test_reports/htmlcov",
                "--cov-report=xml:test_reports/coverage.xml",
                "--junitxml=test_reports/junit.xml"
            ]
            success = run_command(cmd, f"Running {test_file}")
            if not success:
                all_passed = False
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    # Run all tests together for overall coverage
    print(f"\n{'='*60}")
    print("Running All Tests Together for Overall Coverage")
    print(f"{'='*60}")
    
    cmd = PYTEST_COMMAND + [
        "tests/",
        "-v",
        "--tb=short",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:test_reports/htmlcov",
        "--cov-report=xml:test_reports/coverage.xml",
        "--junitxml=test_reports/junit.xml",
        "--maxfail=10"  # Stop after 10 failures
    ]
    
    success = run_command(cmd, "Running all tests together")
    if not success:
        all_passed = False
    
    # Generate detailed coverage report
    print(f"\n{'='*60}")
    print("Generating Detailed Coverage Report")
    print(f"{'='*60}")
    
    cmd = PYTEST_COMMAND + [
        "tests/",
        "--cov=src",
        "--cov-report=html:test_reports/detailed_coverage",
        "--cov-report=xml:test_reports/detailed_coverage.xml",
        "--quiet"
    ]
    
    run_command(cmd, "Generating detailed coverage report")
    
    # Check if coverage reports were generated
    coverage_files = [
        "test_reports/htmlcov/index.html",
        "test_reports/coverage.xml",
        "test_reports/junit.xml"
    ]
    
    print(f"\n{'='*60}")
    print("Test Results Summary")
    print(f"{'='*60}")
    
    for file_path in coverage_files:
        full_path = KUBERNETES_RAG_DIR / file_path
        if full_path.exists():
            print(f"✅ Generated: {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
    
    if all_passed:
        print("\n🎉 All tests passed successfully!")
        print(f"📊 Coverage reports available in: {reports_dir}")
        print(f"🌐 Open HTML coverage report: {reports_dir}/htmlcov/index.html")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        print(f"📊 Coverage reports available in: {reports_dir}")
        print(f"🌐 Open HTML coverage report: {reports_dir}/htmlcov/index.html")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
