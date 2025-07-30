
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

from flask import send_file
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
# --- EXPORT RESULTS TO PDF ROUTE ---

@app.route('/export_results_pdf')
def export_results_pdf():
    selected_event_id = request.args.get('event_id')
    selected_sub_event_id = request.args.get('sub_event_id')
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (selected_event_id,)).fetchone() if selected_event_id else None
    sub_event = conn.execute('SELECT * FROM sub_events WHERE id = ?', (selected_sub_event_id,)).fetchone() if selected_sub_event_id else None
    entries = []
    if selected_sub_event_id:
        entries = conn.execute('SELECT name, house, year, time FROM entries WHERE sub_event_id = ? ORDER BY time ASC', (selected_sub_event_id,)).fetchall()
    elif selected_event_id:
        sub_events = conn.execute('SELECT id FROM sub_events WHERE event_id = ?', (selected_event_id,)).fetchall()
        sub_event_ids = [str(sub['id']) for sub in sub_events]
        if sub_event_ids:
            placeholders = ','.join(['?'] * len(sub_event_ids))
            query = f'SELECT name, house, year, time FROM entries WHERE sub_event_id IN ({placeholders}) ORDER BY time ASC'
            entries = conn.execute(query, sub_event_ids).fetchall()
    conn.close()
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    title = f"Results for {event['name']} ({event['year']})"
    if sub_event:
        title += f" - {sub_event['name']}"
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, title)
    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Place")
    p.drawString(100, y, "Name")
    p.drawString(250, y, "House")
    p.drawString(350, y, "Year Level")
    p.drawString(450, y, "Time")
    y -= 20
    p.setFont("Helvetica", 12)
    for idx, row in enumerate(entries, 1):
        if y < 50:
            p.showPage()
            y = height - 50
        p.drawString(50, y, str(idx))
        p.drawString(100, y, str(row['name']))
        p.drawString(250, y, str(row['house']))
        p.drawString(350, y, str(row['year']))
        p.drawString(450, y, str(row['time']))
        y -= 20
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="results.pdf", mimetype='application/pdf')

