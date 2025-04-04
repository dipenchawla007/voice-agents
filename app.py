from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import json
import time
import random
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_url_path='')
CORS(app)  # Enable CORS for all routes

# In-memory storage for sessions
sessions = {}
customers = {}
audio_files = {}

# Define audio directory
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_files')

# Check for TTS and STT capabilities
HAS_DEEPGRAM_STT = False

# Try to initialize basic audio packages
try:
    import numpy as np
    from scipy.io import wavfile
    print("Basic audio packages are available")
    
    # Initialize Cartesia TTS at startup (on main thread)
    cartesia_tts = None
    cartesia_plugin_available = False
    http_session = None
    
    try:
        from livekit.plugins import cartesia
        
        # Use the new API key directly
        NEW_API_KEY = "sk_car_NATiqbZgreWaL8cTSsVbRL"
        print(f"Initializing Cartesia with API Key: {NEW_API_KEY[:8]}...")
        
        # Create and initialize aiohttp session
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def create_session():
            return aiohttp.ClientSession()
            
        http_session = loop.run_until_complete(create_session())
        
        # Create a completely new TTS instance with the new API key
        async def initialize_tts():
            try:
                # Create a session for testing
                async with aiohttp.ClientSession() as test_session:
                    # Create TTS test instance with its own session
                    test_tts = cartesia.TTS(
                        api_key=NEW_API_KEY,
                        http_session=test_session
                    )
                    
                    # Test the API key
                    stream = test_tts.stream()
                    stream.push_text("Hello")
                    stream.end_input()
                    
                    # Try to get the first chunk
                    async for event in stream:
                        print("Successfully validated Cartesia API key!")
                        return True, test_tts
                        break
                        
                    return True, test_tts
            except Exception as e:
                print(f"Error testing Cartesia API: {e}")
                if "401" in str(e):
                    return False, None
                return False, None
        
        # Run the initialization
        api_valid, new_tts = loop.run_until_complete(initialize_tts())
        
        if api_valid and new_tts:
            cartesia_tts = cartesia.TTS(
                api_key=NEW_API_KEY,
                http_session=http_session
            )
            cartesia_plugin_available = True
            print("Successfully initialized Cartesia TTS plugin with the new API key")
        else:
            cartesia_plugin_available = False
            print("WARNING: Cartesia TTS will be disabled due to invalid API key")
    except Exception as e:
        print(f"Failed to initialize Cartesia TTS plugin: {e}")
        cartesia_plugin_available = False
        # Clean up the session if initialization failed
        if http_session:
            loop.run_until_complete(http_session.close())
except ImportError as e:
    print(f"Warning: Basic audio packages not available: {e}")

# Try to initialize Deepgram STT
try:
    import requests
    if 'DEEPGRAM_API_KEY' in os.environ:
        HAS_DEEPGRAM_STT = True
        print("Deepgram STT is available")
    else:
        print("No Deepgram API key found, STT functionality will be limited")
except ImportError:
    print("Warning: Requests package not available, STT functionality will be limited")

# Agent types and their specialized behaviors
AGENT_TYPES = ["greeter", "technical", "billing", "general", "escalation"]

# Simulated responses for different agent types
AGENT_RESPONSES = {
    "greeter": [
        "Hello! Welcome to our service. How can I assist you today?",
        "Welcome! I'm your initial contact agent. What brings you here today?",
        "Hi there! I'm here to help you get started. What can I do for you?"
    ],
    "technical": [
        "I understand you're having a technical issue. Could you describe what's happening?",
        "Let me help troubleshoot that for you. Have you tried restarting the device?",
        "I'll help solve this technical problem. Can you tell me what steps you've already taken?"
    ],
    "billing": [
        "I can help with your billing question. Which subscription are you inquiring about?",
        "I'll assist with your payment concern. When did you notice the issue?",
        "Let me look into your billing details. Could you verify your account information?"
    ],
    "general": [
        "I can provide information about our services. What would you like to know?",
        "I'm happy to answer your general questions. What information are you looking for?",
        "I can help with general inquiries about our products and services. What do you need?"
    ],
    "escalation": [
        "I understand your concern requires special attention. I'm a senior agent here to help.",
        "I'm sorry to hear about the difficulties. As a manager, I'll personally ensure this gets resolved.",
        "Thank you for your patience. I'm a specialized agent who can address your more complex concerns."
    ]
}

# Directory for storing generated audio files
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Route for serving static files (HTML, JS, etc.)
@app.route('/')
def serve_index():
    # Use absolute path to ensure we can find the file
    root_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(root_dir, 'multi_tenant_system.html')

