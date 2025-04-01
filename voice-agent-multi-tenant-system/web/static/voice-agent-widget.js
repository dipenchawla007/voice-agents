/**
 * Voice Agent Widget
 * Embed voice agents on any website with a simple script
 * 
 * Usage:
 * <script src="https://your-domain.com/static/voice-agent-widget.js" 
 *   data-company-id="COMPANY_ID" 
 *   data-agent-id="AGENT_ID">
 * </script>
 */

(function () {
    // Configuration
    const config = {
        apiBaseUrl: 'https://your-domain.com/api/v1',
        defaultButtonText: 'Talk to an Agent',
        defaultTheme: 'light',
        defaultPosition: 'bottom-right'
    };

    // Widget state
    let state = {
        initialized: false,
        connected: false,
        companyId: null,
        agentId: null,
        token: null,
        room: null,
        roomUrl: null,
        theme: null,
        position: null,
        micActive: false,
        speaking: false
    };

    // LiveKit client
    let room = null;
    let localTracks = [];

    // DOM elements
    let widgetContainer = null;
    let buttonEl = null;
    let widgetEl = null;
    let statusEl = null;

    /**
     * Initialize the widget with configuration from script tag
     */
    function init() {
        if (state.initialized) return;

        // Get the script tag
        const scriptTag = document.currentScript || (function () {
            const scripts = document.getElementsByTagName('script');
            return scripts[scripts.length - 1];
        })();

        // Get configuration from data attributes
        state.companyId = scriptTag.getAttribute('data-company-id');
        state.agentId = scriptTag.getAttribute('data-agent-id');
        state.theme = scriptTag.getAttribute('data-theme') || config.defaultTheme;
        state.position = scriptTag.getAttribute('data-position') || config.defaultPosition;

        // Validate required attributes
        if (!state.companyId || !state.agentId) {
            console.error('Voice Agent Widget: company-id and agent-id are required!');
            return;
        }

        // Create widget elements
        createWidgetElements();

        // Load LiveKit SDK
        loadLiveKitSDK().then(() => {
            // Ready to connect
            state.initialized = true;
            updateStatus('Ready');
        }).catch(err => {
            console.error('Failed to load LiveKit SDK:', err);
            updateStatus('Error loading dependencies');
        });

        // Add window event listeners
        window.addEventListener('beforeunload', cleanup);
    }

    /**
     * Create widget DOM elements
     */
    function createWidgetElements() {
        // Create widget container
        widgetContainer = document.createElement('div');
        widgetContainer.className = `voice-agent-widget-container position-${state.position} theme-${state.theme}`;

        // Create toggle button
        buttonEl = document.createElement('button');
        buttonEl.className = 'voice-agent-button';
        buttonEl.innerHTML = `
      <span class="button-text">${config.defaultButtonText}</span>
      <span class="button-icon">🎙️</span>
    `;
        buttonEl.addEventListener('click', toggleWidget);

        // Create widget panel
        widgetEl = document.createElement('div');
        widgetEl.className = 'voice-agent-panel hidden';
        widgetEl.innerHTML = `
      <div class="panel-header">
        <h3 class="agent-name">Voice Agent</h3>
        <button class="close-button">×</button>
      </div>
      <div class="panel-body">
        <div class="agent-avatar"></div>
        <div class="status-container">
          <span class="status-text">Initializing...</span>
          <div class="status-indicator"></div>
        </div>
        <div class="transcript-container"></div>
      </div>
      <div class="panel-footer">
        <button class="mic-button">
          <span class="mic-icon">🎙️</span>
          <span class="mic-text">Mic Off</span>
        </button>
        <button class="settings-button">⚙️</button>
      </div>
    `;

        // Add close button event
        widgetEl.querySelector('.close-button').addEventListener('click', toggleWidget);

        // Add mic button event
        widgetEl.querySelector('.mic-button').addEventListener('click', toggleMicrophone);

        // Get status element
        statusEl = widgetEl.querySelector('.status-text');

        // Add elements to container
        widgetContainer.appendChild(buttonEl);
        widgetContainer.appendChild(widgetEl);

        // Add container to document
        document.body.appendChild(widgetContainer);

        // Add styles
        addStyles();
    }

    /**
     * Add CSS styles to document
     */
    function addStyles() {
        const styleEl = document.createElement('style');
        styleEl.textContent = `
      .voice-agent-widget-container {
        position: fixed;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
      }
      
      .position-bottom-right {
        right: 20px;
        bottom: 20px;
      }
      
      .position-bottom-left {
        left: 20px;
        bottom: 20px;
      }
      
      .voice-agent-button {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: #4a6cf7;
        color: white;
        border: none;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
      }
      
      .voice-agent-button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
      }
      
      .voice-agent-button .button-text {
        display: none;
      }
      
      .voice-agent-button .button-icon {
        font-size: 24px;
      }
      
      .voice-agent-panel {
        position: absolute;
        bottom: 80px;
        right: 0;
        width: 320px;
        height: 480px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: all 0.3s ease;
      }
      
      .position-bottom-left .voice-agent-panel {
        right: auto;
        left: 0;
      }
      
      .voice-agent-panel.hidden {
        opacity: 0;
        pointer-events: none;
        transform: translateY(20px);
      }
      
      .panel-header {
        padding: 16px;
        background: #4a6cf7;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      
      .panel-header h3 {
        margin: 0;
        font-size: 18px;
      }
      
      .close-button {
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
      }
      
      .panel-body {
        flex: 1;
        padding: 16px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        align-items: center;
      }
      
      .agent-avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: #e0e0e0;
        margin-bottom: 16px;
      }
      
      .status-container {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
      }
      
      .status-indicator {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #999;
        margin-left: 8px;
      }
      
      .status-indicator.connected {
        background: #4caf50;
      }
      
      .status-indicator.error {
        background: #f44336;
      }
      
      .transcript-container {
        width: 100%;
        flex: 1;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        overflow-y: auto;
      }
      
      .panel-footer {
        padding: 12px 16px;
        display: flex;
        justify-content: space-between;
        border-top: 1px solid #e0e0e0;
      }
      
      .mic-button, .settings-button {
        padding: 8px 16px;
        border-radius: 20px;
        border: 1px solid #e0e0e0;
        background: white;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      
      .mic-button {
        display: flex;
        align-items: center;
      }
      
      .mic-button.active {
        background: #4a6cf7;
        color: white;
        border-color: #4a6cf7;
      }
      
      .mic-icon {
        margin-right: 8px;
      }
      
      /* Theme - Dark */
      .theme-dark .voice-agent-panel {
        background: #2a2a2a;
        color: white;
      }
      
      .theme-dark .transcript-container {
        border-color: #444;
        background: #333;
      }
      
      .theme-dark .panel-footer {
        border-color: #444;
      }
      
      .theme-dark .mic-button, 
      .theme-dark .settings-button {
        background: #333;
        border-color: #555;
        color: white;
      }
    `;

        document.head.appendChild(styleEl);
    }

    /**
     * Load the LiveKit SDK
     */
    function loadLiveKitSDK() {
        return new Promise((resolve, reject) => {
            if (window.LivekitClient) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://unpkg.com/livekit-client/dist/livekit-client.umd.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Toggle widget visibility
     */
    function toggleWidget() {
        const isHidden = widgetEl.classList.contains('hidden');

        if (isHidden) {
            widgetEl.classList.remove('hidden');

            // Get token if not already connected
            if (!state.token && state.initialized) {
                getToken();
            }
        } else {
            widgetEl.classList.add('hidden');
        }
    }

    /**
     * Toggle microphone on/off
     */
    function toggleMicrophone() {
        const micButton = widgetEl.querySelector('.mic-button');
        const micText = micButton.querySelector('.mic-text');

        if (!state.connected) {
            updateStatus('Not connected to agent');
            return;
        }

        if (state.micActive) {
            // Turn off microphone
            micButton.classList.remove('active');
            micText.textContent = 'Mic Off';
            state.micActive = false;

            // Disable local audio
            localTracks.forEach(track => {
                if (track.kind === 'audio') {
                    track.stop();
                    room.localParticipant.unpublishTrack(track);
                }
            });

            localTracks = localTracks.filter(track => track.kind !== 'audio');

        } else {
            // Turn on microphone
            micButton.classList.add('active');
            micText.textContent = 'Mic On';
            state.micActive = true;

            // Request microphone permission
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    const audioTrack = stream.getAudioTracks()[0];

                    if (audioTrack && room) {
                        room.localParticipant.publishTrack(audioTrack);
                        localTracks.push(audioTrack);
                    }
                })
                .catch(err => {
                    console.error('Microphone access error:', err);
                    updateStatus('Microphone access denied');
                    micButton.classList.remove('active');
                    micText.textContent = 'Mic Off';
                    state.micActive = false;
                });
        }
    }

    /**
     * Get token from API
     */
    function getToken() {
        updateStatus('Getting token...');

        fetch(`${config.apiBaseUrl}/tokens/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                company_id: state.companyId,
                agent_id: state.agentId
            })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                state.token = data.token;
                state.room = data.room;
                state.roomUrl = data.url;

                updateStatus('Connecting to agent...');
                connectToRoom();
            })
            .catch(err => {
                console.error('Token error:', err);
                updateStatus('Failed to get token');
            });
    }

    /**
     * Connect to LiveKit room
     */
    function connectToRoom() {
        if (!window.LivekitClient) {
            updateStatus('LiveKit SDK not loaded');
            return;
        }

        if (!state.token || !state.room || !state.roomUrl) {
            updateStatus('Missing connection details');
            return;
        }

        // Initialize room
        room = new window.LivekitClient.Room();

        // Set up event listeners
        room.on('connected', () => {
            state.connected = true;
            updateStatus('Connected');
            statusEl.parentElement.querySelector('.status-indicator').classList.add('connected');

            // Update agent name
            const agentNameEl = widgetEl.querySelector('.agent-name');
            const agentName = findAgentName(room);
            if (agentName) {
                agentNameEl.textContent = agentName;
            }
        });

        room.on('disconnected', () => {
            state.connected = false;
            updateStatus('Disconnected');
            statusEl.parentElement.querySelector('.status-indicator').classList.remove('connected');
        });

        room.on('participantConnected', handleParticipantConnected);
        room.on('participantDisconnected', handleParticipantDisconnected);

        // Connect to room
        room.connect(state.roomUrl, state.token)
            .catch(err => {
                console.error('Connection error:', err);
                updateStatus('Connection failed');
                statusEl.parentElement.querySelector('.status-indicator').classList.add('error');
            });
    }

    /**
     * Handle participant connected event
     */
    function handleParticipantConnected(participant) {
        console.log('Participant connected:', participant.identity);

        // Listen for track subscriptions
        participant.on('trackSubscribed', track => {
            if (track.kind === 'audio') {
                // Agent audio track
                track.attach();
            }
        });
    }

    /**
     * Handle participant disconnected event
     */
    function handleParticipantDisconnected(participant) {
        console.log('Participant disconnected:', participant.identity);
    }

    /**
     * Find agent name from room participants
     */
    function findAgentName(room) {
        let agentName = null;

        room.participants.forEach(participant => {
            if (participant.identity.startsWith('agent-')) {
                // Use agent metadata or default to identity
                agentName = participant.metadata || `Agent ${participant.identity.replace('agent-', '')}`;
            }
        });

        return agentName;
    }

    /**
     * Update status text
     */
    function updateStatus(text) {
        if (statusEl) {
            statusEl.textContent = text;
        }
    }

    /**
     * Clean up resources
     */
    function cleanup() {
        // Disconnect from room
        if (room) {
            room.disconnect();
        }

        // Stop all tracks
        localTracks.forEach(track => track.stop());

        // Remove event listeners
        window.removeEventListener('beforeunload', cleanup);
    }

    // Initialize widget
    init();
})(); 