from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import uuid
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import time
from collections import OrderedDict

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------------------------------------------------------
# Implementação de Cache com TTL
# ---------------------------------------------------------------

class TTLCache:
    def __init__(self, maxsize=32, ttl=300):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            
            if key in self.cache:
                data, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return data
                
            result = func(*args, **kwargs)
            self.cache[key] = (result, time.time())
            
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
                
            return result
        return wrapper

cache = TTLCache(maxsize=32, ttl=300)

# ---------------------------------------------------------------
# Implementação do Scraper da Liquipedia
# ---------------------------------------------------------------

LIQUIPEDIA_BASE = "https://liquipedia.net"

@cache
def get_esports_data(game, data_type):
    """Coleta dados da Liquipedia com URLs específicas para cada jogo"""
    try:
        time.sleep(2)  # Respeita o rate limit
        
        headers = {
            'User-Agent': 'FURIA Esports Bot/1.0 (+https://github.com/seu-repositorio)',
            'Accept-Language': 'pt-BR'
        }
        
        if data_type == 'players':
            page = requests.get(f"{LIQUIPEDIA_BASE}/{game}/FURIA", headers=headers, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.content, 'html.parser')
            return parse_players(soup)
            
        elif data_type == 'matches':
            # URL específica para LoL (Played Matches)
            if game == 'leagueoflegends':
                page = requests.get(f"{LIQUIPEDIA_BASE}/{game}/FURIA/Played_Matches", 
                                 headers=headers, timeout=10)
            else:
                # URLs padrão para outros jogos
                page = requests.get(f"{LIQUIPEDIA_BASE}/{game}/FURIA/Matches", 
                                 headers=headers, timeout=10)
            
            page.raise_for_status()
            soup = BeautifulSoup(page.content, 'html.parser')
            return parse_matches(soup, game)
            
    except Exception as e:
        print(f"Erro ao buscar {data_type} de {game}: {str(e)}")
        return [f"Erro temporário. Por favor, tente novamente mais tarde."]

def parse_players(soup):
    """Extrai lista de jogadores da tabela roster-card"""
    players = []
    roster_table = soup.find('table', {'class': 'roster-card'})
    
    if roster_table:
        for player_row in roster_table.find_all('tr', {'class': 'Player'}):
            id_cell = player_row.find('td', {'class': 'ID'})
            if id_cell:
                player_link = id_cell.find('a', href=True)
                if player_link and player_link.get('title'):
                    players.append(player_link['title'])
                else:
                    bold_name = id_cell.find('b')
                    if bold_name:
                        players.append(bold_name.get_text(strip=True))
    
    return players[:10] if players else ["Nenhum jogador encontrado"]

def parse_matches(soup, game):
    """Roteia para o parser específico de cada jogo"""
    if game == 'counterstrike':
        return parse_csgo_matches(soup)
    elif game == 'valorant':
        return parse_valorant_matches(soup)
    elif game == 'leagueoflegends':
        return parse_lol_matches(soup)
    return ["Parser não implementado para este jogo"]

def parse_csgo_matches(soup):
    """Parser específico para CS2"""
    matches = []
    table = soup.find('table', {'class': 'wikitable'})
    
    if table:
        for row in table.select('tr')[1:6]:
            cols = row.select('td')
            if len(cols) >= 5:
                date = cols[0].get_text(strip=True)
                event = cols[5].get_text(strip=True)
                team1 = cols[6].get_text(strip=True)
                resultMatch = cols[7].get_text(strip=True)
                team2 = cols[8].get_text(strip=True) if len(cols) > 5 else "Evento não especificado"
                
                # Formatação consistente
                matchup = f"{team1} vs {team2}"
                matches.append(f"{date} | {matchup} - {event} | {resultMatch}")
    
    return matches if matches else ["Nenhuma partida de CS2 encontrada"]

def parse_valorant_matches(soup):
    """Parser específico para Valorant"""
    matches = []
    table = soup.find('table', {'class': 'wikitable'})
    
    if table:
        for row in table.select('tr')[1:6]:
            cols = row.select('td')
            if len(cols) >= 4:
                date = cols[0].get_text(strip=True)
                event = cols[4].get_text(strip=True)
                team1 = 'Furia'
                resultMatch = cols[5].get_text(strip=True)
                team2 = cols[6].get_text(strip=True) if len(cols) > 5 else "Evento não especificado"
                
                # Formatação consistente
                matchup = f"{team1} vs {team2}"
                matches.append(f"{date} | {matchup} - {event} | {resultMatch}")
    
    return matches if matches else ["Nenhuma partida de Valorant encontrada"]

