from flask import Flask, render_template, request, send_file, Response
from pytube import YouTube
import io

app = Flask(__name__)

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
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )

    except Exception as e:
        return f"Terjadi kesalahan: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)