@app.route('/<path:path>')
def serve_static(path):
    # Use absolute path for all static files
    root_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(root_dir, path)

# API endpoint for connecting to the multi-tenant system
@app.route('/multi-tenant-connect', methods=['POST'])
def connect():
    data = request.json
    customer_id = data.get('customer_id')
    session_id = data.get('session_id')
    
    if not customer_id or not session_id:
        return jsonify({"success": False, "error": "Missing customer_id or session_id"})
    
    # Store session info
    sessions[session_id] = {
        "customer_id": customer_id,
        "agent_type": "greeter",
        "created_at": time.time(),
        "history": []
    }
    
    if customer_id not in customers:
        customers[customer_id] = {
            "sessions": [session_id],
            "preferences": {}
        }
    else:
        customers[customer_id]["sessions"].append(session_id)
    
    return jsonify({"success": True, "message": "Connected successfully"})

# API endpoint for disconnecting from the multi-tenant system
@app.route('/multi-tenant-disconnect', methods=['POST'])
def disconnect():
    data = request.json
    customer_id = data.get('customer_id')
    session_id = data.get('session_id')
    
    if not customer_id or not session_id:
        return jsonify({"success": False, "error": "Missing customer_id or session_id"})
    
    if session_id in sessions:
        del sessions[session_id]
        
    if customer_id in customers and session_id in customers[customer_id]["sessions"]:
        customers[customer_id]["sessions"].remove(session_id)
    
    return jsonify({"success": True, "message": "Disconnected successfully"})

# Main endpoint for handling messages and agent interactions
@app.route('/multi-tenant-message', methods=['POST'])
def handle_message():
    data = request.json
    customer_id = data.get('customer_id')
    session_id = data.get('session_id')
    message = data.get('message', '')
    current_agent_type = data.get('agent_type', 'greeter')
    is_interruption = data.get('is_interruption', False)
    
    if not customer_id or not session_id:
        return jsonify({"success": False, "error": "Missing customer_id or session_id"})
    
    if session_id not in sessions:
        return jsonify({"success": False, "error": "Invalid session"})
    
    # Log the incoming message
    sessions[session_id]["history"].append({
        "role": "user",
        "content": message,
        "timestamp": time.time()
    })
    
    # Determine if we need to change agent type based on message content
    new_agent_type = determine_agent_type(message, current_agent_type)
    agent_changed = new_agent_type != current_agent_type
    
    # Update session with new agent type if changed
    if agent_changed:
        sessions[session_id]["agent_type"] = new_agent_type
    
    # Generate response from appropriate agent
    agent_response = generate_agent_response(message, new_agent_type, is_interruption)
    
    # Log the agent response
    sessions[session_id]["history"].append({
        "role": "agent",
        "content": agent_response,
        "agent_type": new_agent_type,
        "timestamp": time.time()
    })
    
    response_data = {
        "success": True,
        "response": agent_response,
        "agent_type": new_agent_type
    }
    
    return jsonify(response_data)

