// voice_agent_helpers.js
// Helper functions for voice agent frontend

// Function to handle speech interruption
function handleSpeechInterruption() {
    console.log('Speech interruption detected');
    
    // Stop current audio playback
    if (window.currentAudio) {
        window.currentAudio.pause();
        window.currentAudio = null;
    }
    
    // Visual indicator for interruption
    document.body.classList.add('interrupting');
    
    // Start listening to capture what the user wants to say
    if (window.startListening && typeof window.startListening === 'function') {
        setTimeout(() => {
            window.startListening();
        }, 100);
    } else {
        console.error('startListening function not available');
    }
}

// Export functions for use in HTML
window.handleSpeechInterruption = handleSpeechInterruption;
