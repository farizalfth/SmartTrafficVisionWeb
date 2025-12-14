# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import mysql.connector
import os
from functools import wraps
import datetime
import random 

app = Flask(__name__)
app.secret_key = "smart_traffic_secret"

# ===== UPLOAD CONFIG =====
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== KONEKSI DATABASE =====
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="smart_traffic"
)

def get_db_cursor(dictionary=True):
    if not db.is_connected():
        db.reconnect()
    return db.cursor(dictionary=dictionary)

# ===== DECORATORS (KEAMANAN) =====
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash("Silahkan login terlebih dahulu!", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# =========================================================================
# ===== SHARED LOGIC (LOGIKA DATA) =====
# =========================================================================

def fetch_cctv_list():
    return [
        { "id": 1, "name": "CCTV Pontianak (Simpang Garuda)", "lat": -0.0245, "lon": 109.3406, "status": "Aktif", "stream_url": "https://www.youtube.com/embed/1s9cRcqZf58" },
        { "id": 2, "name": "CCTV Pontianak (Tugu Khatulistiwa)", "lat": 0.0000, "lon": 109.3300, "status": "Aktif", "stream_url": "https://www.youtube.com/embed/oqSqC-gOALo" },
        { "id": 3, "name": "CCTV Demak (Alun-Alun)", "lat": -6.8906, "lon": 110.6385, "status": "Aktif", "stream_url": "https://www.youtube.com/embed/mHk5UKckU7M" },
        { "id": 4, "name": "CCTV Demak (Pasar Bintoro)", "lat": -6.8850, "lon": 110.6400, "status": "Aktif", "stream_url": "https://www.youtube.com/embed/7c4CsGkmBu8" },
        { "id": 5, "name": "CCTV Demak (Pertigaan Trengguli)", "lat": -6.8700, "lon": 110.6500, "status": "Aktif", "stream_url": "https://www.youtube.com/embed/5nw3G2jtWaU" },
    ]

def logic_get_summary(cctv_id):
    # JIKA TIDAK ADA CCTV YANG DIPILIH, KEMBALIKAN KOSONG (-)
    if not cctv_id:
        return {
            "kendaraan_hari_ini": "-", 
            "kepadatan_tertinggi": "-", 
            "rata_rata_kecepatan": "-", 
            "kamera_aktif": "-" 
        }

    # Jika ada CCTV dipilih, hitung data (Simulasi)
    try:
        cctv_id = int(cctv_id)
        # Total kamera selalu 5 (tetap tampil meski filter aktif)
        active_cams = "5" 
        
        if cctv_id == 1:
            return {"kendaraan_hari_ini": "5.120", "kepadatan_tertinggi": "92%", "rata_rata_kecepatan": "25 km/j", "kamera_aktif": active_cams}
        elif cctv_id == 2:
            return {"kendaraan_hari_ini": "1.200", "kepadatan_tertinggi": "40%", "rata_rata_kecepatan": "60 km/j", "kamera_aktif": active_cams}
        else:
            return {
                "kendaraan_hari_ini": str(random.randint(2000, 4000)),
                "kepadatan_tertinggi": str(random.randint(50, 80)) + "%",
                "rata_rata_kecepatan": str(random.randint(30, 50)) + " km/j",
                "kamera_aktif": active_cams
            }
    except ValueError:
        return {"kendaraan_hari_ini": "-", "kepadatan_tertinggi": "-", "rata_rata_kecepatan": "-", "kamera_aktif": "-"}

def logic_get_traffic(cctv_id, period):
    # Label Sumbu X
    if period == 'mingguan': labels = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    elif period == 'bulanan': labels = ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4']
    else: labels = ['06:00','08:00','10:00','12:00','14:00','16:00','18:00']

    # JIKA TIDAK ADA CCTV, KEMBALIKAN DATA KOSONG (Array 0)
    if not cctv_id:
        return {"labels": labels, "kepadatan": [0] * len(labels)}

    data_points = len(labels)
    kepadatan = []
    
    try:
        cctv_id = int(cctv_id)
        base_val = 70 if cctv_id == 1 else (25 if cctv_id == 2 else 50)
        for _ in range(data_points):
            kepadatan.append(max(0, min(100, base_val + random.randint(-15, 15))))
    except:
        kepadatan = [0] * data_points

    return {"labels": labels, "kepadatan": kepadatan}

def logic_get_vehicle(cctv_id, period):
    labels = ['Mobil','Motor','Bus','Truk']
    
    # JIKA TIDAK ADA CCTV, KEMBALIKAN DATA KOSONG
    if not cctv_id:
        return {"labels": labels, "data": [0, 0, 0, 0]}

    data = [55, 30, 8, 7] # Default base

    try:
        cctv_id = int(cctv_id)
        if cctv_id == 1: data = [45, 45, 5, 5]
        elif cctv_id == 5: data = [20, 10, 15, 55]
        else: data = [50, 30, 10, 10]
    except:
        pass

    modifier = 0 if period == 'harian' else (5 if period == 'mingguan' else 15)
    data = [max(0, x + random.randint(-modifier, modifier)) for x in data]

    return {"labels": labels, "data": data}

# =========================================================================
# ===== ROUTES WEB (Render Template) =====
# =========================================================================

@app.route('/')
def index():
    cursor = get_db_cursor()
    cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE published=1 ORDER BY tanggal DESC LIMIT 5")
    latest_articles = cursor.fetchall()
    cursor.close()
    return render_template('index.html', latest_articles=latest_articles)

@app.route('/dashboard')
def dashboard():
    cursor = get_db_cursor()
    cursor.execute("SELECT id, judul, gambar, tanggal FROM artikel WHERE published=1 ORDER BY tanggal DESC LIMIT 3")
    latest_articles = cursor.fetchall()
    cursor.close()
    cctv_list = fetch_cctv_list()
    return render_template('dashboard.html', latest_articles=latest_articles, cctv_list=cctv_list)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "admin" and password == "12345":
            session['user'] = 'admin'
            flash("Login Berhasil!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Username atau password salah!", "danger")
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    cursor = get_db_cursor()
    cursor.execute("SELECT id, judul, gambar, tanggal FROM artikel ORDER BY tanggal DESC LIMIT 3")
    latest_articles = cursor.fetchall()
    cursor.close()
    cctv_list = fetch_cctv_list()
    return render_template('admin_dashboard.html', latest_articles=latest_articles, cctv_list=cctv_list)

# --- ARTIKEL ROUTES ---
@app.route('/kelola_artikel')
@login_required
def kelola_artikel():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    offset = (page - 1) * per_page
    cursor = get_db_cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM artikel")
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page
    cursor.execute("SELECT id, judul, isi, gambar, published, tanggal FROM artikel ORDER BY tanggal DESC LIMIT %s OFFSET %s", (per_page, offset))
    data = cursor.fetchall()
    cursor.close()
    return render_template('kelola_artikel.html', artikel=data, page=page, total_pages=total_pages, per_page=per_page)

# --- Update Route Tambah Artikel ---
@app.route('/artikel/tambah', methods=['GET', 'POST'])
@login_required
def tambah_artikel():
    if request.method == 'POST':
        judul = request.form['judul']
        isi = request.form['isi']
        tanggal_str = request.form['tanggal'] # Ambil tanggal dari form (String)

        file = request.files.get('gambar')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cursor = get_db_cursor()
        cursor.execute(
            "INSERT INTO artikel (judul, isi, gambar, published, tanggal) VALUES (%s, %s, %s, %s, %s)",
            (judul, isi, filename, 0, tanggal_str) # Gunakan tanggal_str dari input
        )
        db.commit()
        cursor.close()
        flash("Artikel berhasil ditambahkan!", "success")
        return redirect(url_for('kelola_artikel'))

    return render_template('crud_artikel.html', mode='tambah', artikel=None)

# --- Update Route Edit Artikel ---
@app.route('/artikel/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_artikel(id):
    next_page = request.args.get('next', url_for('kelola_artikel'))
    cursor = get_db_cursor()

    if request.method == 'POST':
        judul = request.form['judul']
        isi = request.form['isi']
        tanggal_str = request.form['tanggal'] # Ambil tanggal baru dari form

        file = request.files.get('gambar')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Update dengan gambar baru + tanggal baru
            cursor.execute("UPDATE artikel SET judul=%s, isi=%s, gambar=%s, tanggal=%s WHERE id=%s", (judul, isi, filename, tanggal_str, id))
        else:
            # Update tanpa gambar baru + tanggal baru
            cursor.execute("UPDATE artikel SET judul=%s, isi=%s, tanggal=%s WHERE id=%s", (judul, isi, tanggal_str, id))
        
        db.commit()
        cursor.close()
        flash("Artikel berhasil diperbarui!", "success")
        return redirect(next_page)

    cursor.execute("SELECT * FROM artikel WHERE id=%s", (id,))
    data = cursor.fetchone()
    cursor.close()
    return render_template('crud_artikel.html', mode='edit', artikel=data)

@app.route('/artikel/hapus/<int:id>')
@login_required
def hapus_artikel(id):
    cursor = get_db_cursor()
    cursor.execute("DELETE FROM artikel WHERE id=%s", (id,))
    db.commit()
    cursor.close()
    flash("Artikel berhasil dihapus!", "danger")
    return redirect(url_for('kelola_artikel'))

@app.route('/artikel/publish/<int:id>')
@login_required
def publish_artikel(id):
    cursor = get_db_cursor()
    try:
        cursor.execute("UPDATE artikel SET published = 1 WHERE id = %s", (id,))
        db.commit()
        flash("Artikel berhasil dipublish!", "success")
    except:
        db.rollback()
        flash("Gagal mempublish artikel", "danger")
    finally:
        cursor.close()
    return redirect(url_for('kelola_artikel'))

@app.route('/artikel/batal_publish/<int:id>')
@login_required
def batal_publish(id):
    cursor = get_db_cursor()
    try:
        cursor.execute("UPDATE artikel SET published = 0 WHERE id = %s", (id,))
        db.commit()
        flash("Artikel berhasil dibatalkan publikasinya!", "warning")
    except:
        db.rollback()
        flash("Gagal membatalkan publikasi", "danger")
    finally:
        cursor.close()
    return redirect(url_for('kelola_artikel'))

@app.route('/read_artikel')
def read_artikel():
    cursor = get_db_cursor()
    cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE published=1 ORDER BY tanggal DESC")
    data = cursor.fetchall()
    cursor.close()
    return render_template('read_artikel.html', artikel=data)

@app.route('/artikel/<int:id>')
def view_artikel_detail(id):
    cursor = get_db_cursor()
    # Query untuk mengambil data 1 artikel berdasarkan ID
    cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE id=%s AND published=1", (id,))
    artikel = cursor.fetchone()
    cursor.close()
    
    if artikel:
        return render_template('artikel_detail.html', artikel=artikel)
    else:
        flash("Artikel tidak ditemukan atau belum dipublikasikan.", "danger")
        return redirect(url_for('read_artikel'))

@app.route('/about')
def about():
    return render_template('aboutme.html')

@app.route('/cctv-page')
def cctv_page():
    return render_template('cctv.html')

@app.route('/static-page')
def static_page():
    return render_template('static.html')

# =========================================================================
# ===== API ENDPOINTS =====
# =========================================================================

# --- 1. API UNTUK DASHBOARD (Admin & Public) ---
# Menggunakan 'logic_' yang mengembalikan data kosong jika cctv_id null

@app.route('/api/admin/dashboard_summary', methods=['GET'])
@api_login_required
def api_admin_dashboard_summary():
    return jsonify(logic_get_summary(request.args.get('cctv_id')))

@app.route('/api/admin/traffic_data', methods=['GET'])
@api_login_required
def api_admin_traffic_data():
    return jsonify(logic_get_traffic(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/admin/vehicle_distribution', methods=['GET'])
@api_login_required
def api_admin_vehicle_distribution():
    return jsonify(logic_get_vehicle(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/public/dashboard_summary', methods=['GET'])
def api_public_dashboard_summary():
    return jsonify(logic_get_summary(request.args.get('cctv_id')))

@app.route('/api/public/traffic_data', methods=['GET'])
def api_public_traffic_data():
    return jsonify(logic_get_traffic(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/public/vehicle_distribution', methods=['GET'])
def api_public_vehicle_distribution():
    return jsonify(logic_get_vehicle(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/public/analytics_data', methods=['GET'])
def api_public_analytics_data():
    period = request.args.get('period', 'harian')
    cctv_id = request.args.get('cctv_id') # Ambil parameter CCTV ID
    
    # 1. Tentukan Labels Sumbu X
    if period == 'mingguan':
        labels = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
    elif period == 'bulanan':
        labels = ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4']
    else: # Harian
        labels = ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00']

    data_len = len(labels)
    traffic = []

    # 2. LOGIKA: Jika tidak ada CCTV dipilih, kembalikan data 0
    if not cctv_id:
        return jsonify({
            "labels": labels,
            "traffic": [0] * data_len
        })

    # 3. Jika ada CCTV, Generate Data Simulasi
    try:
        cctv_id = int(cctv_id)
        # Variasi base value berdasarkan ID agar grafik terlihat beda tiap CCTV
        if cctv_id == 1: base_val = 75
        elif cctv_id == 2: base_val = 30
        elif cctv_id == 3: base_val = 55
        else: base_val = 45
        
        for _ in range(data_len):
            val = base_val + random.randint(-15, 20) 
            val = max(0, min(100, val)) # Clip antara 0-100
            traffic.append(val)
            
    except:
        traffic = [0] * data_len

    return jsonify({
        "labels": labels,
        "traffic": traffic
    })
# --- 3. API UMUM ---
@app.route('/api/cctv_locations', methods=['GET'])
def get_cctv_locations():
    return jsonify(fetch_cctv_list()), 200

if __name__ == '__main__':
    app.run(debug=True)