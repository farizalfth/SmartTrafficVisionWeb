# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import mysql.connector
import os
from functools import wraps
import datetime
import random
import cv2
import base64
import numpy as np
from ultralytics import YOLO
from cap_from_youtube import cap_from_youtube

app = Flask(__name__)
app.secret_key = "smart_traffic_secret"

# ===== UPLOAD CONFIG =====
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ===== LOAD YOLO MODEL =====
print("Sedang memuat Model AI (YOLO)...")
try:
    model = YOLO("yolo11n.pt") 
    print("Model AI Siap!")
except Exception as e:
    print(f"Error loading YOLO: {e}")

# COCO Class ID: 2=Car, 3=Motorcycle, 5=Bus, 7=Truck
VEHICLE_CLASSES = [2, 3, 5, 7]

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

# ===== DECORATORS =====
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
# ===== AI ENGINE (REAL TIME DETECTION) =====
# =========================================================================

def get_real_vehicle_count(video_url):
    """
    Mengambil snapshot dari YouTube dan menghitung kendaraan menggunakan YOLO.
    Digunakan untuk data statistik angka saja.
    """
    counts = {'mobil': 0, 'motor': 0, 'bus': 0, 'truk': 0}
    try:
        # Resolusi '360p' agar proses download dan deteksi cepat
        cap = cap_from_youtube(video_url, '360p')
        if not cap.isOpened(): return counts

        ret, frame = cap.read()
        if ret:
            results = model(frame, classes=VEHICLE_CLASSES, verbose=False)
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    if cls == 2: counts['mobil'] += 1
                    elif cls == 3: counts['motor'] += 1
                    elif cls == 5: counts['bus'] += 1
                    elif cls == 7: counts['truk'] += 1
        cap.release()
        return counts
    except Exception as e:
        print(f"Error Deteksi: {e}")
        return counts

def get_annotated_frame(video_url):
    """
    Sama seperti di atas, tapi mengembalikan GAMBAR dengan KOTAK MERAH (Base64).
    Digunakan untuk fitur 'Deteksi Kendaraan' (Visual) di Dashboard.
    """
    counts = {'mobil': 0, 'motor': 0, 'bus': 0, 'truk': 0}
    img_str = None
    
    try:
        cap = cap_from_youtube(video_url, '360p')
        if not cap.isOpened(): return counts, None

        ret, frame = cap.read()
        if ret:
            results = model(frame, classes=VEHICLE_CLASSES, verbose=False)
            
            # Gambar Kotak (Plotting) - Ini yang membuat kotak merah/warna-warni
            annotated_frame = results[0].plot()
            
            # Hitung Jumlah
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    if cls == 2: counts['mobil'] += 1
                    elif cls == 3: counts['motor'] += 1
                    elif cls == 5: counts['bus'] += 1
                    elif cls == 7: counts['truk'] += 1
            
            # Encode ke Base64 agar bisa dikirim ke HTML img tag
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            img_str = base64.b64encode(buffer).decode('utf-8')
            
        cap.release()
        return counts, img_str

    except Exception as e:
        print(f"Error Annotasi: {e}")
        return counts, None

# =========================================================================
# ===== SHARED LOGIC =====
# =========================================================================

def fetch_cctv_list():
    # SAYA PERBAIKI BAGIAN INI AGAR TIDAK ERROR (Link YouTube diisi)
    return [
        { 
            "id": 1, "name": "CCTV Pontianak (Simpang Garuda)", "status": "Aktif", 
            "lat": -0.0245, "lon": 109.3406,
            "stream_url": "https://www.youtube.com/embed/1s9cRcqZf58", 
            "youtube_link": "https://www.youtube.com/watch?v=1s9cRcqZf58" 
        },
        { 
            "id": 2, "name": "CCTV Pontianak (Tugu Khatulistiwa)", "status": "Aktif",
            "lat": 0.0000, "lon": 109.3300,
            "stream_url": "https://www.youtube.com/embed/oqSqC-gOALo", 
            "youtube_link": "https://www.youtube.com/watch?v=oqSqC-gOALo" 
        },
        { 
            "id": 3, "name": "CCTV Demak (Alun-Alun)", "status": "Aktif",
            "lat": -6.8906, "lon": 110.6385,
            "stream_url": "https://www.youtube.com/embed/mHk5UKckU7M", 
            "youtube_link": "https://www.youtube.com/watch?v=mHk5UKckU7M" 
        },
        { 
            "id": 4, "name": "CCTV Demak (Pasar Bintoro)", "status": "Aktif",
            "lat": -6.8850, "lon": 110.6400,
            "stream_url": "https://www.youtube.com/embed/7c4CsGkmBu8", 
            "youtube_link": "https://www.youtube.com/watch?v=7c4CsGkmBu8" 
        },
        { 
            "id": 5, "name": "CCTV Demak (Pertigaan Trengguli)", "status": "Aktif",
            "lat": -6.8700, "lon": 110.6500,
            "stream_url": "https://www.youtube.com/embed/5nw3G2jtWaU", 
            "youtube_link": "https://www.youtube.com/watch?v=5nw3G2jtWaU" 
        },
    ]

