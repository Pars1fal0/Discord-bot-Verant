from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__, static_folder='.')
CORS(app)

# Путь к корневой директории бота
BOT_DIR = Path(__file__).parent.parent

def load_json_file(filename):
    """Загрузка JSON файла с обработкой ошибок"""
    try:
        filepath = BOT_DIR / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Ошибка загрузки {filename}: {e}")
        return {}

def get_user_count(data):
    """Получить количество пользователей"""
    return len(data) if isinstance(data, dict) else 0

def calculate_total_balance(economy_data):
    """Подсчитать общий баланс всех пользователей"""
    total = 0
    for user_data in economy_data.values():
        total += user_data.get('balance', 0)
    return total

def get_top_users(data, key, limit=10):
    """Получить топ пользователей по ключу"""
    users = []
    for user_id, user_data in data.items():
        value = user_data.get(key, 0)
        users.append({
            'user_id': user_id,
            'value': value,
            'data': user_data
        })
    users.sort(key=lambda x: x['value'], reverse=True)
    return users[:limit]

@app.route('/')
def index():
    """Главная страница дашборда"""
    return send_from_directory('.', 'index.html')

@app.route('/api/economy')
def get_economy():
    """Получить экономические данные"""
    data = load_json_file('economy.json')
    return jsonify(data)

@app.route('/api/levels')
def get_levels():
    """Получить данные уровней"""
    data = load_json_file('levels.json')
    return jsonify(data)

@app.route('/api/pvp')
def get_pvp():
    """Получить PvP статистику"""
    data = load_json_file('pvp_stats.json')
    return jsonify(data)

@app.route('/api/business')
def get_business():
    """Получить данные бизнесов"""
    data = load_json_file('business.json')
    return jsonify(data)

@app.route('/api/stocks')
def get_stocks():
    """Получить данные биржи"""
    data = load_json_file('stocks.json')
    return jsonify(data)

@app.route('/api/bank')
def get_bank():
    """Получить банковские данные"""
    data = load_json_file('bank.json')
    return jsonify(data)

@app.route('/api/tournaments')
def get_tournaments():
    """Получить данные турниров"""
    data = load_json_file('tournaments.json')
    return jsonify(data)

@app.route('/api/enhancements')
def get_enhancements():
    """Получить данные улучшений"""
    data = load_json_file('enhancements.json')
    return jsonify(data)

@app.route('/api/stats')
def get_stats():
    """Получить агрегированную статистику"""
    economy = load_json_file('economy.json')
    levels = load_json_file('levels.json')
    pvp = load_json_file('pvp_stats.json')
    business = load_json_file('business.json')
    bank = load_json_file('bank.json')
    
    # Общая статистика
    total_users = max(
        get_user_count(economy),
        get_user_count(levels),
        get_user_count(pvp)
    )
    
    total_balance = calculate_total_balance(economy)
    
    # Подсчет общего банковского баланса
    total_bank_balance = 0
    total_loans = 0
    for user_data in bank.values():
        total_bank_balance += user_data.get('deposit', 0)  # Исправлено: deposit вместо balance
        total_loans += user_data.get('loan', 0)
    
    # Подсчет бизнесов
    total_businesses = 0
    for user_businesses in business.values():
        total_businesses += len(user_businesses)
    
    # Подсчет игровой статистики
    total_games_played = 0
    total_games_won = 0
    for user_data in economy.values():
        game_stats = user_data.get('game_stats', {})
        total_games_played += (
            game_stats.get('slots_played', 0) +
            game_stats.get('roulette_played', 0) +
            game_stats.get('coinflip_played', 0)
        )
        total_games_won += (
            game_stats.get('slots_won', 0) +
            game_stats.get('roulette_won', 0) +
            game_stats.get('coinflip_won', 0)
        )
    
    # Подсчет PvP статистики
    total_duels = 0
    for user_data in pvp.values():
        total_duels += user_data.get('wins', 0) + user_data.get('losses', 0)
    
    # Топ пользователей
    top_rich = get_top_users(economy, 'balance', 10)
    top_levels = get_top_users(levels, 'level', 10)
    
    # Топ PvP
    top_pvp = []
    for user_id, user_data in pvp.items():
        wins = user_data.get('wins', 0)
        top_pvp.append({
            'user_id': user_id,
            'wins': wins,
            'losses': user_data.get('losses', 0),
            'rank': user_data.get('rank', 'Новичок')
        })
    top_pvp.sort(key=lambda x: x['wins'], reverse=True)
    top_pvp = top_pvp[:10]
    
    stats = {
        'overview': {
            'total_users': total_users,
            'total_balance': total_balance,
            'total_bank_balance': total_bank_balance,
            'total_loans': total_loans,
            'total_businesses': total_businesses,
            'total_games_played': total_games_played,
            'total_games_won': total_games_won,
            'total_duels': total_duels,
            'timestamp': datetime.now().isoformat()
        },
        'leaderboards': {
            'top_rich': top_rich,
            'top_levels': top_levels,
            'top_pvp': top_pvp
        }
    }
    
    return jsonify(stats)

@app.route('/api/transactions')
def get_recent_transactions():
    """Получить последние транзакции"""
    economy = load_json_file('economy.json')
    all_transactions = []
    
    for user_id, user_data in economy.items():
        transactions = user_data.get('transactions', [])
        for trans in transactions:
            trans_copy = trans.copy()
            trans_copy['user_id'] = user_id
            all_transactions.append(trans_copy)
    
    # Сортировка по времени
    all_transactions.sort(
        key=lambda x: x.get('timestamp', ''),
        reverse=True
    )
    
    # Возвращаем последние 50 транзакций
    return jsonify(all_transactions[:50])

if __name__ == '__main__':
    print('🚀 Dashboard API запущен на http://localhost:5001')
    print('📊 Доступные эндпоинты:')
    print('   - http://localhost:5001/api/economy')
    print('   - http://localhost:5001/api/levels')
    print('   - http://localhost:5001/api/pvp')
    print('   - http://localhost:5001/api/business')
    print('   - http://localhost:5001/api/stats')
    print('   - http://localhost:5001/api/transactions')
    app.run(debug=True, host='0.0.0.0', port=5001)
