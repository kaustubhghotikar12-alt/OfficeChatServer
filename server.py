"""
Office Chat Server - Backend API for Render Web Service deployment
Enhanced with online users and typing indicators
"""

from flask import Flask, request
from flask_socketio import SocketIO, emit
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'office_chat_secret_key_2024')

# Configure SocketIO for Render deployment
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    logger=True, 
    engineio_logger=True
)

# Store chat history, connected users, and typing status
chat_history = []
connected_users = {}  # {session_id: {'username': 'John', 'joined_at': datetime}}
typing_users = {}  # {session_id: {'username': 'John', 'timestamp': datetime}}

@socketio.on('connect')
def handle_connect(auth):
    print(f'Client {request.sid} connected')

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_users:
        username = connected_users[request.sid]['username']
        del connected_users[request.sid]
        
        # Remove from typing users if they were typing
        if request.sid in typing_users:
            del typing_users[request.sid]
            emit('user_stopped_typing', {'username': username}, broadcast=True)
        
        # Broadcast leave message
        leave_message = {
            'username': 'System',
            'message': f'{username} left the chat',
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': 'system'
        }
        chat_history.append(leave_message)
        emit('message', leave_message, broadcast=True)
        
        # Update online users list
        online_users = [user['username'] for user in connected_users.values()]
        emit('online_users_update', {'users': online_users, 'count': len(online_users)}, broadcast=True)
        
        print(f'{username} disconnected')

@socketio.on('join_chat')
def handle_join_chat(data):
    username = data['username']
    connected_users[request.sid] = {
        'username': username,
        'joined_at': datetime.now()
    }
    
    # Send chat history to the new user
    emit('chat_history', chat_history)
    
    # Send current online users to the new user
    online_users = [user['username'] for user in connected_users.values()]
    emit('online_users_update', {'users': online_users, 'count': len(online_users)})
    
    # Broadcast join message
    join_message = {
        'username': 'System',
        'message': f'{username} joined the chat',
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'type': 'system'
    }
    chat_history.append(join_message)
    emit('message', join_message, broadcast=True)
    
    # Update online users list for everyone
    emit('online_users_update', {'users': online_users, 'count': len(online_users)}, broadcast=True)
    
    print(f'{username} joined the chat')

@socketio.on('send_message')
def handle_message(data):
    if request.sid in connected_users:
        username = connected_users[request.sid]['username']
        
        # Stop typing when message is sent
        if request.sid in typing_users:
            del typing_users[request.sid]
            emit('user_stopped_typing', {'username': username}, broadcast=True, include_self=False)
        
        message_data = {
            'username': username,
            'message': data['message'],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': 'user'
        }
        chat_history.append(message_data)
        emit('message', message_data, broadcast=True)
        print(f'{username}: {data["message"]}')

@socketio.on('typing')
def handle_typing(data):
    if request.sid in connected_users:
        username = connected_users[request.sid]['username']
        
        if data['typing']:
            # User started typing
            typing_users[request.sid] = {
                'username': username,
                'timestamp': datetime.now()
            }
            emit('user_typing', {'username': username}, broadcast=True, include_self=False)
        else:
            # User stopped typing
            if request.sid in typing_users:
                del typing_users[request.sid]
            emit('user_stopped_typing', {'username': username}, broadcast=True, include_self=False)

@app.route('/')
def index():
    return {
        "message": "Office Chat Server API is running!",
        "status": "active",
        "connected_users": len(connected_users),
        "total_messages": len(chat_history),
        "online_users": [user['username'] for user in connected_users.values()]
    }

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# For Gunicorn deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
