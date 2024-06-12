from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import os
import json
import holidayapi
import sqlite3
import requests
import schedule
import threading
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
CORS(app,resources={r"/*":{"origins":"*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE = 'events.db'

# Retrieve environment variables
hoilday_key = os.getenv('HOILDAY_KEY')

logging.basicConfig(level=logging.INFO)


def get_db_connection():
    logging.info("DATABASE CONNECTED...")
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

     # Drop the events table if it exists
    # cursor.execute('DROP TABLE IF EXISTS events')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        description TEXT NOT NULL,
        participants TEXT NOT NULL,
        message_status BOOLEAN DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

initialize_db()

@app.route('/')
def index():
    try:
        logging.info("DATABASE CONNECTED...")
        conn = sqlite3.connect(DATABASE)  # Change 'your_database.db' to your SQLite database file
        cursor = conn.cursor()

        # SQLite query to get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        
        # Fetch all table names
        tables = cursor.fetchall()

        # Close connection
        conn.close()

        return tables

    except Exception as e:
        print("Error:", e)
        return None

@app.route('/add-event', methods=['POST'])
def add_record():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        title = data['title']
        start_date = data['start_date']
        end_date = data['end_date']
        description = data['description']
        participants = json.dumps(data['participants'])  # Convert participants to JSON string
        year = data['year']  # Removed unnecessary comma
        month = data['month']  # Removed unnecessary comma
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO events (title, start_date, end_date, description, participants, year, month) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (title, start_date, end_date, description, participants, year, month))
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()


        
        return jsonify({"success": "Event is successfully created !!", "status": event_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/update-event/<int:id>', methods=['PUT'])
def update_record(id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        title = data['title']
        start_date = data['start_date']
        end_date = data['end_date']
        description = data['description']
        participants = json.dumps(data['participants'])  # Convert participants to JSON string
        year = data['year']
        month = data['month']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE events SET title = ?, start_date = ?, end_date = ?, description = ?, participants = ?, year = ?, month = ? WHERE id = ?',
                    (title, start_date, end_date, description, participants, year, month, id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": "Event is successfully updated !!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/delete-event/<int:id>', methods=['DELETE'])
def delete_record(id):

    try:

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE from events WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": "Event is successfully deleted !!"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
@app.route('/events/<int:year>/<int:month>', methods=['GET'])
def get_events(year, month):
    
    if month < 1 or month > 12 :
        return jsonify({"error": "Month must be between 1 and 12"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, start_date, end_date, description, participants, year, month, message_status
        FROM events
                   WHERE year = ? and month = ?
        ''', (year, month))
    
    events = cursor.fetchall()
    conn.close()


    event_list = []
    for event in events:
        event_dict = dict(event)
        event_dict['participants'] = json.loads(event_dict['participants'])
        event_list.append(event_dict)


    return jsonify(event_list)

@app.route('/get-holidays', methods=['GET'])
def show_all():
    try:

        hapi = holidayapi.v1(hoilday_key)
        holidays = hapi.holidays({
        'country': 'NP',
        'year': '2023',
        })
        return jsonify(holidays)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/get-countries', methods=['GET'])
def show_countries():
    try:
        # API endpoint
        url = "https://holidayapi.com/v1/countries"

        # Query parameters
        params = {
            "key": hoilday_key,
            "pretty": "true"  # Optional parameter to format the response
        }

        # Sending GET request
        response = requests.get(url, params=params)
    
        # Checking response status
        if response.status_code == 200:
            # Parsing JSON response
            data = response.json()
             # Extract relevant information from the response
            countries = data.get('countries', [])

            # Create a list to store the country information
            country_list = []

            # Process each country's data
            for country in countries:
                country_name = country.get('name')
                country_code = country.get('code')
                country_flag = country.get('flag')

                # Add country information to the list
                country_info = {
                    'name': country_name,
                    'code': country_code,
                    'flag': country_flag
                }
                country_list.append(country_info)

            # Return the list of countries in JSON format
            return json.dumps(country_list)
        else:
            return jsonify({"Error:", response.status_code})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@socketio.on('connect')
def handle_connect():
    logging.info('Client Connected')

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Client Disconnected')

def send_notification(event_id, message):
    socketio.emit('event_notification', {'event_id': event_id, 'message': message})

@app.route('/test_emit')
def test_emit():
    # Emit a message to the client
    socketio.emit('event_notification', {'event_id': '12', 'message': 'notification eimited!!'})
    return 'Message sent to client'

def check_events():
    logging.info("Sending notifications...")
    current_time = datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, title, start_date, participants, message_status
                   FROM events 
                   WHERE start_date <= ? AND message_status = ? 
                   ''', (current_time, False))
    
    events = cursor.fetchall()
    conn.close()

    for event in events:
        event_id, title, start_date, participants, _ = event
        notification_time =  start_date - timedelta(hours=1)
        if current_time >= notification_time:
            send_notification(event_id, f'Event "{title}" starts in one hour!')
            update_event_status(event_id)

def update_event_status(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE events SET message_status = ? WHERE id = ?', (True, event_id))
    conn.commit()
    conn.close()

def schedule_notifications():
    logging.info("Schedule notifications...")
    schedule.every().minute.do(check_events)

def run_scheduler():
    logging.info("Run scheduler...")
    while True:
        schedule.run_pending()
        socketio.sleep(1)

schedule_notifications()
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.start()

if __name__ == '__main__':
    socketio.run(app, debug=True)
