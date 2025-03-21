from flask import Flask, session, render_template, request, send_from_directory, redirect, url_for, flash
from flask import jsonify
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secret_key_for_session_management'

# Tambahkan di awal file, setelah import
CUSTOM_DIRECTORY_FOLDER = "custom_directories"
app.config['CUSTOM_DIRECTORY_FOLDER'] = CUSTOM_DIRECTORY_FOLDER

# Pastikan folder "custom_directories" ada
if not os.path.exists(app.config['CUSTOM_DIRECTORY_FOLDER']):
    os.makedirs(app.config['CUSTOM_DIRECTORY_FOLDER'])  # Buat folder jika belum ada

# Folder penyimpanan file
UPLOAD_FOLDER = "static"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Format file yang diizinkan
ALLOWED_EXTENSIONS = {
    'documents': {'pdf', 'docx', 'xlsx', 'pptx'},
    'images': {'png', 'jpg', 'jpeg', 'bmp', 'webp'},
    'videos': {'mp4', 'mkv'},
    'audios': {'mp3'},
    'programs': {'rar', 'zip', 'py', 'exe'}
}

# Fungsi untuk cek ekstensi file
def allowed_file(filename, filetype):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS[filetype]

@app.route('/')
def index():
    """Halaman utama aplikasi"""
    # List semua direktori khusus
    directories = next(os.walk(app.config['CUSTOM_DIRECTORY_FOLDER']))[1]
    allowed_categories = ALLOWED_EXTENSIONS.keys()
    return render_template('index.html', directories=directories, allowed_categories=allowed_categories)
    
@app.context_processor
def inject_user():
    return dict(user="Anonymous")  # Untuk testing, ganti sesuai login user jika diperlukan