def logic_get_summary(cctv_id):
    # Default Kosong
    if not cctv_id:
        return { "kendaraan_hari_ini": "-", "kepadatan_tertinggi": "-", "rata_rata_kecepatan": "-", "kamera_aktif": "-" }

    try:
        cctv_id = int(cctv_id)
        cctv_data = next((item for item in fetch_cctv_list() if item["id"] == cctv_id), None)
        
        if cctv_data:
            # === GUNAKAN DATA ASLI DARI YOLO (Tanpa Gambar) ===
            real_counts = get_real_vehicle_count(cctv_data['youtube_link'])
            
            total_kendaraan = sum(real_counts.values())
            
            # Hitung Kepadatan (Asumsi 1 frame penuh = 40 kendaraan)
            kepadatan_val = min(100, int((total_kendaraan / 40) * 100))
            
            # Estimasi Kecepatan (Makin padat = makin pelan)
            if total_kendaraan == 0:
                kecepatan = "Lancar"
            else:
                kecepatan_val = max(5, 80 - (kepadatan_val * 0.7))
                kecepatan = f"{int(kecepatan_val)} km/j"

            return {
                "kendaraan_hari_ini": str(total_kendaraan), 
                "kepadatan_tertinggi": f"{kepadatan_val}%", 
                "rata_rata_kecepatan": kecepatan, 
                "kamera_aktif": "5"
            }
    except Exception as e:
        print(f"Logic Error: {e}")
    
    return { "kendaraan_hari_ini": "0", "kepadatan_tertinggi": "0%", "rata_rata_kecepatan": "-", "kamera_aktif": "5" }

def logic_get_vehicle(cctv_id, period):
    labels = ['Mobil','Motor','Bus','Truk']
    if not cctv_id:
        return {"labels": labels, "data": [0, 0, 0, 0]}

    try:
        cctv_id = int(cctv_id)
        cctv_data = next((item for item in fetch_cctv_list() if item["id"] == cctv_id), None)
        
        if cctv_data:
            # === GUNAKAN DATA ASLI DARI YOLO ===
            # (Untuk Pie Chart Distribusi Kendaraan)
            real_counts = get_real_vehicle_count(cctv_data['youtube_link'])
            return {
                "labels": labels, 
                "data": [real_counts['mobil'], real_counts['motor'], real_counts['bus'], real_counts['truk']]
            }
    except:
        pass

    return {"labels": labels, "data": [0, 0, 0, 0]}

def logic_get_traffic(cctv_id, period):
    # Untuk Tren Grafik, kita masih simulasi karena belum ada DB history
    if period == 'mingguan': labels = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    elif period == 'bulanan': labels = ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4']
    else: labels = ['06:00','08:00','10:00','12:00','14:00','16:00','18:00']

    if not cctv_id: return {"labels": labels, "kepadatan": [0] * len(labels)}

    data_points = len(labels)
    # Simulasi history (karena AI hanya real-time saat ini)
    kepadatan = [random.randint(20, 80) for _ in range(data_points)]

    return {"labels": labels, "kepadatan": kepadatan}

# =========================================================================
# ===== ROUTES & API =====
# =========================================================================

