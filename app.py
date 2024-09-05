#
# filename: app.py
# 
# Server side of web game known as paper bending game
#
# Author: Petr Holánek
# Created: 30.8.2024
# last modified: 1.9.2024

# Imports
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import random
from collections import defaultdict
import socket


# Flask app setup
app = Flask(__name__,
            static_url_path='',
            static_folder='web/static',
            template_folder='web/templates'
            )


# Socket.IO setup for real-time communication between clients and server
socketio = SocketIO(app)

# In-memory storage for games
games = {}

# Sequence of questions/phrases for the game
questions = [
    "Jaký?", "Kdo?", "S kým?", "Kdy?", "Kde?", "Co dělali?", "Proč?"
]

# Function to get local IP address for server
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # initalize socket
        s.settimeout(0) 
        s.connect(('8.8.8.8', 80))  # Google DNS server
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'  # Fallback to localhost if there's an error
    finally:
        s.close()
    return local_ip

# Endpoint for index
@app.route('/')
def index():
    return render_template('index.html', server_ip=get_local_ip()) # returns index template to the user

# Endpoint for game creation
@app.route('/create_game', methods=['POST'])
def create_game():
    data = request.json
    provided_game_id = data.get('game_id') # gets game id that user want the game to create
    
    if provided_game_id not in games: #checks if game id is already created
        game_id = provided_game_id
    else:
        game_id = stdocument.getElementById('waiting-text').style.display = 'none'; # Hide waiting text when game starts
    
    # Initialize the game data structure
    games[game_id] = {
        'players': {},
        'responses': defaultdict(list),
        'current_question': 0,
        'submitted_players': set(),
        'started': False,
        'admin': None
    }
    return jsonify({'game_id': game_id}), 201

# Endpoint for joining game
@app.route('/join_game', methods=['POST'])
def join_game():
    data = request.json
    game_id = data.get('game_id') # gets game id from user to join
    is_admin = data.get('is_admin', False)
    
    if game_id not in games: # if game doesn't exist
        return jsonify({'error': 'Game not found.'}), 404
    
    if games[game_id]["started"] == True: # If game started don't let the user join
        return jsonify({'error': 'Game has already started.'}), 409
    
    device_id = str(uuid.uuid4())  # Generate a unique device ID
    games[game_id]['players'][device_id] = device_id  # Use a default name or a placeholder

    if is_admin and games[game_id]['admin'] is None:
        games[game_id]['admin'] = device_id

    socketio.emit('player_update', {'game_id': game_id, 'player_count': len(games[game_id]['players']), 'admin': games[game_id]['admin']}, room=game_id)

    current_question = questions[games[game_id]['current_question']] # get current question to show to the user
    return jsonify({'status': 'Joined game', 'device_id': device_id, 'current_question': current_question, 'player_count': len(games[game_id]['players'])}), 200

# Function to create list with lenght of parameret n
def create_list_with_length(n):
    return [[None, None] for _ in range(n)]

# Function to shuffle responses from players
def shuffle(responses, game):
    players = list(game['players'].keys()) # Get list of players IDs
    num_players = len(players) # gets number of players

    device_index = defaultdict(int) # create dictionary for device and their index
    for ind, device in enumerate(list(game['players'].keys())):
        device_index[device] = ind # fill dictionary with devices indexes


    responses_by_question = defaultdict(lambda: create_list_with_length(num_players)) # create dictionary for questions and list of responses
    
    # for each question fill their response list with answers
    for question, responses_list in responses.items():
        for resp in responses_list:
            ind = device_index[resp['device_id']]
            responses_by_question[question][ind] = [resp['device_id'], resp['response']]
    
    responses_by_device = defaultdict(list) # create disctionary for devices and list for their answeres
    
    # Shuffle the responses for each device so it doesn't get answer from the same user twice in a row
    for question_index, (question, responses_list) in enumerate(responses_by_question.items()):
        for index, device in enumerate(players):
            # Calculate the correct index for this device's response
            response_index = (index + question_index) % num_players
            selected_response = responses_list[response_index][1]
            responses_by_device[device].append((question, selected_response))

    return responses_by_device


# Endpoint for submitting response
@app.route('/submit_response', methods=['POST'])
def submit_response():
    data = request.json
    game_id = data.get('game_id') # get game id from user
    device_id = data.get('device_id') # get device id from user
    response = data.get('response') # get response from user
    
    if game_id not in games: # if game no longer exists
        leave_game()
        return jsonify({'error': 'Game not found.'}), 404
    
    game = games[game_id]
    
    if device_id not in game['players']: # if user doesnt belong to the game room
        return jsonify({'error': 'Player not part of this game.'}), 403
    
    question = questions[game['current_question']] # gets current question
    if device_id not in game['responses'][question]:
        game['responses'][question].append({'device_id': device_id, 'response': response}) # add response to array of responses
        game['submitted_players'].add(device_id) # add device to submitted players
    
    # Check if all players have submitted responses
    if len(game['submitted_players']) >= len(game['players']):
        game['submitted_players'].clear()
        
        # if this question was not last
        if game['current_question'] + 1 < len(questions):
            game['current_question'] += 1
            next_question = questions[game['current_question']]
            socketio.emit('question_update', {'current_question': next_question}, room=game_id)
        
        #if question was last
        else:
            shuffled_responses = shuffle(game['responses'], game)
            socketio.emit('game_over', {'shuffled_responses': shuffled_responses}, room=game_id)
            del shuffled_responses
    
    # Emit waiting event to all players who have submitted
    else:
        remaining_players = set(game['players']) - game['submitted_players']
        if len(remaining_players) > 0:
            for player in remaining_players:
                socketio.emit('waiting', {}, room=player)
    
    return jsonify({'status': 'Response submitted'}), 200

@app.route('/leave_game', methods=['POST'])
def leave_game():
    data = request.json
    game_id = data.get('game_id') # get game id from user
    device_id = data.get('device_id') # get device id from user

    # if user is in the game room
    if game_id in games and device_id in games[game_id]['players']:
        del games[game_id]['players'][device_id] #delete user from the game

        # Remove the player's responses
        for question in questions:
            if question in games[game_id]['responses']:
                games[game_id]['responses'][question] = [
                    resp for resp in games[game_id]['responses'][question] 
                    if resp['device_id'] != device_id
                ]

        # Emit player number change
        socketio.emit('player_update', {'game_id': game_id, 'player_count': len(games[game_id]['players'])}, room=game_id)

        # If no players left in the game, delete it
        if len(games[game_id]['players']) == 0:
            del games[game_id]

    return jsonify({'status': 'left game'}), 200

@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.json
    game_id = data.get('game_id') # get game id from user
    device_id = data.get('device_id') # get device id

    if device_id == games[game_id]['admin']:
        games[game_id]['started'] = True
        socketio.emit('game_started', {'game_id': game_id}, room=game_id)
    
    return jsonify({'status': 'game started'}), 200


# Socket on connect
@socketio.on('join')
def handle_join(data):
    game_id = data['game_id']
    device_id = data['device_id']
    join_room(game_id)
    print(f"Player {device_id} joined game {game_id}")


# Start web server
if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"Server running on http://{local_ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
