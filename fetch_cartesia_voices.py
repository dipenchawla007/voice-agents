#!/usr/bin/env python3
import requests
import json
import sys

# Cartesia API configuration
API_KEY = "sk_car_NATiqbZgreWaL8cTSsVbRL"  # Using our existing key
API_VERSION = "2024-11-13"
API_URL = "https://api.cartesia.ai/voices"

def main():
    """Fetch and display voice information"""
    print("Fetching voices with emotions from Cartesia API...")
    
    # Make API request (we'll only fetch one page)
    response = requests.get(
        API_URL,
        headers={
            "X-API-Key": API_KEY,
            "Cartesia-Version": API_VERSION,
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code != 200:
        print(f"Error fetching voices: {response.status_code} - {response.text}")
        sys.exit(1)
    
    data = response.json()
    voices = data.get('data', [])
    
    print(f"\nFound {len(voices)} voices with emotional descriptions:\n")
    
    # Group voices by their emotional characteristics
    calm_voices = []
    deep_voices = []
    smooth_voices = []
    friendly_voices = []
    bright_voices = []
    confident_voices = []
    
    for voice in voices:
        voice_id = voice.get('id', '')
        name = voice.get('name', '')
        description = voice.get('description', '').lower()
        gender = voice.get('gender', '')
        language = voice.get('language', '')
        
        voice_info = {
            'id': voice_id,
            'name': name,
            'description': voice.get('description', ''),
            'gender': gender,
            'language': language
        }
        
        # Categorize based on description
        if 'calm' in description:
            calm_voices.append(voice_info)
        if 'deep' in description:
            deep_voices.append(voice_info)
        if 'smooth' in description:
            smooth_voices.append(voice_info)
        if 'friendly' in description or 'warm' in description:
            friendly_voices.append(voice_info)
        if 'bright' in description or 'expressive' in description:
            bright_voices.append(voice_info)
        if 'confident' in description or 'authoritative' in description:
            confident_voices.append(voice_info)
    
    # Print by emotion category
    print("## Calm Voices:")
    if calm_voices:
        print("| Voice ID | Name | Description | Gender | Language |")
        print("|----------|------|-------------|--------|----------|")
        for voice in calm_voices:
            print(f"| {voice['id']} | {voice['name']} | {voice['description']} | {voice['gender']} | {voice['language']} |")
    else:
        print("No calm voices found.")
    
    print("\n## Deep Voices:")
    if deep_voices:
        print("| Voice ID | Name | Description | Gender | Language |")
        print("|----------|------|-------------|--------|----------|")
        for voice in deep_voices:
            print(f"| {voice['id']} | {voice['name']} | {voice['description']} | {voice['gender']} | {voice['language']} |")
    else:
        print("No deep voices found.")
    
    print("\n## Smooth Voices:")
    if smooth_voices:
        print("| Voice ID | Name | Description | Gender | Language |")
        print("|----------|------|-------------|--------|----------|")
        for voice in smooth_voices:
            print(f"| {voice['id']} | {voice['name']} | {voice['description']} | {voice['gender']} | {voice['language']} |")
    else:
        print("No smooth voices found.")
    
    print("\n## Friendly/Warm Voices:")
    if friendly_voices:
        print("| Voice ID | Name | Description | Gender | Language |")
        print("|----------|------|-------------|--------|----------|")
        for voice in friendly_voices:
            print(f"| {voice['id']} | {voice['name']} | {voice['description']} | {voice['gender']} | {voice['language']} |")
    else:
        print("No friendly/warm voices found.")
    
    print("\n## Bright/Expressive Voices:")
    if bright_voices:
        print("| Voice ID | Name | Description | Gender | Language |")
        print("|----------|------|-------------|--------|----------|")
        for voice in bright_voices:
            print(f"| {voice['id']} | {voice['name']} | {voice['description']} | {voice['gender']} | {voice['language']} |")
    else:
        print("No bright/expressive voices found.")
    
    print("\n## Confident/Authoritative Voices:")
    if confident_voices:
        print("| Voice ID | Name | Description | Gender | Language |")
        print("|----------|------|-------------|--------|----------|")
        for voice in confident_voices:
            print(f"| {voice['id']} | {voice['name']} | {voice['description']} | {voice['gender']} | {voice['language']} |")
    else:
        print("No confident/authoritative voices found.")

if __name__ == "__main__":
    main()
