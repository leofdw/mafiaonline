from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from models import db, Player, Lobby, PlayerRole
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ZOVSvaston'
socketio = SocketIO(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
db.init_app(app)

@app.route("/")
def hello_world():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    socket_id = request.sid
    existing_player = Player.query.filter_by(socket_id=socket_id).first()
    if existing_player:
        print("Пользователь переподключился: " + existing_player.socket_id)
    else:
        player = Player(socket_id=socket_id, current_lobby_id=None)
        db.session.add(player)
        db.session.commit()
        print("Пользователь подключился: " + player.socket_id)

@socketio.on('disconnect')
def handle_disconnect():
    socket_id = request.sid
    try:
        player = Player.query.filter_by(socket_id=socket_id).first()
        if player:
            if player.current_lobby_id:
                lobby = Lobby.query.filter_by(id=player.current_lobby_id).first()
                leave_lobby(player, lobby)
                update_players_list(lobby.id)
                print(f'Пользователь {player.nickname} вышел из лобби! Игроки в лобби: {[i.nickname for i in Player.query.filter_by(current_lobby_id=lobby.id)]}')
            db.session.delete(player)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Ошибка при отключении: " + str(e))

@socketio.on('client_create_lobby')
def handle_create_lobby(data):
    socket_id = request.sid
    player = Player.query.filter_by(socket_id=socket_id).first()
    if player.current_lobby_id:
        emit('lobby_error', 'Вы уже в лобби!')
        return
    
    try:
        lobby = Lobby(
            host_socket_id = socket_id,
            max_players=data.get('max_players'),
            location=data.get('location'),
            mafia_count = data.get('mafia_count'),
            is_maniac = data.get('is_maniac'),
            is_mistress = data.get('is_mistress'),
            is_sheriff_can_shot = data.get('is_sheriff_can_shot')
        )
        db.session.add(lobby)
        db.session.commit()
        player.current_lobby_id = lobby.id
        player.nickname = data.get('nickname')
        db.session.commit()
        join_room(lobby.id)
        update_players_list(lobby.id)
        print(f'Лобби {lobby.id} создано! Хост: {player.nickname}')
    except Exception as e:
        db.session.rollback()
        print("Ошибка при создании лобби: " + str(e))
    

@socketio.on('client_join_lobby')
def handle_join_lobby(data):
    lobby_id = data.get('lobby_id')
    nickname = data.get('nickname')
    socket_id = request.sid
    lobby = db.session.get(Lobby, lobby_id)
    player = Player.query.filter_by(socket_id=socket_id).first()
    if not lobby:
        emit('lobby_error', 'Лобби не найдено')
        print(f'Лобби {lobby_id} не найдено!')
        return
    
    if player.current_lobby_id:
        emit('lobby_error', 'Вы уже в лобби!')
        return

    current_players = Player.query.filter_by(current_lobby_id=lobby_id).count()
    if current_players >= lobby.max_players:
        emit('lobby_error', 'Лобби заполнено')
        return
    try:
        player.current_lobby_id = lobby.id
        player.nickname = nickname
        db.session.commit()
        emit('client_lobby_message', f'Пользователь {player.nickname} зашел в лобби! Игроки в лобби: {[i.nickname for i in Player.query.filter_by(current_lobby_id=lobby.id)]}', to=lobby.id)
        join_room(lobby.id)
        update_players_list(lobby.id)
        print(f'Пользователь {player.nickname} зашел в лобби! Игроки в лобби: {[i.nickname for i in Player.query.filter_by(current_lobby_id=lobby.id)]}')
    except Exception as e:
        db.session.rollback()
        print("Ошибка при заходе в лобби: " + str(e))

@socketio.on('client_leave_lobby')
def handle_leave_lobby():
    socket_id = request.sid
    player = Player.query.filter_by(socket_id=socket_id).first()
    try:
        lobby = Lobby.query.filter_by(id=player.current_lobby_id).first()
        leave_lobby(player, lobby)
        update_players_list(lobby.id)
        print(f'Пользователь {player.nickname} вышел из лобби! Игроки в лобби: {[i.nickname for i in Player.query.filter_by(current_lobby_id=lobby.id)]}')
    except Exception as e:
        db.session.rollback()
        print("Ошибка при выходе из лобби: " + str(e))

def leave_lobby(player, lobby):
    leave_room(lobby.id)
    player.current_lobby_id = None
    db.session.commit()
    if lobby.host_socket_id == player.socket_id:
        another_player = Player.query.filter_by(current_lobby_id=lobby.id).first()
        if another_player:
            lobby.host_socket_id = another_player.socket_id
            print(f'Хост вышел из лобби! Теперь хост {another_player.nickname}!')
            db.session.commit()
        else:
            db.session.delete(lobby)
            db.session.commit()
            print(f'Лобби {lobby.id} удалено!')

def update_players_list(lobby_id):
    lobby = Lobby.query.get(lobby_id)
    players = Player.query.filter_by(current_lobby_id=lobby_id).all()
    data = {
        'lobby_id': lobby_id,
        'players': [i.nickname for i in players],
        'host_socket_id': lobby.host_socket_id
    }
    emit('server_lobby_update', data, to=lobby_id)

def shuffle_role(lobby, players, roles):
    avaliable_roles = roles.copy()
    random.shuffle(avaliable_roles)
    for player in players:
        player.role = avaliable_roles.pop()
    db.session.commit()

@socketio.on('client_start_game')
def handle_start_game():
    try:
        player = Player.query.filter_by(socket_id=request.sid).first()
        lobby = Lobby.query.filter_by(id=player.current_lobby_id).first()
        players = Player.query.filter_by(current_lobby_id=lobby.id).all()
        lobby.players_count = len(players)

        roles = []
        roles.append('sheriff')
        roles.append('doctor')
        for i in range(lobby.mafia_count):
            roles.append('mafia')
        if lobby.is_maniac:
            roles.append('maniac')
        if lobby.is_mistress:
            roles.append('mistress')
        for i in range(lobby.players_count - len(roles)):
            roles.append('civilian')
        shuffle_role(lobby, players, roles)
        db.session.commit()

        for p in players:
            emit('server_game_started', {'role':p.role, 'players_count':lobby.players_count}, to=p.socket_id)
    except Exception as e:
        print("Ошибка при старте игры: " + str(e))

def initialize_cleanup():
    try:
        Player.query.delete()
        Lobby.query.delete()
        db.session.commit()
        print("Очистка завершена")
    except Exception as e:
        db.session.rollback()
        print("Ошибка при очистке: " + str(e))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Таблицы БД созданы")
        initialize_cleanup()
    socketio.run(app, debug=True)