"""Video Language Tutor - Flask Application.

A language learning application that uses Reka Vision API to help users
learn languages through video content.
"""
from flask import Flask
from src.config import Config
from src.routes.main import main_bp
from src.routes.video import video_bp
from src.routes.language import language_bp
from src.routes.chat import chat_bp


app = Flask(__name__)

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(video_bp)
app.register_blueprint(language_bp)
app.register_blueprint(chat_bp)


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)