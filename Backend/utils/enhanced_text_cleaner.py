#!/usr/bin/env python3
"""
Enhanced text cleaning utilities for Gemini API responses.
Handles comprehensive formatting cleanup for all data types.
"""

import re
import json
from typing import Dict, List, Any, Union


def clean_response_text(text: str) -> str:
    """
    Enhanced text cleaning with comprehensive markdown and formatting removal
    
    Args:
        text: Raw text that may contain various formatting
        
    Returns:
        Cleaned text without formatting artifacts
    """
    if not text or not isinstance(text, str):
        return text
    
    # Remove code blocks (```code```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove headers (# ## ### etc.)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove bold markdown (**text** and __text__)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    
    # Remove italic markdown (*text* and _text_)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    # Remove strikethrough (~~text~~)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    
    # Remove links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove bullet points and list markers
    text = re.sub(r'^[\s]*[-*+•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Handle various newline formats
    text = text.replace('\\n', ' ')
    text = text.replace('\n', ' ')
    text = text.replace('\\r', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\\t', ' ')
    text = text.replace('\t', ' ')
    
    # Remove escape characters
    text = text.replace('\\', '')
    
    # Clean quotes and apostrophes
    text = text.replace("\'", "'")
    text = text.replace("\\'", "'")
    text = text.replace('\"', '"')
    text = text.replace('\\"', '"')
    text = text.replace('"', '')
    text = text.replace(''', "'")
    text = text.replace(''', "'")

    
    # Remove extra punctuation artifacts
    text = re.sub(r'[*_~`#]+', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def clean_response_list(response_list: List[Any]) -> List[Any]:
    """
    Clean all items in a list recursively
    
    Args:
        response_list: List containing mixed data types
        
    Returns:
        List with cleaned string values
    """
    cleaned_list = []
    for item in response_list:
        if isinstance(item, str):
            cleaned_list.append(clean_response_text(item))
        elif isinstance(item, dict):
            cleaned_list.append(clean_response_dict(item))
        elif isinstance(item, list):
            cleaned_list.append(clean_response_list(item))
        else:
            cleaned_list.append(item)
    return cleaned_list


def clean_response_dict(response_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced recursive cleaning for all data types in dictionary
    
    Args:
        response_dict: Dictionary containing response data
        
    Returns:
        Dictionary with cleaned values
    """
    if isinstance(response_dict, dict):
        cleaned_dict = {}
        for key, value in response_dict.items():
            # Clean the key itself if it's a string
            clean_key = clean_response_text(key) if isinstance(key, str) else key
            
            if isinstance(value, str):
                cleaned_dict[clean_key] = clean_response_text(value)
            elif isinstance(value, dict):
                cleaned_dict[clean_key] = clean_response_dict(value)
            elif isinstance(value, list):
                cleaned_dict[clean_key] = clean_response_list(value)
            else:
                cleaned_dict[clean_key] = value
        return cleaned_dict
    elif isinstance(response_dict, str):
        return clean_response_text(response_dict)
    elif isinstance(response_dict, list):
        return clean_response_list(response_dict)
    else:
        return response_dict


def clean_any_response(response: Any) -> Any:
    """
    Universal cleaner that handles any data type
    
    Args:
        response: Any type of response data
        
    Returns:
        Cleaned response maintaining original structure
    """
    if isinstance(response, str):
        return clean_response_text(response)
    elif isinstance(response, dict):
        return clean_response_dict(response)
    elif isinstance(response, list):
        return clean_response_list(response)
    else:
        return response


def extract_json_from_text(text: str) -> Union[Dict, List, str]:
    """
    Extract JSON from text that might contain markdown or other formatting
    
    Args:
        text: Text that might contain JSON
        
    Returns:
        Parsed JSON object or cleaned text if no valid JSON found
    """
    if not text:
        return text
    
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON without code blocks
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # If no JSON found, return cleaned text
    return clean_response_text(text)


def sanitize_for_frontend(response: Any) -> Any:
    """
    Complete sanitization pipeline for frontend consumption
    
    Args:
        response: Raw response from Gemini API
        
    Returns:
        Fully sanitized response ready for frontend
    """
    # First try to extract JSON if it's embedded in text
    if isinstance(response, str):
        response = extract_json_from_text(response)
    
    # Then clean all formatting
    cleaned_response = clean_any_response(response)
    
    return cleaned_response