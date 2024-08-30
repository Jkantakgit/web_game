
let gameId = null;
let deviceId = null;
const socket = io();

export function createGame() {
    console.log("Create")
    const gameIdInput = document.getElementById('game-id-create').value;
    fetch('/create_game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameIdInput })
    })
    .then(response => response.json())
    .then(data => {
        if (data.game_id) {
            gameId = data.game_id;
            document.getElementById('create-game-section').style.display = 'none';
            document.getElementById('join-game-section').style.display = 'block';
            joinGame(gameId)
        }
    })
    .catch(error => console.error('Error:', error));
}

export function joinGame(gameIdFromCreate = null, isAdmin = false) {
    const gameIdInput = gameIdFromCreate || document.getElementById('game-id-join').value;
    fetch('/join_game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameIdInput , is_admin: isAdmin})
    })
    .then(response => response.json())
    .then(data => {
        if (data.device_id) {
            deviceId = data.device_id;
            gameId = gameIdInput;
            document.getElementById('create-game-section').style.display = 'none';
            document.getElementById('join-game-section').style.display = 'none';
            document.getElementById('game-section').style.display = 'block';
            document.getElementById('current-question-text').textContent = data.current_question;
            document.getElementById('gameID').textContent = gameId;
            document.getElementById('playersNum').textContent = data.player_count;

            // Emit join event
            socket.emit('join', { game_id: gameId, device_id: deviceId });

            // Listen for player count updates
            socket.on('player_update', function(data) {
                if (data.game_id === gameId) {
                    document.getElementById('playersNum').textContent = data.player_count;
                }
            });

            // Listen for real-time updates
            socket.on('question_update', function(data) {
                document.getElementById('current-question-text').textContent = data.current_question;
                document.getElementById('waiting-text').style.display = 'none'; // Hide waiting text when question updates
            });

            socket.on('game_over', function(data) {
                const deviceResponses = data.shuffled_responses[deviceId] || {};
                
                // Update the HTML for each question
                for (const [question, response] of deviceResponses) {
                    // Find the element by the question text
                    const element = document.getElementById(question);
                    
                    // If the element exists, update its text content
                    if (element) {
                        const span = element.querySelector('span');
                        
                        // Check if the span exists, then set its text content
                        if (span) {
                            span.textContent = response;
                        }
                    }
                }
                
                // Show game over section and hide game section
                document.getElementById('game-section').style.display = 'none';
                document.getElementById('game-over-section').style.display = 'block';
            });

            socket.on('waiting', function() {
                document.getElementById('waiting-text').style.display = 'block'; // Show waiting text
            });
        }
    })
    .catch(error => console.error('Error:', error));
}

export function submitResponse() {
    const response = document.getElementById('response').value;
    fetch('/submit_response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId, device_id: deviceId, response: response })
    })
    .then(response => response.json())
    .then(data => {
        // Show waiting message when response is submitted
        document.getElementById('waiting-text').style.display = 'block';
    })
    .catch(error => console.error('Error:', error));
}

socket.on('connect', () => {
    console.log('Connected to Socket.IO server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from Socket.IO server');
});



window.createGame = createGame;
window.joinGame = joinGame;
window.submitResponse = submitResponse;