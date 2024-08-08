from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room
import uuid
import random
from collections import defaultdict
import socket

app = Flask(__name__)
socketio = SocketIO(app)

# In-memory storage for games
games = {}

# Sequence of questions/phrases for the game
questions = [
    "Jaký?", "Kdo?", "S kým?", "Kdy?", "Kde?", "Co dělali?", "Proč?"
]

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('8.8.8.8', 80))  # Google DNS server
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'  # Fallback to localhost if there's an error
    finally:
        s.close()
    return local_ip

@app.route('/')
def index():
    return render_template('index.html', server_ip=get_local_ip())

@app.route('/create_game', methods=['POST'])
def create_game():
    data = request.json
    provided_game_id = data.get('game_id')
    
    if provided_game_id and provided_game_id not in games:
        game_id = provided_game_id
    else:
        game_id = str(uuid.uuid4())
    
    games[game_id] = {
        'players': {},
        'responses': defaultdict(list),
        'current_question': 0,
        'submitted_players': set()
    }
    return jsonify({'game_id': game_id}), 201

@app.route('/join_game', methods=['POST'])
def join_game():
    data = request.json
    game_id = data.get('game_id')
    
    if game_id not in games:
        return jsonify({'error': 'Game not found.'}), 404
    
    device_id = str(uuid.uuid4())  # Generate a unique device ID
    games[game_id]['players'][device_id] = "Player"  # Use a default name or a placeholder

    current_question = questions[games[game_id]['current_question']]
    return jsonify({'status': 'Joined game', 'device_id': device_id, 'current_question': current_question}), 200


@app.route('/leave_game', methods = ['POST'])
def leave_game():
    for game_id, game_data in games.items():
        for device_id in list(game_data['players'].keys()):
            if request.sid == socketio.server.manager.sid_from_environ(request.environ):
                # Remove the player from the game
                del game_data['players'][device_id]
                print(f"Player {device_id} removed from game {game_id}")

                # Optionally, remove the player from the submitted_players list
                if device_id in game_data['submitted_players']:
                    game_data['submitted_players'].remove(device_id)

                # Check if no players are left in the game
                if not game_data['players']:
                    del games[game_id]  # Clean up the game if empty
                    print(f"Game {game_id} deleted because it is empty")

                return  # Exit after removing the player


def shuffle(responses, game):
    responses_by_question = defaultdict(list)
    for question, responses_list in responses.items():
        for resp in responses_list:
            responses_by_question[question].append((resp['device_id'],resp['response']))

    responses_by_device = defaultdict(list)
    for device in game['players']:
        for question in responses_by_question:
            if question == "Jaký?":
                for player in range(len(game['players'])):
                    responses_by_device[device].append(responses_by_question[question][player])
            else:
                for player in range(len(game['players'])):
                    valid = range(len(game['players']))
                    for i in range(len(game['players'])):
                        rand = random.randrange(len(game['players']))
                        if responses_by_device[device][]


    print(responses_by_device)


    

    """ # Initialize data structures
    responses_by_device = defaultdict(list)
    questions = defaultdict(list)

    # Collect responses for each device
    for question, responses_list in responses.items():
        if not isinstance(responses_list, list):
            raise TypeError(f"Expected list for responses under question '{question}'")
        
        for resp in responses_list:
            if not isinstance(resp, dict):
                raise TypeError(f"Expected dictionary for response item under question '{question}'")
            if 'device_id' not in resp or 'response' not in resp:
                raise KeyError(f"Response item under question '{question}' missing 'device_id' or 'response'")
            responses_by_device[resp['device_id']].append((question, resp['response']))

    # Prepare the final output format
    results_by_device = defaultdict(dict)
    
    # For each device, prepare the shuffled responses
    for device_id, responses_list in responses_by_device.items():
        # Track the last device ID used to avoid repetition
        last_device_id = None
        for question, _ in responses_list:
            # Find a different response if the last one was from the same device
            if last_device_id == device_id:
                available_responses = []
                for d, resps in responses_by_device.items():
                    for q, r in resps:
                        if q == question and d != last_device_id:
                            available_responses.append((d, q, r))
                
                if available_responses:
                    last_device_id, question, response = random.choice(available_responses)
                    responses_by_device[last_device_id].remove((question, response))
                else:
                    raise ValueError("No valid responses available from different devices")
            else:
                response = next(r for q, r in responses_by_device[device_id] if q == question)
                last_device_id = device_id
                
            results_by_device[device_id][question] = response
    
    return results_by_device """

    
@app.route('/submit_response', methods=['POST'])
def submit_response():
    data = request.json
    game_id = data.get('game_id')
    device_id = data.get('device_id')
    response = data.get('response')
    
    if game_id not in games:
        return jsonify({'error': 'Game not found.'}), 404
    
    game = games[game_id]
    
    if device_id not in game['players']:
        return jsonify({'error': 'Player not part of this game.'}), 403
    
    question = questions[game['current_question']]
    game['responses'][question].append({'device_id': device_id, 'response': response})
    game['submitted_players'].add(device_id)
    
    # Check if all players have submitted responses
    if len(game['submitted_players']) >= len(game['players']):
        game['submitted_players'].clear()
        
        if game['current_question'] + 1 < len(questions):
            game['current_question'] += 1
            next_question = questions[game['current_question']]
            socketio.emit('question_update', {'current_question': next_question}, room=game_id)
        else:
            shuffled_responses = shuffle(game['responses'], game)
            socketio.emit('game_over', {'shuffled_responses': shuffled_responses}, room=game_id)
    else:
        # Emit waiting event to all players who have submitted
        remaining_players = set(game['players']) - game['submitted_players']
        if len(remaining_players) > 0:
            for player in remaining_players:
                socketio.emit('waiting', {}, room=player)
    
    return jsonify({'status': 'Response submitted'}), 200


@socketio.on('join')
def handle_join(data):
    game_id = data['game_id']
    device_id = data['device_id']
    join_room(game_id)
    print(f"Player {device_id} joined game {game_id}")

@socketio.on('disconnect')
def handle_disconnect():
    leave_game()
    # Optional: Handle player disconnection, e.g., removing from the game
    print('A player disconnected')

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"Server running on http://{local_ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
