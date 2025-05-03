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
# Configuração de Times por Jogo
# ---------------------------------------------------------------

GAME_TEAMS = {
    'counterstrike': ['FURIA', 'FURIA Academy', 'FURIA Female'],
    'valorant': ['FURIA', 'FURIA Academy', 'FURIA Female'],
    'leagueoflegends': ['FURIA', 'FURIA Youth']
}

# ---------------------------------------------------------------
# Implementação do Scraper da Liquipedia
# ---------------------------------------------------------------

LIQUIPEDIA_BASE = "https://liquipedia.net"

@cache
def get_esports_data(game, team, data_type):
    try:
        time.sleep(2)
        headers = {
            'User-Agent': 'FURIA Esports Bot/1.0 (+https://github.com/seu-repositorio)',
            'Accept-Language': 'pt-BR'
        }
        
        # Construir URL baseado no time
        team_slug = team.replace(' ', '_')
        base_url = f"{LIQUIPEDIA_BASE}/{game}/{team_slug}"
        
        if data_type == 'players':
            page = requests.get(base_url, headers=headers, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.content, 'html.parser')
            return parse_players(soup)
            
        elif data_type == 'matches':
            if game == 'leagueoflegends':
                page_url = f"{base_url}/Played_Matches"
            else:
                page_url = f"{base_url}/Matches"
            
            page = requests.get(page_url, headers=headers, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.content, 'html.parser')
            return parse_matches(soup, game)
            
    except Exception as e:
        print(f"Erro ao buscar {data_type} de {team} ({game}): {str(e)}")
        return [f"Erro temporário. Por favor, tente novamente mais tarde."]

def parse_match_result(result_str, team="FURIA"):
    """Analisa o placar e adiciona emoji de vitória/derrota"""
    if not result_str or ':' not in result_str:
        return result_str  # Retorna o original se inválido
    
    try:
        x, y = map(int, result_str.split(':'))
        
        # Verifica qual time é a FURIA (baseado na posição)
        if x > y:
            return f"{result_str} | ✅ Vitória"
        elif y > x:
            return f"{result_str} | ❌ Derrota"
        else:
            return f"{result_str} | ⚡ Empate"
            
    except ValueError:
        return result_str  # Retorna o placar mesmo se não for números

def parse_players(soup):
    """Extrai lista de jogadores com posições e tratamento de páginas inexistentes"""
    players = []
    roster_table = soup.find('table', {'class': 'roster-card'})
    
    if roster_table:
        for player_row in roster_table.find_all('tr', {'class': 'Player'}):
            # Extrair nome do jogador
            name = None
            id_cell = player_row.find('td', {'class': 'ID'})
            if id_cell:
                player_link = id_cell.find('a', href=True)
                if player_link:
                    # Remover "(page does not exist)" do nome
                    raw_name = player_link.get('title', '')
                    name = raw_name.replace(' (page does not exist)', '')
                else:
                    bold_name = id_cell.find('b')
                    if bold_name:
                        name = bold_name.get_text(strip=True)
            
            # Extrair posição
            position = ""
            position_cell = player_row.find('td', {'class': 'Position'})
            if position_cell:
                position = position_cell.get_text(strip=True)
                # Limpar formatação da posição
                position = position.split('.')[-1]
                position = position.replace('Role:', '').replace('(', '').replace(')', '').strip()
                position = position.replace('&nbsp;', ' ').strip()
            
            # Formatar entrada
            if name:
                if position:
                    players.append(f"{name} - ({position})")
                else:
                    players.append(name)
    
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
                result_match = cols[7].get_text(strip=True)
                team2 = cols[8].get_text(strip=True) if len(cols) > 8 else "TBD"
                
                # Formatação corrigida
                formatted_result = parse_match_result(result_match)
                matches.append(f"{date} | {team1} vs {team2} - {event} | {formatted_result}")
    
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
                result_match = cols[5].get_text(strip=True)
                team2 = cols[6].get_text(strip=True) if len(cols) > 6 else "TBD"
                
                formatted_result = parse_match_result(result_match)
                matches.append(f"{date} | FURIA vs {team2} - {event} | {formatted_result}")
    
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
            teams = GAME_TEAMS[game['code']]
            
            team_options = "\n".join([f"{i+1}. {team}" for i, team in enumerate(teams)])
            response = (
                f"🏆 **Times disponíveis para {game['name']}**:\n"
                f"{team_options}\n\n"
                "🔴 0. Sair"
            )
            
            user_states[user_id] = {
                'step': 2,
                'game_code': game['code'],
                'game_name': game['name'],
                'teams': teams
            }
            return {'message': response, 'is_final': False}
            
        except ValueError:
            return {'message': "⚠️ Opção inválida! Digite um número.", 'is_final': False}
    
    # Seleção de Time
    elif state['step'] == 2:
        try:
            choice = int(command)
            if choice == 0:
                return {'message': "❌ Conversa encerrada.", 'is_final': True}
            
            teams = state['teams']
            if choice < 1 or choice > len(teams):
                return {'message': "⚠️ Opção inválida! Escolha um número da lista.", 'is_final': False}
            
            selected_team = teams[choice-1]
            
            response = (
                f"📋 **Opções para {selected_team} - {state['game_name']}**:\n"
                "1. 👥 Ver jogadores\n"
                "2. 📅 Últimas partidas\n\n"
                "🔴 0. Sair"
            )
            
            user_states[user_id] = {
                'step': 3,
                'game_code': state['game_code'],
                'game_name': state['game_name'],
                'team': selected_team
            }
            return {'message': response, 'is_final': False}
            
        except ValueError:
            return {'message': "⚠️ Opção inválida! Digite um número.", 'is_final': False}
    
    # Processar Escolha de Dados
    elif state['step'] == 3:
        try:
            choice = int(command)
            if choice == 0:
                return {'message': "❌ Conversa encerrada.", 'is_final': True}
            
            if choice not in [1, 2]:
                return {'message': "⚠️ Opção inválida! Escolha 1 ou 2.", 'is_final': False}
            
            data_type = 'players' if choice == 1 else 'matches'
            data = get_esports_data(state['game_code'], state['team'], data_type)
            
            if choice == 1:
                response = f"👥 **Jogadores {state['team']} ({state['game_name']})**:\n" + "\n".join([f"• {p}" for p in data])
            else:
                response = f"📅 **Últimas partidas {state['team']} ({state['game_name']})**:\n" + "\n".join([f"• {m}" for m in data])
            
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