# --- API UNTUK DETEKSI GAMBAR & KOTAK MERAH (DIPANGGIL TOMBOL DETEKSI) ---
@app.route('/api/analyze_cctv', methods=['GET'])
def api_analyze_cctv():
    cctv_id = request.args.get('cctv_id')
    if not cctv_id: return jsonify({"error": "No ID"}), 400
    
    try:
        cctv_id = int(cctv_id)
        cctv_data = next((item for item in fetch_cctv_list() if item["id"] == cctv_id), None)
        
        if cctv_data:
            # Panggil fungsi yang mengembalikan GAMBAR dengan KOTAK
            counts, img_base64 = get_annotated_frame(cctv_data['youtube_link'])
            
            total = sum(counts.values())
            
            return jsonify({
                "counts": counts,
                "total": total,
                "image": img_base64  # Ini string base64 gambar berkotak merah
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    return jsonify({"error": "Not Found"}), 404

# --- API Dashboard (Data Angka) ---
@app.route('/api/admin/dashboard_summary', methods=['GET'])
@api_login_required
def api_admin_dashboard_summary():
    return jsonify(logic_get_summary(request.args.get('cctv_id')))

@app.route('/api/public/dashboard_summary', methods=['GET'])
def api_public_dashboard_summary():
    return jsonify(logic_get_summary(request.args.get('cctv_id')))

@app.route('/api/admin/traffic_data', methods=['GET'])
@api_login_required
def api_admin_traffic_data():
    return jsonify(logic_get_traffic(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/public/traffic_data', methods=['GET'])
def api_public_traffic_data():
    return jsonify(logic_get_traffic(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/admin/vehicle_distribution', methods=['GET'])
@api_login_required
def api_admin_vehicle_distribution():
    return jsonify(logic_get_vehicle(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/public/vehicle_distribution', methods=['GET'])
def api_public_vehicle_distribution():
    return jsonify(logic_get_vehicle(request.args.get('cctv_id'), request.args.get('period')))

@app.route('/api/cctv_locations', methods=['GET'])
def get_cctv_locations():
    return jsonify(fetch_cctv_list()), 200

# API Statistik Halaman User
@app.route('/api/public/analytics_data', methods=['GET'])
def api_public_analytics_data():
    period = request.args.get('period', 'harian')
    cctv_id = request.args.get('cctv_id')
    
    if period == 'mingguan':
        labels = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
    elif period == 'bulanan':
        labels = ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4']
    else: 
        labels = ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00']

    data_len = len(labels)
    
    if not cctv_id:
        return jsonify({"labels": labels, "traffic": [0] * data_len})

    # Simulasi history (karena AI hanya real-time saat ini)
    traffic = [random.randint(20, 90) for _ in range(data_len)]

    return jsonify({
        "labels": labels,
        "traffic": traffic
    })

# --- Standard Routes ---
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

@app.route('/artikel/tambah', methods=['GET', 'POST'])
@login_required
def tambah_artikel():
    if request.method == 'POST':
        judul = request.form['judul']
        isi = request.form['isi']
        tanggal_str = request.form['tanggal']
        file = request.files.get('gambar')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cursor = get_db_cursor()
        cursor.execute("INSERT INTO artikel (judul, isi, gambar, published, tanggal) VALUES (%s, %s, %s, %s, %s)", (judul, isi, filename, 0, tanggal_str))
        db.commit()
        cursor.close()
        flash("Artikel berhasil ditambahkan!", "success")
        return redirect(url_for('kelola_artikel'))
    return render_template('crud_artikel.html', mode='tambah', artikel=None)

@app.route('/artikel/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_artikel(id):
    next_page = request.args.get('next', url_for('kelola_artikel'))
    cursor = get_db_cursor()
    if request.method == 'POST':
        judul = request.form['judul']
        isi = request.form['isi']
        tanggal_str = request.form['tanggal']
        file = request.files.get('gambar')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute("UPDATE artikel SET judul=%s, isi=%s, gambar=%s, tanggal=%s WHERE id=%s", (judul, isi, filename, tanggal_str, id))
        else:
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
    cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE id=%s AND published=1", (id,))
    artikel = cursor.fetchone()
    cursor.close()
    if artikel:
        return render_template('artikel_detail.html', artikel=artikel)
    else:
        flash("Artikel tidak ditemukan.", "danger")
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

if __name__ == '__main__':
    app.run(debug=True)