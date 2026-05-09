"""
Sample API Requests

Sample requests for testing the Mutual Fund RAG ChatBot API endpoints.
Includes curl commands and Python examples for validation.
"""

import json
import requests
from typing import Dict, Any


# API Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


def test_health_endpoint():
    """Test the health check endpoint."""
    url = f"{BASE_URL}/health"
    
    print("=== Testing Health Endpoint ===")
    print(f"GET {url}")
    
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_meta_endpoint():
    """Test the API metadata endpoint."""
    url = f"{BASE_URL}/meta"
    
    print("\n=== Testing Meta Endpoint ===")
    print(f"GET {url}")
    
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat_endpoint_basic():
    """Test the chat endpoint with a basic query."""
    url = f"{BASE_URL}/chat"
    
    payload = {
        "query": "What is the expense ratio of HDFC Equity Fund?",
        "use_groq": "false",
        "top_k": 5,
        "include_metadata": True
    }
    
    print("\n=== Testing Chat Endpoint (Basic) ===")
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat_endpoint_with_filters():
    """Test the chat endpoint with filters."""
    url = f"{BASE_URL}/chat"
    
    payload = {
        "query": "What is the minimum investment amount?",
        "use_groq": "auto",
        "top_k": 3,
        "scheme_filter": "hdfc_equity",
        "section_filter": "Minimum Investment",
        "include_metadata": True
    }
    
    print("\n=== Testing Chat Endpoint (With Filters) ===")
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat_endpoint_groq():
    """Test the chat endpoint with Groq LLM."""
    url = f"{BASE_URL}/chat"
    
    payload = {
        "query": "Tell me about the risk level of HDFC Mid Cap Fund",
        "use_groq": "true",
        "top_k": 5,
        "include_metadata": True
    }
    
    print("\n=== Testing Chat Endpoint (Groq LLM) ===")
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat_endpoint_validation_errors():
    """Test the chat endpoint with validation errors."""
    url = f"{BASE_URL}/chat"
    
    # Test with empty query
    payload = {
        "query": "",
        "use_groq": "auto",
        "top_k": 5
    }
    
    print("\n=== Testing Chat Endpoint (Validation Error) ===")
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 422  # Validation error
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_metrics_endpoint():
    """Test the metrics endpoint."""
    url = f"{BASE_URL}/metrics"
    
    print("\n=== Testing Metrics Endpoint ===")
    print(f"GET {url}")
    
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def run_all_tests():
    """Run all API tests."""
    print("🧪 Running API Validation Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("API Metadata", test_meta_endpoint),
        ("Basic Chat", test_chat_endpoint_basic),
        ("Chat with Filters", test_chat_endpoint_with_filters),
        ("Chat with Groq", test_chat_endpoint_groq),
        ("Validation Error", test_chat_endpoint_validation_errors),
        ("Metrics", test_metrics_endpoint)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above.")


def generate_curl_commands():
    """Generate curl commands for manual testing."""
    commands = {
        "health": f"curl -X GET {BASE_URL}/health",
        "meta": f"curl -X GET {BASE_URL}/meta",
        "chat_basic": f'''curl -X POST {BASE_URL}/chat \\
  -H "Content-Type: application/json" \\
  -d '{{
    "query": "What is the expense ratio of HDFC Equity Fund?",
    "use_groq": "false",
    "top_k": 5,
    "include_metadata": true
  }}''',
        "chat_groq": f'''curl -X POST {BASE_URL}/chat \\
  -H "Content-Type: application/json" \\
  -d '{{
    "query": "Tell me about the risk level of HDFC Mid Cap Fund",
    "use_groq": "true",
    "top_k": 5,
    "include_metadata": true
  }}''',
        "chat_filters": f'''curl -X POST {BASE_URL}/chat \\
  -H "Content-Type: application/json" \\
  -d '{{
    "query": "What is the minimum investment amount?",
    "use_groq": "auto",
    "top_k": 3,
    "scheme_filter": "hdfc_equity",
    "section_filter": "Minimum Investment",
    "include_metadata": true
  }}''',
        "metrics": f"curl -X GET {BASE_URL}/metrics"
    }
    
    print("\n📋 Curl Commands for Manual Testing")
    print("=" * 50)
    
    for name, command in commands.items():
        print(f"\n# {name.replace('_', ' ').title()}")
        print(command)


if __name__ == "__main__":
    print("🚀 Mutual Fund RAG ChatBot API Test Suite")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and accessible")
        else:
            print("⚠️  Server responded but may have issues")
    except requests.exceptions.RequestException:
        print("❌ Server is not running or not accessible")
        print("Please start the server with: python -m backend.main")
        exit(1)
    
    # Run tests
    run_all_tests()
    
    # Generate curl commands
    generate_curl_commands()