@app.template_filter('datetimeformat')
def datetimeformat(value):
    """Memformat timestamp menjadi format yang mudah dibaca."""
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Halaman untuk upload file"""
    # List semua direktori khusus
    directories = next(os.walk(app.config['CUSTOM_DIRECTORY_FOLDER']))[1]
    if request.method == 'POST':
        file = request.files.get('file')
        custom_path = request.form.get('custom_path')  # Path kustom yang dipilih
        if file:
            # Identifikasi jenis file
            for filetype, extensions in ALLOWED_EXTENSIONS.items():
                if allowed_file(file.filename, filetype):
                    # Tentukan path penyimpanan
                    if custom_path:
                        save_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], custom_path)
                    else:
                        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filetype)
                    
                    os.makedirs(save_path, exist_ok=True)  # Buat folder jika belum ada
                    file.save(os.path.join(save_path, file.filename))
                    return redirect(url_for('view_files', category=filetype))
        return "Invalid file type or no file uploaded!", 400
    return render_template('upload.html', directories=directories)

@app.route('/upload_folder', methods=['POST'])
def upload_folder():
    """Mengunggah folder beserta file di dalamnya"""
    if 'files[]' not in request.files:
        return jsonify({'status': 'error', 'message': 'No files uploaded'}), 400

    files = request.files.getlist('files[]')
    folder_base_path = app.config['CUSTOM_DIRECTORY_FOLDER']

    for file in files:
        # Dapatkan path relatif dari file
        relative_path = request.form.get(f'{file.name}_path', file.filename)
        save_path = os.path.join(folder_base_path, relative_path)

        # Buat folder jika belum ada
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Simpan file
        file.save(save_path)

    return jsonify({'status': 'success', 'message': 'Folder successfully uploaded'})

@app.route('/create_directory', methods=['GET', 'POST'])
def create_directory():
    """Membuat direktori baru di folder khusus"""
    if request.method == 'POST':
        dir_name = request.form.get('directory_name')
        if dir_name:
            new_dir_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], dir_name)
            os.makedirs(new_dir_path, exist_ok=True)
            return redirect(url_for('index'))  # Kembali ke halaman utama setelah membuat direktori
        return "Directory name not provided!", 400
    return render_template('create_directory.html')

@app.route('/files/<category>')
def view_files(category):
    """Menampilkan daftar file berdasarkan kategori dengan dukungan filter."""
    is_custom = False
    folder_path = None

    # Periksa apakah kategori adalah default atau custom
    if category in ALLOWED_EXTENSIONS.keys():
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
    elif os.path.exists(os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], category)):
        folder_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], category)
        is_custom = True

    if folder_path and os.path.exists(folder_path):
        # Ambil daftar file
        files = os.listdir(folder_path)
        file_details = []

        for file in files:
            file_path = os.path.join(folder_path, file)
            file_details.append({
                'name': file,
                'size': os.path.getsize(file_path),  # Ukuran file dalam byte
                'mtime': os.path.getmtime(file_path)  # Waktu terakhir diubah
            })

        # Ambil parameter filter dari URL
        sort_by = request.args.get('sort_by', 'name')  # Default: 'name'
        reverse = request.args.get('order', 'asc') == 'desc'

        # Urutkan file berdasarkan filter
        if sort_by == 'name':
            file_details.sort(key=lambda x: x['name'].lower(), reverse=reverse)
        elif sort_by == 'size':
            file_details.sort(key=lambda x: x['size'], reverse=reverse)
        elif sort_by == 'mtime':
            file_details.sort(key=lambda x: x['mtime'], reverse=reverse)

        # Kirim data ke template
        return render_template(
            'view_file.html',
            files=file_details,
            category=category,
            is_custom=is_custom,
            sort_by=sort_by,
            order='desc' if reverse else 'asc'
        )

    return "Invalid category!", 404
    
@app.route('/delete/<category>/<filename>', methods=['POST'])
def delete_file(category, filename):
    """Menghapus file yang dipilih"""
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
    file_path = os.path.join(folder_path, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return redirect(url_for('view_files', category=category))
    return "File not found!", 404

@app.route('/rename/<category>/<filename>', methods=['POST'])
def rename_file(category, filename):
    """Mengubah nama file yang dipilih"""
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
    old_file_path = os.path.join(folder_path, filename)
    new_name = request.form.get('new_name')  # Nama baru dari form
    if not new_name:
        return "New name not provided!", 400

    new_file_path = os.path.join(folder_path, new_name)
    if os.path.exists(old_file_path):
        os.rename(old_file_path, new_file_path)
        return redirect(url_for('view_files', category=category))
    return "File not found!", 404

@app.route('/download/<category>/<filename>')
def download_file(category, filename):
    """Mengunduh file"""
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
    return send_from_directory(folder_path, filename, as_attachment=True)

@app.route('/custom_files/<path:directory>/<filename>')
def serve_custom_file(directory, filename):
    """Menyajikan file dari direktori khusus."""
    folder_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], directory)
    file_path = os.path.join(folder_path, filename)

    if os.path.exists(file_path):
        return send_from_directory(folder_path, filename)

    return "File not found!", 404

@app.route('/preview/<category>/<filename>')
def preview_file(category, filename):
    """Menampilkan pratinjau file."""
    # Decode URL untuk menangani spasi (%20)
    from urllib.parse import unquote
    filename = unquote(filename)

    # Tentukan folder berdasarkan kategori
    if category == 'custom':
        folder_path = app.config['CUSTOM_DIRECTORY_FOLDER']
    else:
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], category)

    # Jalur lengkap file
    file_path = os.path.join(folder_path, filename)
    
    # Validasi apakah file ada
    if not os.path.exists(file_path):
        return "File not found!", 404

    # Kirim jalur file ke template untuk pratinjau
    if category == 'documents' or category == 'custom':
        return render_template('preview_document.html', file_path=f"/{file_path}")
    elif category == 'images':
        return render_template('preview_image.html', file_path=f"/{file_path}")
    elif category == 'videos':
        return render_template('preview_video.html', file_path=f"/{file_path}")
    elif category == 'audios':
        return render_template('preview_audio.html', file_path=f"/{file_path}")
    
    return "Preview not supported!", 400

@app.route('/preview/document/<path:directory>/<filename>')
def preview_document(directory, filename):
    """
    Preview file dokumen di website.
    Mendukung preview dari direktori umum dan direktori khusus.
    """
    # Tentukan folder berdasarkan jenis direktori
    if directory == "general":  # Direktori umum
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], 'documents')
    else:  # Direktori khusus
        folder_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], directory)

    file_path = os.path.join(folder_path, filename)

    # Periksa apakah file ada
    if not os.path.exists(file_path):
        return "File not found!", 404

    file_extension = filename.split('.')[-1].lower()

    # Jika file adalah .txt, baca kontennya langsung
    if file_extension == 'txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return render_template('preview_document.html', content=content, file_type='text')

    # Jika file adalah .pdf
    if file_extension == 'pdf':
        return render_template('preview_document.html', file_url=f'/static/documents/{filename}', file_type='pdf')

    # Jika file adalah .docx, .xlsx, atau .pptx, kirim file ke JavaScript untuk diproses
    if file_extension in {'docx', 'xlsx', 'pptx'}:
        file_url = f'/custom_files/{directory}/{filename}' if directory != "general" else f'/static/documents/{filename}'
        return render_template('preview_document.html', file_url=file_url, file_type=file_extension)

    return "Preview not supported!", 400

@app.route('/download/custom/<path:directory>/<filename>')
def download_custom_file(directory, filename):
    """Mengunduh file dari direktori custom."""
    folder_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], directory)
    file_path = os.path.join(folder_path, filename)

    if os.path.exists(file_path):
        return send_from_directory(folder_path, filename, as_attachment=True)
    return "File not found!", 404

@app.route('/delete/custom/<path:directory>/<filename>', methods=['POST'])
def delete_custom_file(directory, filename):
    """Menghapus file dari direktori custom."""
    folder_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], directory)
    file_path = os.path.join(folder_path, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        return redirect(url_for('view_files', category=directory))
    return "File not found!", 404
    
@app.route('/rename/custom/<path:directory>/<filename>', methods=['POST'])
def rename_custom_file(directory, filename):
    """Mengubah nama file di direktori custom."""
    folder_path = os.path.join(app.config['CUSTOM_DIRECTORY_FOLDER'], directory)
    old_file_path = os.path.join(folder_path, filename)
    new_name = request.form.get('new_name')  # Nama baru dari form

    if not new_name:
        return "New name not provided!", 400

    new_file_path = os.path.join(folder_path, new_name)
    if os.path.exists(old_file_path):
        os.rename(old_file_path, new_file_path)
        return redirect(url_for('view_files', category=directory))
    return "File not found!", 404
 
@app.route('/preview/custom/<path:filename>')
def preview_custom_file(filename):
    """Menampilkan pratinjau file dari direktori custom."""
    from urllib.parse import unquote
    filename = unquote(filename)  # Decode nama file untuk mengatasi spasi (%20)

    # Tentukan jalur file di direktori custom
    folder_path = app.config['CUSTOM_DIRECTORY_FOLDER']
    file_path = os.path.join(folder_path, filename)

    # Validasi keberadaan file
    if not os.path.exists(file_path):
        return "File not found!", 404

    # Kirim jalur file ke template untuk pratinjau
    file_url = f"/custom_files/{filename}"  # Endpoint untuk menyajikan file custom
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
        return render_template('preview_image.html', file_path=file_url)
    elif filename.lower().endswith(('.mp4', '.mkv')):
        return render_template('preview_video.html', file_path=file_url)
    elif filename.lower().endswith('.mp3'):
        return render_template('preview_audio.html', file_path=file_url)
    elif filename.lower().endswith(('.pdf', '.docx', '.xlsx', '.pptx')):
        return render_template('preview_document.html', file_path=file_url)
    return "Preview not supported!", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