def parse_lol_matches(soup):
    """Parser completo com tratamento de erro"""
    try:
        matches = []
        table = soup.find('table', {'class': 'wikitable'})
        
        if not table:
            return ["Nenhuma tabela de partidas encontrada"]
            
        for row in table.select('tr')[1:10]:
            try:
                # Determina resultado
                row_classes = row.get('class', [])
                if 'recent-matches-bg-win' in row_classes:
                    result = "✅ Vitória"
                elif 'recent-matches-bg-lose' in row_classes:
                    result = "❌ Derrota"
                else:
                    result = "🔶 Sem resultado"
                
                cols = row.select('td')
                if len(cols) >= 5:
                    date = cols[0].get_text(strip=True)
                    event = cols[3].get_text(strip=True)
                    enemy = cols[4].get_text(strip=True)[:30]  # Limita tamanho do evento
                    
                    matches.append(f"{date} | {event} - Furia vs {enemy} | {result}")
            
            except Exception as e:
                print(f"Erro ao processar linha: {e}")
                continue
                
        return matches if matches else ["Nenhuma partida válida encontrada"]
        
    except Exception as e:
        print(f"Erro no parser LoL: {e}")
        return ["Erro ao processar partidas de LoL"]

# ---------------------------------------------------------------
# Lógica do Bot
# ---------------------------------------------------------------

user_states = {}
message_history = []

def handle_bot_command(user_id, command):
    state = user_states.get(user_id, {})
    
    if command.lower() in ['0', 'sair']:
        user_states.pop(user_id, None)
        return {
            'message': "❌ Conversa com o bot encerrada.",
            'is_final': True
        }
    
    # Menu Inicial
    if not state:
        response = (
            "🎮 **Escolha um jogo**:\n"
            "1. CS2\n"
            "2. Valorant\n"
            "3. League of Legends\n\n"
            "🔴 0. Sair"
        )
        user_states[user_id] = {'step': 1}
        return {'message': response, 'is_final': False}
    
    # Seleção de Jogo
    elif state['step'] == 1:
        try:
            choice = int(command)
            if choice == 0:
                return {'message': "❌ Conversa encerrada.", 'is_final': True}
            
            games = {
                1: {'name': 'CS2', 'code': 'counterstrike'},
                2: {'name': 'Valorant', 'code': 'valorant'},
                3: {'name': 'LoL', 'code': 'leagueoflegends'}
            }
            
            if choice not in games:
                return {'message': "⚠️ Opção inválida! Escolha 1, 2 ou 3.", 'is_final': False}
            
            game = games[choice]
            response = (
                f"📋 **Opções para {game['name']}**:\n"
                "1. 👥 Ver jogadores\n"
                "2. 📅 Últimas partidas\n\n"
                "🔴 0. Sair"
            )
            user_states[user_id] = {'step': 2, 'game': game['code'], 'game_name': game['name']}
            return {'message': response, 'is_final': False}
            
        except ValueError:
            return {'message': "⚠️ Opção inválida! Digite um número.", 'is_final': False}
    
    # Processar Escolha
    elif state['step'] == 2:
        try:
            choice = int(command)
            if choice == 0:
                return {'message': "❌ Conversa encerrada.", 'is_final': True}
            
            if choice not in [1, 2]:
                return {'message': "⚠️ Opção inválida! Escolha 1 ou 2.", 'is_final': False}
            
            game = state['game']
            game_name = state.get('game_name', game.upper())
            data_type = 'players' if choice == 1 else 'matches'
            data = get_esports_data(game, data_type)
            
            if choice == 1:
                response = f"👥 **Jogadores {game_name}**:\n" + "\n".join([f"• {p}" for p in data])
            else:
                response = f"📅 **Últimas partidas {game_name}**:\n" + "\n".join([f"• {m}" for m in data])
            
            response += "\n\n🔚 Digite @FuriaBot para novo comando"
            user_states.pop(user_id, None)
            return {'message': response, 'is_final': True}
            
        except Exception as e:
            print(f"Erro no bot: {e}")
            return {'message': "⚠️ Erro ao processar comando!", 'is_final': True}

# ---------------------------------------------------------------
# Socket Events
# ---------------------------------------------------------------

@socketio.on('send_message')
def handle_message(data):
    msg_text = data['message']
    msg_id = str(uuid.uuid4())
    
    if msg_text.startswith('@FuriaBot'):
        command = msg_text.replace('@FuriaBot', '').strip()
        bot_response = handle_bot_command(request.sid, command)
        
        emit('bot_message', {
            'id': msg_id,
            'message': bot_response['message'],
            'is_final': bot_response['is_final'],
            'timestamp': datetime.now().isoformat()
        }, room=request.sid)
    else:
        new_msg = {
            'id': msg_id,
            'message': msg_text,
            'is_bot': False,
            'timestamp': datetime.now().isoformat()
        }
        message_history.append(new_msg)
        emit('new_message', new_msg, broadcast=True)

@socketio.on('edit_message')
def handle_edit_message(data):
    for msg in message_history:
        if msg['id'] == data['id']:
            msg['message'] = data['message']
            emit('message_edited', data, broadcast=True)
            break

@socketio.on('delete_message')
def handle_delete_message(data):
    global message_history
    message_history = [msg for msg in message_history if msg['id'] != data['id']]
    emit('message_deleted', data['id'], broadcast=True)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')