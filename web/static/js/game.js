/* 
filename: game.js

Client side of web game known as paper bending game

Author: Petr Holánek
Created: 30.8.2024
last modified: 1.9.2024 
*/



let gameId = null; // variable for gameId
let deviceId = null; // variable for deviceId
const socket = io(); //socket

//fucntion for creating game with optional game id 
export function createGame() {
    const gameIdInput = document.getElementById('game-id-create').value; //get optonal game id from user
    //go to endpoint create game
    fetch('/create_game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameIdInput })
    })
    .then(response => response.json())
    .then(data => {
        if (data.game_id) {
            gameId = data.game_id; //set game id to current game_id
            document.getElementById('join-game-section').style.display = 'none'; // display game section
            joinGame(gameId, true) // join game after creation and set the user as admin
        }
    })
    .catch(error => console.error('Error:', error));
}
//function to join existing game
export function joinGame(gameIdFromCreate = null, isAdmin = false) {
    const gameIdInput = gameIdFromCreate || document.getElementById('game-id-join').value; // get game_id from create endpoint or from user input
    //go to endpoint for joining gameroom
    fetch('/join_game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameIdInput , is_admin: isAdmin})
    })
    .then(response => response.json())
    .then(data => {
        if (data.device_id) {
            deviceId = data.device_id; // set device id from response
            gameId = gameIdInput; // set game id from response
            document.getElementById('join-game-section').style.display = 'none'; // hide create game section
            document.getElementById('game-section').style.display = 'block'; // display game section
            document.getElementById('current-question-text').textContent = data.current_question; // update current question text
            document.getElementById('gameID').textContent = gameId; // update game id text 
            document.getElementById('playersNum').textContent = data.player_count; // update player count for game roomm

            // Listen for player count updates
            socket.on('player_update', function(data) {
                if (data.game_id === gameId) {
                    document.getElementById('playersNum').textContent = data.player_count;
                }
            });

            // Emit join event
            socket.emit('join', { game_id: gameId, device_id: deviceId });

            // Listen for real-time updates
            socket.on('question_update', function(data) {
                document.getElementById('current-question-text').textContent = data.current_question;
                document.getElementById('waiting-text').style.display = 'none'; // Hide waiting text when question updates
            });

            // listen for game over event
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

// Function to submit response to the current question
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

// Socket event listeners
socket.on('connect', () => {
    console.log('Connected to Socket.IO server');
});

// window listener before the user leaves site
window.onbeforeunload = function() {
    fetch('/leave_game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId, device_id: deviceId})
    })
    socket.emit('leave_game', {gameId: gameId, deviceId: deviceId});
};

window.createGame = createGame;
window.joinGame = joinGame;
window.submitResponse = submitResponse;