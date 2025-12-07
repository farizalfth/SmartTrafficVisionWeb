# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, jsonify
from werkzeug.utils import secure_filename
import mysql.connector
import os
from functools import wraps
import datetime

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
    return db.cursor(dictionary=dictionary)

# ===== DECORATOR UNTUK OTENTIKASI WEB =====
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash("Silahkan login terlebih dahulu!", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ===== DECORATOR UNTUK OTENTIKASI API =====
# Ini hanya akan digunakan untuk API yang benar-benar memerlukan login admin (misal: CRUD artikel admin)
def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"message": "Unauthorized. Login required."}), 401
        return f(*args, **kwargs)
    return decorated

# ===== ROUTES WEB (Render HTML) =====
@app.route('/')
def index():
    # Mengambil artikel terbaru yang dipublish untuk landing page
    cursor = get_db_cursor()
    cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE published=1 ORDER BY tanggal DESC LIMIT 5")
    latest_articles = cursor.fetchall()
    cursor.close()
    return render_template('index.html', latest_articles=latest_articles)


@app.route('/dashboard')
def dashboard():
    cursor = get_db_cursor()
    # Hanya ambil artikel yang published untuk dashboard publik
    cursor.execute("SELECT id, judul, gambar, tanggal FROM artikel WHERE published=1 ORDER BY tanggal DESC LIMIT 3")
    latest_articles = cursor.fetchall()
    cursor.close()

    # Data ringkasan dan CCTV akan diambil via JavaScript (API non-admin)
    return render_template('dashboard.html', latest_articles=latest_articles)

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
    # Ambil artikel terbaru untuk ditampilkan di admin dashboard
    cursor.execute("SELECT id, judul, gambar, tanggal FROM artikel ORDER BY tanggal DESC LIMIT 3")
    latest_articles = cursor.fetchall()
    cursor.close()
    return render_template('admin_dashboard.html', latest_articles=latest_articles)

# Di app.py
@app.route('/artikel/<int:id>')
def view_artikel_detail(id):
    cursor = get_db_cursor()
    cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE id=%s AND published=1", (id,))
    artikel = cursor.fetchone()
    cursor.close()
    if artikel:
        return render_template('artikel_detail.html', artikel=artikel)
    else:
        flash("Artikel tidak ditemukan atau belum dipublikasikan.", "danger")
        return redirect(url_for('read_artikel'))

@app.route('/artikel/tambah', methods=['GET', 'POST'])
@login_required
def tambah_artikel():
    if request.method == 'POST':
        judul = request.form['judul']
        isi = request.form['isi']

        file = request.files.get('gambar')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        cursor = get_db_cursor()
        cursor.execute(
            "INSERT INTO artikel (judul, isi, gambar, published, tanggal) VALUES (%s, %s, %s, %s, %s)",
            (judul, isi, filename, 0, datetime.datetime.now()) # Tambahkan datetime.datetime.now()
        )
        db.commit()
        cursor.close()
        flash("Artikel berhasil ditambahkan!", "success")
        return redirect(url_for('kelola_artikel'))

    return render_template('crud_artikel.html', mode='tambah', artikel=None)

@app.route('/kelola_artikel')
@login_required
def kelola_artikel():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    offset = (page - 1) * per_page

    cursor = get_db_cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM artikel")
    total_articles = cursor.fetchone()['total']
    total_pages = (total_articles + per_page - 1) // per_page

    cursor.execute("SELECT id, judul, isi, gambar, published, tanggal FROM artikel ORDER BY tanggal DESC LIMIT %s OFFSET %s", (per_page, offset))
    data = cursor.fetchall()
    cursor.close()
    return render_template('kelola_artikel.html', artikel=data, page=page, total_pages=total_pages, per_page=per_page)

@app.route('/read_artikel')
def read_artikel():
    cursor = get_db_cursor()
    # Pastikan hanya artikel yang dipublikasikan (published=1) yang ditampilkan
    cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE published=1 ORDER BY tanggal DESC")
    data = cursor.fetchall()
    cursor.close()
    return render_template('read_artikel.html', artikel=data)

