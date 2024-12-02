from flask import Flask, render_template, request, send_file
from pytube import YouTube
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    yt = YouTube(url)
    
    if request.form['format'] == 'video':
        stream = yt.streams.get_highest_resolution()
        filename = 'downloaded.mp4'
    elif request.form['format'] == 'audio':
        stream = yt.streams.filter(only_audio=True).first()
        filename = 'downloaded.mp3'

    output_path = os.path.join(os.getcwd(), 'downloads')
    file_path = os.path.join(output_path, filename)
    
    stream.download(output_path=output_path, filename=filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File tidak ditemukan", 404

@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('405.html'), 405

if __name__ == "__main__":
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app.run(debug=True)
