import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

# Import blueprints
from blueprints.language_exam.exam import exam_bp
# from blueprints.exam import exam_bp

# Importeer de nieuwe blueprint voor niet-taalvakken
from blueprints.non_language_exam.non_language_exam import non_language_exam_bp

# Load environment variables from .env file
load_dotenv()

# Create Flask app instance
app = Flask(__name__)

# Set secret key from environment variable or use a default (change this in production!)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_default_secret_key_change_me')

# Register blueprints
app.register_blueprint(exam_bp)
# Registreer de nieuwe blueprint voor niet-taalvakken met een prefix
app.register_blueprint(non_language_exam_bp, url_prefix='/nl-exam')

# Add a root route to redirect to the exam selection page
@app.route('/')
def index():
    return redirect(url_for('exam.select_exam_page'))

# Main execution block
if __name__ == '__main__':
    app.run(debug=True) # Run in debug mode for development 