@app.route('/artikel/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_artikel(id):
    next_page = request.args.get('next', url_for('kelola_artikel'))
    cursor = get_db_cursor()
    
    if request.method == 'POST':
        judul = request.form['judul']
        isi = request.form['isi']
        
        file = request.files.get('gambar')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute("UPDATE artikel SET judul=%s, isi=%s, gambar=%s WHERE id=%s", (judul, isi, filename, id))
        else:
            cursor.execute("UPDATE artikel SET judul=%s, isi=%s WHERE id=%s", (judul, isi, id))

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
    except Exception as e:
        db.rollback()
        flash(f"Gagal mempublish artikel: {e}", "danger")
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
    except Exception as e:
        db.rollback()
        flash(f"Gagal membatalkan publikasi: {e}", "danger")
    finally:
        cursor.close()
    return redirect(url_for('kelola_artikel'))

@app.route('/about')
def about():
    return render_template('aboutme.html')

@app.route('/static-page')
def static_page():
    return render_template('static.html')

@app.route('/cctv-page')
def cctv_page():
    return render_template('cctv.html') # Halaman ini sekarang akan menampilkan peta CCTV

# =========================================================================
# ===== API ENDPOINTS FOR MOBILE APP & PUBLIC DASHBOARD (Returns JSON) =====
# =========================================================================

# API Ringkasan Dashboard Publik (TIDAK PERLU LOGIN ADMIN)
@app.route('/api/public/dashboard_summary', methods=['GET'])
def api_public_dashboard_summary():
    # Ini masih mock data, Anda bisa menggantinya dengan data nyata dari database/sensor
    summary = {
        "kendaraan_hari_ini": "2.431",
        "kepadatan_tertinggi": "65%", # Contoh data
        "rata_rata_kecepatan": "43 km/j",
        "kamera_aktif": "12"
    }
    return jsonify(summary), 200

# API Tren Kepadatan Lalu Lintas Publik (TIDAK PERLU LOGIN ADMIN)
@app.route('/api/public/traffic_data', methods=['GET'])
def api_public_traffic_data():
    traffic_data = {
        "labels": ['06:00','08:00','10:00','12:00','14:00','16:00','18:00'],
        "kepadatan": [35,60,75,50,65,80,55]
    }
    return jsonify(traffic_data), 200

# API Distribusi Jenis Kendaraan Publik (TIDAK PERLU LOGIN ADMIN)
@app.route('/api/public/vehicle_distribution', methods=['GET'])
def api_public_vehicle_distribution():
    vehicle_data = {
        "labels": ['Mobil','Motor','Bus','Truk'],
        "data": [55,30,8,7]
    }
    return jsonify(vehicle_data), 200


@app.route('/api/articles', methods=['GET'])
def get_published_articles():
    cursor = get_db_cursor()
    try:
        cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE published=1 ORDER BY tanggal DESC")
        articles = cursor.fetchall()
        for article in articles:
            if article['gambar']:
                article['gambar_url'] = url_for('static', filename='uploads/' + article['gambar'], _external=True)
            else:
                article['gambar_url'] = None
            if article['tanggal']:
                article['tanggal'] = article['tanggal'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                article['tanggal'] = None
        return jsonify(articles), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching articles: {str(e)}"}), 500
    finally:
        cursor.close()

@app.route('/api/articles/<int:article_id>', methods=['GET'])
def get_article_detail(article_id):
    cursor = get_db_cursor()
    try:
        cursor.execute("SELECT id, judul, isi, gambar, tanggal FROM artikel WHERE id=%s AND published=1", (article_id,))
        article = cursor.fetchone()
        if article:
            if article['gambar']:
                article['gambar_url'] = url_for('static', filename='uploads/' + article['gambar'], _external=True)
            else:
                article['gambar_url'] = None
            if article['tanggal']:
                article['tanggal'] = article['tanggal'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                article['tanggal'] = None
            return jsonify(article), 200
        else:
            return jsonify({"message": "Article not found or not published"}), 404
    except Exception as e:
        return jsonify({"message": f"Error fetching article detail: {str(e)}"}), 500
    finally:
        cursor.close()

# API Admin (membutuhkan login admin)
@app.route('/api/admin/dashboard_summary', methods=['GET'])
@api_login_required
def api_admin_dashboard_summary():
    summary = {
        "kendaraan_hari_ini": "2.431",
        "kepadatan_tertinggi": "87%", # Data admin, bisa berbeda
        "rata_rata_kecepatan": "43 km/j",
        "kamera_aktif": "12"
    }
    return jsonify(summary), 200

@app.route('/api/admin/traffic_data', methods=['GET'])
@api_login_required
def api_admin_traffic_data():
    traffic_data = {
        "labels": ['06:00','08:00','10:00','12:00','14:00','16:00','18:00'],
        "kepadatan": [35,60,75,50,65,80,55]
    }
    return jsonify(traffic_data), 200

@app.route('/api/admin/vehicle_distribution', methods=['GET'])
@api_login_required
def api_admin_vehicle_distribution():
    vehicle_data = {
        "labels": ['Mobil','Motor','Bus','Truk'],
        "data": [55,30,8,7]
    }
    return jsonify(vehicle_data), 200

@app.route('/api/analytics/traffic_congestion/<string:period>', methods=['GET'])
def api_analytics_traffic_congestion(period):
    data_set = {
        "harian": {
            "labels": ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00'],
            "traffic": [30, 60, 75, 50, 68, 80, 55]
        },
        "mingguan": {
            "labels": ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'],
            "traffic": [55, 65, 70, 60, 75, 80, 50]
        },
        "bulanan": {
            "labels": ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4'],
            "traffic": [65, 70, 60, 75]
        },
        "tahunan": {
            "labels": ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'],
            "traffic": [60, 62, 65, 68, 72, 70, 75, 73, 68, 70, 74, 78]
        }
    }
    if period in data_set:
        return jsonify(data_set[period]), 200
    else:
        return jsonify({"message": "Invalid period"}), 400

@app.route('/api/analytics/accident_count/<string:period>', methods=['GET'])
def api_analytics_accident_count(period):
    data_set = {
        "harian": {
            "labels": ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00'],
            "accidents": [0, 2, 1, 1, 2, 3, 1]
        },
        "mingguan": {
            "labels": ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'],
            "accidents": [2, 1, 3, 2, 4, 5, 1]
        },
        "bulanan": {
            "labels": ['Minggu 1', 'Minggu 2', 'Minggu 3', 'Minggu 4'],
            "accidents": [8, 6, 9, 7]
        },
        "tahunan": {
            "labels": ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'],
            "accidents": [20, 18, 25, 22, 27, 24, 26, 29, 28, 30, 31, 33]
        }
    }
    if period in data_set:
        return jsonify(data_set[period]), 200
    else:
        return jsonify({"message": "Invalid period"}), 400

# API untuk data lokasi CCTV (publik, TIDAK PERLU LOGIN ADMIN)
@app.route('/api/cctv_locations', methods=['GET'])
def get_cctv_locations():
    # Ini adalah data mock untuk lokasi CCTV di Jawa Tengah
    cctv_locations = [
        { "id": 1, "name": "CCTV Semarang (Simpang Lima)", "lat": -6.9832, "lon": 110.4093, "status": "Aktif", "last_update": "2024-05-15 10:30:00", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4" }, # Contoh URL stream
        { "id": 2, "name": "CCTV Solo (Gladag)", "lat": -7.5684, "lon": 110.8291, "status": "Aktif", "last_update": "2024-05-15 10:32:15", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_2mb.mp4" },
        { "id": 3, "name": "CCTV Yogyakarta (Malioboro)", "lat": -7.7925, "lon": 110.3659, "status": "Aktif", "last_update": "2024-05-15 10:35:00", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_3mb.mp4" },
        { "id": 4, "name": "CCTV Magelang (Alun-alun)", "lat": -7.4727, "lon": 110.2188, "status": "Tidak Aktif", "last_update": "2024-05-15 09:00:00", "stream_url": None },
        { "id": 5, "name": "CCTV Tegal (Perempatan Maya)", "lat": -6.8778, "lon": 109.1418, "status": "Aktif", "last_update": "2024-05-15 10:28:40", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4" },
        { "id": 6, "name": "CCTV Purwokerto (Bundaran)", "lat": -7.4243, "lon": 109.2201, "status": "Aktif", "last_update": "2024-05-15 10:31:00", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_2mb.mp4" },
        { "id": 7, "name": "CCTV Kudus (Simpang Tujuh)", "lat": -6.8048, "lon": 110.8351, "status": "Aktif", "last_update": "2024-05-15 10:34:00", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_3mb.mp4" },
        { "id": 8, "name": "CCTV Pekalongan (Pantai Pasir Kencana)", "lat": -6.8624, "lon": 109.6587, "status": "Aktif", "last_update": "2024-05-15 10:29:10", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4" },
        { "id": 9, "name": "CCTV Salatiga (Bundaran Tamansari)", "lat": -7.3323, "lon": 110.4965, "status": "Aktif", "last_update": "2024-05-15 10:36:20", "stream_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_2mb.mp4" },
        { "id": 10, "name": "CCTV Cilacap (Bundaran)", "lat": -7.6908, "lon": 109.0270, "status": "Tidak Aktif", "last_update": "2024-05-15 08:45:00", "stream_url": None }
    ]
    return jsonify(cctv_locations), 200

if __name__ == '__main__':
    app.run(debug=True)