# --- DELETE ENTRY ROUTE ---
@app.route('/delete_entry/<int:event_id>/<int:row_id>', methods=['POST'])
def delete_entry(event_id, row_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM entries WHERE id = ?', (row_id,))
    conn.commit()
    conn.close()
    flash('Entry deleted successfully.', 'success')
    return redirect(url_for('edit_event', event_id=event_id))

# --- EDIT ENTRY ROUTE ---
@app.route('/edit_entry/<int:event_id>/<int:row_id>', methods=['GET', 'POST'])
def edit_entry(event_id, row_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (row_id,)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        house = request.form['house']
        year = request.form['year']
        time = request.form['time']
        conn.execute('UPDATE entries SET name = ?, house = ?, year = ?, time = ? WHERE id = ?',
                     (name, house, year, time, row_id))
        conn.commit()
        conn.close()
        return redirect(url_for('edit_event', event_id=event_id))
    conn.close()
    return render_template('edit_entry.html', event_id=event_id, entry=entry, logged_in=True, username=session['username'])

# --- DELETE EVENT ROUTE ---
@app.route('/delete/<int:event_id>', methods=['POST', 'GET'])
def delete_event(event_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.execute('DELETE FROM entries WHERE event_id = ?', (event_id,))
    conn.commit()
    conn.close()
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('edit_events'))

# --- ADD ENTRY ROUTE ---
@app.route('/add_entry/<int:event_id>', methods=['GET', 'POST'])
def add_entry(event_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    sub_events = conn.execute('SELECT * FROM sub_events WHERE event_id = ?', (event_id,)).fetchall()
    if request.method == 'POST':
        name = request.form['name']
        house = request.form['house']
        year = request.form['year']
        time = request.form['time']
        sub_event_id = request.form.get('sub_event_id')
        if not sub_event_id:
            flash('Please select a sub-event.', 'danger')
            conn.close()
            return render_template('add_entry.html', event_id=event_id, sub_events=sub_events, logged_in=True, username=session['username'])
        conn.execute('INSERT INTO entries (sub_event_id, name, house, year, time) VALUES (?, ?, ?, ?, ?)',
                     (sub_event_id, name, house, year, time))
        conn.commit()
        conn.close()
        return redirect(url_for('edit_event', event_id=event_id))
    conn.close()
    return render_template('add_entry.html', event_id=event_id, sub_events=sub_events, logged_in=True, username=session['username'])

# Change home route to show public results page for everyone
@app.route('/')
def home():
    if 'logged_in' in session:
        return render_template('admin_home.html', logged_in=True, username=session['username'])
    else:
        conn = get_db_connection()
        events = conn.execute('SELECT * FROM events ORDER BY id').fetchall()
        selected_event_id = request.args.get('event_id')
        selected_sub_event_id = request.args.get('sub_event_id')
        sub_events = []
        results = []
        if selected_event_id:
            try:
                event_id_int = int(selected_event_id)
                sub_events = conn.execute('SELECT * FROM sub_events WHERE event_id = ?', (event_id_int,)).fetchall()
                if selected_sub_event_id:
                    results = conn.execute('SELECT name, house, time FROM entries WHERE sub_event_id = ? ORDER BY time ASC', (selected_sub_event_id,)).fetchall()
                else:
                    sub_event_ids = [str(sub['id']) for sub in sub_events]
                    if sub_event_ids:
                        placeholders = ','.join(['?'] * len(sub_event_ids))
                        query = f'SELECT name, house, time FROM entries WHERE sub_event_id IN ({placeholders}) ORDER BY time ASC'
                        results = conn.execute(query, sub_event_ids).fetchall()
                    else:
                        results = []
            except ValueError:
                results = []
        conn.close()
        return render_template('public_results.html', events=events, sub_events=sub_events, results=results,
                               selected_event_id=selected_event_id,
                               selected_sub_event_id=selected_sub_event_id,
                               logged_in=False, username=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Incorrect username or password', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/edit')
def edit_events():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    return render_template('main.html', events=events, logged_in=True, username=session['username'])


# --- EDIT EVENT ROUTE WITH SUB-EVENTS ---
@app.route('/edit/<int:event_id>')
def edit_event(event_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    sub_events = conn.execute('SELECT * FROM sub_events WHERE event_id = ?', (event_id,)).fetchall()
    selected_sub_event_id = request.args.get('sub_event_id')
    entries = []
    if selected_sub_event_id:
        entries = conn.execute('SELECT * FROM entries WHERE sub_event_id = ?', (selected_sub_event_id,)).fetchall()
    conn.close()
    return render_template('edit.html', event=event, sub_events=sub_events, entries=entries, selected_sub_event_id=selected_sub_event_id, logged_in=True, username=session['username'])

# --- ADD SUB-EVENT ROUTE ---
@app.route('/add_sub_event/<int:event_id>', methods=['POST'])
def add_sub_event(event_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    name = request.form['sub_event_name']
    conn = get_db_connection()
    conn.execute('INSERT INTO sub_events (event_id, name) VALUES (?, ?)', (event_id, name))
    conn.commit()
    conn.close()
    flash('Sub-event added successfully.', 'success')
    return redirect(url_for('edit_event', event_id=event_id))

# --- DELETE SUB-EVENT ROUTE ---
@app.route('/delete_sub_event/<int:event_id>/<int:sub_event_id>', methods=['POST'])
def delete_sub_event(event_id, sub_event_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM sub_events WHERE id = ?', (sub_event_id,))
    conn.execute('DELETE FROM entries WHERE sub_event_id = ?', (sub_event_id,))
    conn.commit()
    conn.close()
    flash('Sub-event deleted successfully.', 'success')
    return redirect(url_for('edit_event', event_id=event_id))

@app.route('/events/create', methods=['GET', 'POST'])
def create_event():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['event_name']
        year = request.form['year']
        with get_db_connection() as conn:
            conn.execute('INSERT INTO events (name, year) VALUES (?, ?)', (name, year))
            conn.commit()
        return redirect(url_for('edit_events'))
    return render_template('create_event.html', logged_in=True, username=session['username'])

@app.route('/results')
def results():
    if 'logged_in' not in session:
        return redirect(url_for('public_results'))
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events').fetchall()
    selected_event_id = request.args.get('event_id') or request.args.get('event')
    selected_sub_event_id = request.args.get('sub_event_id')
    sub_events = []
    entries = []
    event_options = conn.execute('SELECT id, name, year FROM events').fetchall()
    if selected_event_id:
        sub_events = conn.execute('SELECT * FROM sub_events WHERE event_id = ?', (selected_event_id,)).fetchall()
        if selected_sub_event_id:
            entries = conn.execute('SELECT name, house, year, time FROM entries WHERE sub_event_id = ? ORDER BY time ASC', (selected_sub_event_id,)).fetchall()
    conn.close()
    return render_template('results.html', events=events, sub_events=sub_events, entries=entries,
                           event_options=event_options,
                           selected_event_id=selected_event_id,
                           selected_sub_event_id=selected_sub_event_id,
                           logged_in=True, username=session['username'])



if __name__ == '__main__':
    conn = get_db_connection()
    # Create tables if they don't exist
    conn.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, name TEXT, year INTEGER)')
    conn.execute('''CREATE TABLE IF NOT EXISTS sub_events (
        id INTEGER PRIMARY KEY,
        event_id INTEGER,
        name TEXT,
        FOREIGN KEY(event_id) REFERENCES events(id)
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY,
        sub_event_id INTEGER,
        name TEXT,
        house TEXT,
        year INTEGER,
        time TEXT,
        FOREIGN KEY(sub_event_id) REFERENCES sub_events(id)
    )''')
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
    conn.commit()
    conn.close()
    app.run(debug=True)
    