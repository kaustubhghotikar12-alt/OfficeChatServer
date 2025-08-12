"""
Office Chat Server - Backend API for Render Web Service deployment
This will be deployed as a Render Web Service
"""

from flask import Flask, request
from flask_socketio import SocketIO, emit
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'office_chat_secret_key_2024')

# Configure SocketIO for Render deployment - remove async_mode to let it auto-detect
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",  # Allow connections from your static site
    logger=True, 
    engineio_logger=True
)

# Store chat history and connected users
chat_history = []
connected_users = {}

@socketio.on('connect')
def handle_connect(auth):
    print(f'Client {request.sid} connected')

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_users:
        username = connected_users[request.sid]
        del connected_users[request.sid]
        
        # Broadcast leave message
        leave_message = {
            'username': 'System',
            'message': f'{username} left the chat',
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': 'system'
        }
        chat_history.append(leave_message)
        emit('message', leave_message, broadcast=True)
        print(f'{username} disconnected')

@socketio.on('join_chat')
def handle_join_chat(data):
    username = data['username']
    connected_users[request.sid] = username
    
    # Send chat history to the new user
    emit('chat_history', chat_history)
    
    # Broadcast join message
    join_message = {
        'username': 'System',
        'message': f'{username} joined the chat',
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'type': 'system'
    }
    chat_history.append(join_message)
    emit('message', join_message, broadcast=True)
    print(f'{username} joined the chat')

@socketio.on('send_message')
def handle_message(data):
    if request.sid in connected_users:
        username = connected_users[request.sid]
        message_data = {
            'username': username,
            'message': data['message'],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': 'user'
        }
        chat_history.append(message_data)
        emit('message', message_data, broadcast=True)
        print(f'{username}: {data["message"]}')

@app.route('/')
def index():
    return {
        "message": "Office Chat Server API is running!",
        "status": "active",
        "connected_users": len(connected_users),
        "total_messages": len(chat_history)
    }

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
