from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import os
import json
import holidayapi
import sqlite3

app = Flask(__name__)
CORS(app)

DATABASE = 'events.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        description TEXT NOT NULL,
        participants TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

initialize_db()

@app.route('/')
def index():
    try:
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

    
@app.route('/events/<int:year>/<int:month>', methods=['GET'])
def get_events(year, month):
    
    if month < 1 or month > 12 :
        return jsonify({"error": "Month must be between 1 and 12"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, start_date, end_date, description, participants, year, month
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
        key = '56a163e6-6872-4daa-8cc1-b8538e476247'
        hapi = holidayapi.v1(key)
        holidays = hapi.holidays({
        'country': 'NP',
        'year': '2023',
        })
        return jsonify(holidays)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_ENV') == 'development')