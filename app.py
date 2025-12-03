from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from werkzeug.utils import secure_filename
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "smart_traffic_secret"

# ===== UPLOAD CONFIG =====
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== ROUTE TAMBAHAN AGAR FILE DI TEMPLATES BISA DIAKSES =====
@app.route('/templates/<path:filename>')
def template_static(filename):
    return send_from_directory('templates', filename)

# ===== KONEKSI DATABASE =====
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="smart_traffic"
)
cursor = db.cursor(dictionary=True)

# ===== LOGIN REQUIRED DECORATOR =====
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash("Silahkan login terlebih dahulu!", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ===== ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')

# ===== USER DASHBOARD =====
@app.route('/dashboard')
def dashboard():
    # User umum, tampilkan artikel yang sudah publish
    cursor.execute("SELECT * FROM artikel WHERE published=1 ORDER BY tanggal DESC LIMIT 5")
    data = cursor.fetchall()
    return render_template('dashboard.html', artikel=data)

# ===== LOGIN / LOGOUT =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "admin" and password == "12345":
            session['user'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Username atau password salah!", "danger")
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== ADMIN DASHBOARD =====
@app.route('/admin')
@login_required
def admin_dashboard():
    cursor.execute("SELECT * FROM artikel ORDER BY tanggal DESC")
    data = cursor.fetchall()
    return render_template('admin_dashboard.html', artikel=data)

# ===== TAMBAH ARTIKEL =====
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

        cursor.execute(
            "INSERT INTO artikel (judul, isi, gambar, published) VALUES (%s, %s, %s, %s)", 
            (judul, isi, filename, 0)
        )
        db.commit()
        flash("Artikel berhasil ditambahkan!", "success")
        return redirect(url_for('kelola_artikel'))

    return render_template('crud_artikel.html', mode='tambah', artikel=None)

# ===== KELOLA ARTIKEL =====
@app.route('/kelola_artikel')
@login_required
def kelola_artikel():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    offset = (page - 1) * per_page

    cursor.execute("SELECT COUNT(*) AS total FROM artikel")
    total_articles = cursor.fetchone()['total']
    total_pages = (total_articles + per_page - 1) // per_page

    cursor.execute("SELECT * FROM artikel ORDER BY tanggal DESC LIMIT %s OFFSET %s", (per_page, offset))
    data = cursor.fetchall()
    return render_template('kelola_artikel.html', artikel=data, page=page, total_pages=total_pages)

# ===== READ ARTIKEL (USER) =====
@app.route('/baca_artikel')
def read_artikel():
    cursor.execute("SELECT * FROM artikel WHERE published=1 ORDER BY tanggal DESC")
    data = cursor.fetchall()
    return render_template('read_artikel.html', artikel=data)

# ===== EDIT ARTIKEL =====
@app.route('/artikel/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_artikel(id):
    next_page = request.args.get('next', url_for('kelola_artikel'))
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
        flash("Artikel berhasil diperbarui!", "success")
        return redirect(next_page)

    cursor.execute("SELECT * FROM artikel WHERE id=%s", (id,))
    data = cursor.fetchone()
    return render_template('crud_artikel.html', mode='edit', artikel=data)

# ===== HAPUS ARTIKEL =====
@app.route('/artikel/hapus/<int:id>')
@login_required
def hapus_artikel(id):
    cursor.execute("DELETE FROM artikel WHERE id=%s", (id,))
    db.commit()
    flash("Artikel berhasil dihapus!", "danger")
    return redirect(url_for('kelola_artikel'))

@app.route('/artikel/publish/<int:id>')
@login_required
def publish_artikel(id):
    try:
        cursor.execute("UPDATE artikel SET published = 1 WHERE id = %s", (id,))
        db.commit()
        flash("Artikel berhasil dipublish!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Gagal mempublish artikel: {e}", "danger")
    return redirect(url_for('kelola_artikel'))


@app.route('/artikel/batal_publish/<int:id>')
@login_required
def batal_publish(id):
    try:
        cursor.execute("UPDATE artikel SET published = 0 WHERE id = %s", (id,))
        db.commit()
        flash("Artikel berhasil dibatalkan publikasinya!", "warning")
    except Exception as e:
        db.rollback()
        flash(f"Gagal membatalkan publikasi: {e}", "danger")
    return redirect(url_for('kelola_artikel'))

# ===== ABOUT / LAPORAN / STATIC PAGE =====
@app.route('/about')
def about():
    return render_template('aboutme.html')

@app.route('/static-page')
def static_page():
    return render_template('static.html')

@app.route('/cctv-page')
def cctv_page():
    return render_template('cctv.html')

if __name__ == '__main__':
    app.run(debug=True)