# Endpoint for text-to-speech conversion
@app.route('/local-tts', methods=['POST'])
def text_to_speech():
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'echo')  # Default voice
    
    if not text:
        return jsonify({"success": False, "error": "Missing text"})
    
    print(f"TTS Request received for text: '{text}' with voice: {voice}")
    
    # Generate a unique ID for the audio file
    file_id = str(uuid.uuid4())
    print(f"Generated file ID: {file_id}")
    
    # Store metadata about the audio
    audio_files[file_id] = {
        "text": text,
        "voice": voice,
        "created_at": time.time()
    }
    
    # Define path for the audio file
    os.makedirs(AUDIO_DIR, exist_ok=True)
    file_path = os.path.join(AUDIO_DIR, f"{file_id}.wav")
    audio_path = f"/audio/{file_id}.wav"
    print(f"Audio will be saved to: {file_path}")
    
    # Generate a guaranteed working audio as a fallback first
    try:
        _generate_simple_audio(text, file_path)
        print(f"Generated simple fallback audio as a safety measure")
    except Exception as e:
        print(f"Failed to generate simple fallback audio: {e}")
    
    # Try to use Cartesia TTS plugin directly
    tts_success = False
    try:
        # Check if we have a valid, globally initialized Cartesia TTS plugin
        if cartesia_plugin_available and cartesia_tts is not None:
            # Only attempt Cartesia if the API key was validated at startup
            print("Using globally initialized Cartesia TTS plugin...")
            import asyncio
            
            # Map voice type to simple string names for Cartesia plugin
            # Let the plugin handle the mapping to actual voice IDs
            if voice == "echo":
                voice_id = "echo"
            elif voice == "agent":
                voice_id = "alloy"
            else:
                voice_id = "echo"
            
            # Update voice setting for this request
            cartesia_tts.voice = voice_id
            print(f"Set Cartesia TTS voice to: {voice_id}")
            
            # Always create a new event loop for the worker thread
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception as e:
                print(f"Error creating event loop: {e}")
                raise
            
            # Define async function to synthesize
            async def synthesize_audio():
                try:
                    # Use the built-in plugin functionality directly
                    print(f"Using Cartesia plugin directly with voice: {voice_id}")
                    
                    # Set up the TTS options with the specific voice
                    if voice_id != cartesia_tts._opts.voice:
                        print(f"Updating Cartesia voice to: {voice_id}")
                        cartesia_tts.update_options(voice=voice_id)
                    
                    # Direct API approach to avoid task issues
                    import aiohttp
                    import base64
                    import json
                    
                    # Use the API parameters directly from the plugin's options
                    api_key = cartesia_tts._opts.api_key
                    model = cartesia_tts._opts.model
                    sample_rate = cartesia_tts._opts.sample_rate
                    base_url = cartesia_tts._opts.base_url
                    
                    # Map the voice name to the specific Cartesia voice ID
                    # Using exact voice IDs provided by the user
                    voice_mapping = {
                        "echo": "6f84f4b8-58a2-430c-8c79-688dad597532",  # Brooke (friendly American female)
                        "agent": "1f1d2b29-7438-4796-9b70-9e5a76c75f5e",   # Griffin (deep British male) - using a placeholder ID
                        "alloy": "694f9389-aac1-45b6-b726-9d9369183238",  # Special voice for billing agent
                        "default": "bf0a246a-8642-498a-9950-80c35e9276b5"  # Sophie (calm conversational female)
                    }
                    
                    # Use the mapped voice or default to Sophie
                    cartesia_voice_id = voice_mapping.get(voice_id, voice_mapping["default"])
                    print(f"Mapped voice '{voice_id}' to Cartesia voice ID: {cartesia_voice_id}")
                    
                    url = f"{base_url}/tts/bytes"
                    headers = {
                        "X-API-Key": api_key,
                        "Cartesia-Version": "2024-06-10",
                        "Content-Type": "application/json"
                    }
                    
                    # Prepare the request payload using the ID mode with specific voice IDs
                    payload = {
                        "transcript": text,
                        "model_id": model,
                        "voice": {"mode": "id", "id": cartesia_voice_id},
                        "output_format": {
                            "container": "wav",
                            "encoding": "pcm_s16le",
                            "sample_rate": sample_rate
                        }
                    }
                    
                    print(f"Making direct API request to Cartesia with voice: {voice}")
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, headers=headers, json=payload) as response:
                            if response.status == 200:
                                audio_data = await response.read()
                                print(f"Successfully received {len(audio_data)} bytes from Cartesia API")
                                return audio_data
                            else:
                                error_text = await response.text()
                                print(f"Cartesia API error: {response.status} - {error_text}")
                                return None
                except Exception as inner_err:
                    print(f"Error during Cartesia synthesis: {inner_err}")
                    return None
            
            # Run the async function
            print("Running Cartesia synthesis...")
            audio_data = loop.run_until_complete(synthesize_audio())
        else:
            print("Cartesia plugin was not initialized at startup")
            raise Exception("Cartesia plugin not available")
        
        if audio_data and len(audio_data) > 0:
            print(f"Received audio data of length: {len(audio_data)} bytes")
            print(f"First few bytes: {audio_data[:20]}")
            
            # Save the audio file
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            print(f"Successfully saved Cartesia audio to: {file_path}")
            tts_success = True
            
            # Calculate approximate duration (assuming 16kHz sample rate, 16-bit samples, mono)
            audio_duration = len(audio_data) / (16000 * 2)  # bytes / (sample_rate * bytes_per_sample)
            
            return jsonify({
                "success": True,
                "audio_file": audio_path,
                "duration": audio_duration
            })
        else:
            print("No audio data received from Cartesia plugin")
                
    except ImportError as ie:
        print(f"Could not import Cartesia plugin: {ie}")
    except Exception as e:
        import traceback
        print(f"Error using Cartesia TTS plugin: {e}")
        print(traceback.format_exc())
    
    # If Cartesia TTS failed, try Google TTS as fallback
    if not tts_success:
        try:
            from gtts import gTTS
            print("Falling back to Google Text-to-Speech service...")
            
            # Choose voice based on input
            lang = 'en-uk' if voice == 'echo' else 'en-us'
            tts = gTTS(text=text, lang=lang, slow=False)
            
            # Save to a temporary file first
            temp_mp3 = file_path.replace('.wav', '.mp3')
            tts.save(temp_mp3)
            print(f"Saved Google TTS MP3 to {temp_mp3}")
            
            # Try to convert to WAV if possible
            try:
                # Use system command for reliable conversion
                import subprocess
                cmd = f"ffmpeg -y -i {temp_mp3} -acodec pcm_s16le -ar 44100 -ac 1 {file_path}"
                subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
                print(f"Converted to WAV using ffmpeg: {file_path}")
                tts_success = True
            except Exception as conv_err:
                print(f"ffmpeg conversion failed: {conv_err}, using MP3 directly")
                # If conversion fails, just use the MP3
                file_path = temp_mp3
                audio_path = f"/audio/{os.path.basename(file_path)}"
                tts_success = True
        except Exception as google_err:
            print(f"Google TTS failed: {google_err}")

    
    # Verify the audio file exists
    print(f"Checking if audio file exists at {file_path}")
    if os.path.exists(file_path):
        print(f"Audio file exists with size: {os.path.getsize(file_path)} bytes")
    else:
        print(f"WARNING: Audio file does not exist! Generating fallback.")
        # Final fallback - generate basic audio if nothing else worked
        _generate_simple_audio(text, file_path)
    
    # Calculate duration based on file or approximation
    try:
        # Try to get actual duration if possible
        from scipy.io import wavfile
        import numpy as np
        
        if file_path.endswith('.wav'):
            sample_rate, data = wavfile.read(file_path)
            duration = len(data) / sample_rate
        else:
            # Estimate for MP3 or other formats
            duration = len(text) * 0.08  # ~80ms per character
    except Exception:
        # Fallback duration calculation
        duration = len(text) * 0.08
    
    print(f"Final audio duration: {duration:.2f} seconds")
    
    return jsonify({
        "success": True,
        "audio_file": audio_path,
        "duration": duration
    })

