from flask import Flask, render_template, request, send_file, Response, redirect, url_for
from pytube import YouTube
import io
import os
from pymongo import MongoClient
from bson.binary import Binary
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Koneksi ke MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['youtube_downloader']
files_collection = db['temp_files']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.form['url']
        yt = YouTube(url)
        
        if request.form['format'] == 'video':
            stream = yt.streams.get_highest_resolution()
            filename = f"{yt.title}.mp4"
            mime_type = 'video/mp4'
        else:
            stream = yt.streams.filter(only_audio=True).first()
            filename = f"{yt.title}.mp3"
            mime_type = 'audio/mpeg'

        # Download ke memory buffer
        buffer = io.BytesIO()
        stream.stream_to_buffer(buffer)
        
        # Simpan ke MongoDB
        file_data = {
            'filename': filename,
            'mime_type': mime_type,
            'data': Binary(buffer.getvalue()),
            'created_at': datetime.utcnow()
        }
        
        result = files_collection.insert_one(file_data)
        file_id = str(result.inserted_id)
        
        # Redirect ke endpoint download_file
        return redirect(url_for('download_file', file_id=file_id))

    except Exception as e:
        return f"Terjadi kesalahan: {str(e)}", 500

@app.route('/download_file/<file_id>')
def download_file(file_id):
    try:
        # Ambil file dari MongoDB
        from bson.objectid import ObjectId
        file_data = files_collection.find_one({'_id': ObjectId(file_id)})
        
        if not file_data:
            return "File tidak ditemukan", 404

        # Buat memory buffer dari data
        buffer = io.BytesIO(file_data['data'])
        
        # Hapus file dari MongoDB setelah diambil
        files_collection.delete_one({'_id': ObjectId(file_id)})
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=file_data['filename'],
            mimetype=file_data['mime_type']
        )

    except Exception as e:
        return f"Terjadi kesalahan: {str(e)}", 500

# Fungsi untuk membersihkan file lama (jalankan secara periodik)
def cleanup_old_files():
    try:
        # Hapus file yang lebih tua dari 1 jam
        deadline = datetime.utcnow() - timedelta(hours=1)
        files_collection.delete_many({'created_at': {'$lt': deadline}})
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True)
