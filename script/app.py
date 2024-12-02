from flask import Flask, render_template, request, send_file, Response, redirect, url_for
from pytube import YouTube
import io
import os
from pymongo import MongoClient
from bson.binary import Binary
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback
import sys

load_dotenv()

app = Flask(__name__)

# Tambahkan error handling untuk koneksi MongoDB
try:
    client = MongoClient(os.getenv('MONGODB_URI'))
    # Test koneksi
    client.server_info()
    db = client['youtube_downloader']
    files_collection = db['temp_files']
    print("MongoDB connection successful")
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    traceback.print_exc()

# Tambahkan di bagian atas file, setelah koneksi MongoDB berhasil
def cleanup_old_files():
    try:
        # Hapus file yang lebih tua dari 1 jam
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        result = files_collection.delete_many({'created_at': {'$lt': cutoff_time}})
        print(f"Cleaned up {result.deleted_count} old files")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

# Jalankan pembersihan saat aplikasi dimulai
cleanup_old_files()

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('405.html'), 405

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.form['url']
        if not url.startswith(('https://www.youtube.com/', 'https://youtu.be/')):
            raise ValueError('URL tidak valid. Harap masukkan URL YouTube yang valid.')
        
        print(f"Processing URL: {url}")  # Debug log
        
        yt = YouTube(url)
        print(f"YouTube object created for: {yt.title}")  # Debug log
        
        if request.form['format'] == 'video':
            stream = yt.streams.get_highest_resolution()
            filename = f"video_{datetime.now().timestamp()}.mp4"
            mime_type = 'video/mp4'
        else:
            stream = yt.streams.filter(only_audio=True).first()
            filename = f"audio_{datetime.now().timestamp()}.mp3"
            mime_type = 'audio/mpeg'
        
        print(f"Stream selected: {stream}")  # Debug log
        
        # Download ke memory buffer
        buffer = io.BytesIO()
        stream.stream_to_buffer(buffer)
        buffer_size = buffer.getbuffer().nbytes
        print(f"Buffer size: {buffer_size} bytes")  # Debug log
        
        if buffer_size > 0:
            # Simpan ke MongoDB
            file_data = {
                'filename': filename,
                'mime_type': mime_type,
                'data': Binary(buffer.getvalue()),
                'created_at': datetime.utcnow()
            }
            
            result = files_collection.insert_one(file_data)
            file_id = str(result.inserted_id)
            print(f"File saved to MongoDB with ID: {file_id}")  # Debug log
            
            return redirect(url_for('download_file', file_id=file_id))
        else:
            raise Exception("Buffer is empty")

    except ValueError as e:
        return str(e), 400
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"Error in download route: {str(e)}\n{error_info}")
        return f"Terjadi kesalahan: {str(e)}", 500

@app.route('/download_file/<file_id>')
def download_file(file_id):
    try:
        from bson.objectid import ObjectId
        print(f"Retrieving file with ID: {file_id}")  # Debug log
        
        file_data = files_collection.find_one({'_id': ObjectId(file_id)})
        
        if not file_data:
            print(f"File not found: {file_id}")  # Debug log
            return "File tidak ditemukan", 404

        buffer = io.BytesIO(file_data['data'])
        
        # Hapus file dari MongoDB
        files_collection.delete_one({'_id': ObjectId(file_id)})
        print(f"File deleted from MongoDB: {file_id}")  # Debug log
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=file_data['filename'],
            mimetype=file_data['mime_type']
        )

    except Exception as e:
        error_info = traceback.format_exc()
        print(f"Error in download_file route: {str(e)}\n{error_info}")  # Debug log
        return f"Terjadi kesalahan: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)