# Helper function to generate fallback audio
def _generate_simple_audio(text, file_path):
    """Generate a simple audio file as a fallback"""
    from scipy.io import wavfile
    import numpy as np
    
    # Create a placeholder audio file
    sample_rate = 44100
    duration = max(1, len(text) * 0.08)  # Base duration on text length, minimum 1 second
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Create a more pleasant sound with varying frequency to simulate speech
    frequencies = np.linspace(300, 700, int(sample_rate * duration))
    frequencies = frequencies + 100 * np.sin(2 * np.pi * 0.5 * t)  # Add some variation
    audio_data = 0.5 * np.sin(2 * np.pi * frequencies * t / sample_rate)
    audio_data = (audio_data * 32767).astype(np.int16)  # Convert to 16-bit PCM
    
    # Save as WAV file
    wavfile.write(file_path, sample_rate, audio_data)
    
    print(f"Generated fallback audio for text: '{text}'")
    return duration

# Speech-to-text endpoint using Deepgram
@app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    import os
    import asyncio
    import tempfile
    import numpy as np
    from scipy.io import wavfile
    
    if 'audio' not in request.files:
        return jsonify({"success": False, "error": "No audio file provided"})
    
    audio_file = request.files['audio']
    
    try:
        # Try to use Deepgram plugin if it's installed
        deepgram_available = False
        try:
            from livekit.plugins.deepgram import stt as deepgram_stt
            from livekit.agents import AudioBuffer
            deepgram_available = True
            print("Using Deepgram STT plugin")
        except ImportError:
            print("Deepgram STT plugin not found, trying direct API call")
        
        # Save the audio to a temporary file
        temp_path = os.path.join(AUDIO_DIR, f"temp_{uuid.uuid4()}.wav")
        audio_file.save(temp_path)
        
        if deepgram_available and 'DEEPGRAM_API_KEY' in os.environ:
            try:
                # Use the Deepgram plugin
                async def transcribe_with_plugin():
                    # Create a Deepgram STT instance with appropriate settings
                    stt_service = deepgram_stt.STT(
                        model="nova-2-general",  # Modern Deepgram model
                        language="en-US",
                        punctuate=True,
                        smart_format=True
                    )
                    
                    # Load audio from the temporary file
                    sample_rate, audio_data = wavfile.read(temp_path)
                    
                    # Convert to float if needed for the plugin
                    if audio_data.dtype == np.int16:
                        audio_data = audio_data.astype(np.float32) / 32768.0
                    
                    # Create an audio buffer
                    buffer = AudioBuffer(
                        audio=audio_data,
                        sample_rate=sample_rate,
                        num_channels=1 if len(audio_data.shape) == 1 else audio_data.shape[1]
                    )
                    
                    # Perform speech recognition
                    result = await stt_service._recognize_impl(buffer)
                    return result.alternatives[0].text if result.alternatives else ""
                
                # Run the async function
                transcript = asyncio.run(transcribe_with_plugin())
                print(f"Transcribed with Deepgram plugin: '{transcript}'")
                
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
                return jsonify({
                    "success": True,
                    "text": transcript
                })
                
            except Exception as e:
                print(f"Error using Deepgram plugin: {e}, falling back to direct API")
                # Fall through to the direct API call
        
        # If plugin not available or failed, use direct API call
        if 'DEEPGRAM_API_KEY' in os.environ:
            import requests
            deepgram_api_key = os.environ.get('DEEPGRAM_API_KEY')
            
            # Call Deepgram API directly
            headers = {
                "Authorization": f"Token {deepgram_api_key}"
            }
            
            url = "https://api.deepgram.com/v1/listen?model=nova-2&language=en-US&punctuate=true"
            
            with open(temp_path, 'rb') as f:
                response = requests.post(url, headers=headers, data=f)
            
            # Clean up the temporary file
            try:
                os.remove(temp_path)
            except:
                pass
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('transcript', '')
                
                return jsonify({
                    "success": True,
                    "text": transcript
                })
            else:
                return jsonify({"success": False, "error": f"Deepgram API error: {response.text}"})
        else:
            return jsonify({"success": False, "error": "No Deepgram API key found"})
            
    except Exception as e:
        return jsonify({"success": False, "error": f"Error processing speech: {str(e)}"})

