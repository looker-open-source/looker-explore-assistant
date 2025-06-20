#!/usr/bin/env python3

"""
Test script for feedback detection functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_server import detect_feedback_pattern

def test_feedback_detection():
    """Test various feedback patterns"""
    
    print("Testing feedback detection patterns...")
    
    # Test 1: Simple feedback cycle
    prompt_history = [
        "Show me sales data",
        "This chart is wrong, I want a table instead", 
        "Perfect, that's exactly what I wanted"
    ]
    
    has_feedback, _ = detect_feedback_pattern(prompt_history, [], "Perfect, that's exactly what I wanted")
    print(f"Test 1 - Simple feedback cycle: {has_feedback} (expected: True)")
    
    # Test 2: No feedback pattern
    prompt_history = [
        "Show me sales data",
        "Show me customer data"
    ]
    
    has_feedback, _ = detect_feedback_pattern(prompt_history, [], "Show me customer data")
    print(f"Test 2 - No feedback: {has_feedback} (expected: False)")
    
    # Test 3: Feedback but no confirmation
    prompt_history = [
        "Show me sales data",
        "This is incorrect, fix it"
    ]
    
    has_feedback, _ = detect_feedback_pattern(prompt_history, [], "This is incorrect, fix it")
    print(f"Test 3 - Feedback but no confirmation: {has_feedback} (expected: False)")
    
    # Test 4: Confirmation but no prior feedback
    prompt_history = [
        "Show me sales data"
    ]
    
    has_feedback, _ = detect_feedback_pattern(prompt_history, [], "Thanks, that looks good")
    print(f"Test 4 - Confirmation but no feedback: {has_feedback} (expected: False)")
    
    # Test 5: Using thread messages
    prompt_history = ["Show me sales data"]
    thread_messages = [
        {"message": "This visualization is not right", "actor": "user"},
        {"message": "I've corrected it to show a table", "actor": "system"}
    ]
    
    has_feedback, _ = detect_feedback_pattern(prompt_history, thread_messages, "Great, much better!")
    print(f"Test 5 - Thread messages feedback: {has_feedback} (expected: True)")

if __name__ == "__main__":
    test_feedback_detection()