# Route to serve audio files
@app.route('/audio/<path:file_id>')
def serve_audio(file_id):
    print(f"Audio requested: {file_id}")
    
    # Handle URL query parameters if present
    if '?' in file_id:
        file_id = file_id.split('?')[0]
        print(f"Removed query parameters, now using: {file_id}")
    
    # Create audio directory if it doesn't exist
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    # Extract the actual file name without extension
    file_name_parts = file_id.split('.')
    file_id_base = file_name_parts[0]
    extension = file_name_parts[1] if len(file_name_parts) > 1 else 'wav'
    
    # Path to the audio file
    file_path = os.path.join(AUDIO_DIR, f"{file_id_base}.{extension}")
    print(f"Looking for audio file at: {file_path}")
    
    # Check if the file exists, if not generate a fallback tone
    if not os.path.exists(file_path):
        print(f"Audio file not found, generating fallback tone")
        try:
            from scipy.io import wavfile
            import numpy as np
            
            # Generate a simple fallback tone
            sample_rate = 44100
            duration = 2.0  # 2 seconds
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            fallback_data = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz = A4
            fallback_data = (fallback_data * 32767).astype(np.int16)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save the fallback tone
            wavfile.write(file_path, sample_rate, fallback_data)
            print(f"Fallback tone saved to: {file_path}")
        except Exception as e:
            print(f"Error generating fallback tone: {e}")
            return jsonify({"error": "Could not generate audio"}), 500
    else:
        print(f"Found audio file: {file_path}, size: {os.path.getsize(file_path)} bytes")
    
    # Serve the audio file directly using Flask's send_file for better control
    try:
        from flask import send_file
        
        # Simplified audio serving with only compatible parameters
        response = send_file(
            file_path,
            mimetype='audio/wav'
        )
        
        # Add Cache-Control header to prevent caching issues
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f"Serving audio file with headers: {response.headers}")
        return response
    except Exception as e:
        import traceback
        print(f"Error serving audio file: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# Helper function to determine which agent should handle a message
def determine_agent_type(message, current_agent_type):
    # Simple keyword-based routing rules
    message = message.lower()
    
    # Check for explicit transfer requests
    if "speak to manager" in message or "supervisor" in message or "escalate" in message:
        return "escalation"
    
    # Check for billing keywords
    if "bill" in message or "payment" in message or "charge" in message or "refund" in message or "subscription" in message:
        return "billing"
    
    # Check for technical keywords
    if "error" in message or "problem" in message or "not working" in message or "help me fix" in message or "broken" in message:
        return "technical"
    
    # Check for general information keywords
    if "information" in message or "details" in message or "tell me about" in message or "what is" in message:
        return "general"
    
    # Stay with current agent if no transfer needed
    return current_agent_type

# Helper function to generate agent responses
def generate_agent_response(message, agent_type, is_interruption):
    # Handle interruptions specially
    if is_interruption:
        return "I understand you wanted to say something. Please go ahead."
    
    # Get a random response for the specified agent type
    responses = AGENT_RESPONSES.get(agent_type, AGENT_RESPONSES["greeter"])
    return random.choice(responses)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True)
