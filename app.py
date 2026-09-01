# General python built-in module imports
import os
import pytz
import random
import logging
import re
import string
import glob
from datetime import datetime, timezone

# Flask(web backend) imports
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# LLM tool imports 
from langchain_ollama import OllamaLLM

# Custom module imports
from prompts import summarizer_prompt
from app_logger import log_transcript
from constants import VALID_IDS

# Main V4 imports
from versions.NAOMI_DCA.v4_orchestrator import call_v4, warmup_v4


app = Flask(__name__)

# Get the absolute path of the directory containing app.py
basedir = os.path.abspath(os.path.dirname(__file__))

# Define the path to your new data/instance folder
db_dir = os.path.join(basedir, 'data', 'instance')

# Ensure the directory actually exists so SQLAlchemy doesn't crash on startup
os.makedirs(db_dir, exist_ok=True)

# Point the database URI to the exact file path
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(db_dir, 'users.db')}"
# ---------------------------

# CORS
CORS(app)

# Initialize our database
db =  SQLAlchemy(app)

# Create a Database Model
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ref = db.Column(db.String(8), nullable=False, unique=True) # external data reference
    date_created = db.Column(db.DateTime, default=datetime.now(timezone.utc))   
    progress = db.Column(db.Integer, default=0)
    
# Function to return a string when we add some new user
    def __repr__(self):
        return 'User_ID %r>' % self.ref
    
# BASIC LOGGING JUST FOR app.py
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/app.log',  # Log file name
    level=logging.INFO,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
)

V4_TRANSCRIPT_DIR = os.environ.get("V4_TRANSCRIPT_DIR", "./data/v4_transcripts")
TEST_TRANSCRIPT_DIR = os.environ.get("TEST_TRANSCRIPT_DIR", "./data/test_transcripts")

current_name = None # Used only to erase name from transcripts
current_user = None
character_pool = string.ascii_letters + string.digits

#################### ---------------- WEBSITE LOGIC ENDPOINTS (NOT LLM RELATED) --------------------------- #########################
@app.get("/_health")
def health():
    return "ok", 200

@app.route('/')
def home():
    app.logger.info("Home page access")
    all_users = Users.query.all()
    # Format the user data
    users_data = [{'id': user.id, 'ref': user.ref, 'date_created': user.date_created, 'progress': user.progress} for user in all_users]
    
    # Return the formatted user data as JSON
    return jsonify(users_data)


@app.route('/getCurrentUser', methods=['GET'])
def get_user_id():
    # Assuming you want to return a static user ID for demonstration purposes
    # In a real application, you would retrieve the user ID from the request or session
    global current_user
    
    print("returning current user... ", current_user)
    
    # Check if the user ID exists in the user data
    if current_user in VALID_IDS:
        return jsonify({'userId': current_user})
    else:
        app.logger.warning(f"/getCurrentUser No user found: {current_user}")
        return jsonify({'error': 'User ID not found'}), 404

# Define your route to fetch user information
@app.route('/getUserInfo', methods=['GET'])
def get_user_info():
    global current_user

    # Check if there is a logged-in user
    if current_user is None:
        app.logger.warning(f"/getUserInfo No user logged in: {current_user}")
        return jsonify({'error': 'No user logged in'}), 400
    
    user = Users.query.filter_by(ref=current_user).first()
    
    if user:
        return jsonify({'userId': user.ref, 'progress': user.progress}), 200
    else:
        app.logger.warning(f"/getUserInfo No user ID found: {current_user}")
        return jsonify({'error': 'User ID not found'}), 404

   
# Endpoint that updtates the current user's progress 
@app.route('/incrementProgress', methods=['POST'])
def increment_progress():
    global current_user
    global user_progress
    
    # Check if there is a logged-in user
    if current_user is None:
        app.logger.warning(f"/incrementProgress No user logged in: {current_user}")
        return jsonify({'error': 'No user logged in'}), 400
    
    # Fetch the user from the database
    user = Users.query.filter_by(ref=current_user).first()

    # Increment the progress of the current user
    if user:
        # Increment the progress
        user.progress += 1
        print("User progress after update:", user.progress)
        # Commit the changes to the database
        db.session.commit()
        return jsonify({'message': 'Progress incremented successfully'}), 200
    else:
        app.logger.warning(f"/incrementProgress No user fetched from database: {user}")
        return jsonify({'error': 'User ID not found'}), 404


@app.route('/login', methods=['POST'])
def login():
    userid = request.json['userid']
    global current_user

    userid = userid.lower()
    # Check if the user exists in the database
    user = Users.query.filter_by(ref=userid).first()

    if user:
        # set the current user
        current_user = userid
        
        # retrieve the current user's progress
        progress = user.progress
        
        print("current_user: ", current_user)
        print("userid: ", userid)
        print("user progress: ", progress)

        app.logger.info(f"/login successful - current_user: {current_user}, userid: {userid}, user progress: {progress}")
        return jsonify({"progress": user.progress}), 200
    else:
        app.logger.warning(f"/login Invalid credentials, userID: {userid}")
        return jsonify({'message': 'Invalid credentials'}), 401

#################### ---------------- LLM HELPER ENDPOINTS   --------------------------- #########################
@app.route('/get_yes_no_answer', methods=['POST'])
def get_yes_no_answer():
    
    # Extracting 'question' which is the user's answer (yes or no)
    user_answer = (request.json.get('question') or '').strip().lower() if request.is_json else ''

     # Define patterns for explicit "no" and "yes" answers.
    no_patterns = r'\b(no|nope|nah|not really|i don\'t think so|not at all)\b'
    yes_patterns = r'\b(yes|yeah|yep|yup|sure|ok|okay|sounds good|absolutely|definitely)\b'

    # Check for explicit "no" first.
    if re.search(no_patterns, user_answer):
        response = "NEGATIVE"
    # Then check for explicit "yes".
    elif re.search(yes_patterns, user_answer):
        response = "POSITIVE"
    # Default to POSITIVE for ambiguous cases to prevent loops.
    else:
        response = "POSITIVE"

    app.logger.info(f"Classified '{user_answer or '[empty]'}' as {response}")
    return jsonify({'response': response})


def _redact_name_from_files(transcript_path: str, summary_path: str):
    """
    Finds and replaces a user's name with their ID in the transcript and summary files.
    This is a redaction step to protect user privacy.
    """
    global current_name, current_user

    # Only run if a name has been captured and is not empty
    if not current_name or not current_name.strip():
        return

    try:
        # --- Redact the main transcript file ---
        with open(transcript_path, 'r+', encoding='utf-8') as f:
            content = f.read()
            # Perform a case-insensitive replacement of the name with the user ID
            redacted_content = re.sub(current_name, current_user, content, flags=re.IGNORECASE)
            f.seek(0) # Go back to the beginning of the file
            f.truncate() # Clear the file content
            f.write(redacted_content) # Write the updated content

        # --- Redact the summary file ---
        with open(summary_path, 'r+', encoding='utf-8') as f:
            content = f.read()
            redacted_content = re.sub(current_name, current_user, content, flags=re.IGNORECASE)
            f.seek(0)
            f.truncate()
            f.write(redacted_content)
        
        app.logger.info(f"Redacted name '{current_name}' in files for user '{current_user}'")

    except Exception as e:
        app.logger.error(f"Failed to redact name for user {current_user}: {e}")

# Fetches a summary of the conversation between current user and the chatbot
@app.route('/get_summary', methods=['GET'])
def get_summary():
    app.logger.debug(f"/get_summary || Started")
    global current_user, current_name
    if not current_user:
        return jsonify({'error': 'No user logged in'}), 400
    print("Getting summary for user: ", current_user)

    # --- CHANGE: Find the transcript file using a search pattern ---
    
    # 1. Determine the correct directory to search
    target_dir = TEST_TRANSCRIPT_DIR if current_user.startswith("TEST") else V4_TRANSCRIPT_DIR

    # 2. Create a search pattern with a wildcard (*) for the date prefix
    search_pattern = os.path.join(target_dir, f"*_{current_user}.txt")
    
    # 3. Use glob to find all matching files
    transcript_files = sorted(glob.glob(search_pattern))
    
    if not transcript_files:
        app.logger.error(f"/get_summary || Transcript not found for user {current_user} in {target_dir}")
        return jsonify({'error': 'Transcript not found'}), 404

    # 4. Use the most recent transcript found
    transcript_file = transcript_files[-1]
    
    try:
        # Read the user's transcript
        with open(transcript_file, 'r', encoding='utf-8') as file:
            transcript = file.read()

        # Generate the summary using the LLM
        prompt = summarizer_prompt.format(transcript=transcript)
        LLM = get_llm()
        response = LLM.invoke(prompt)
        app.logger.debug(f"/get_summary || Generated summary for {current_user}")

        # --- IMPROVEMENT: Save summary in the same directory as the transcript ---
        # Get the base name of the transcript (e.g., Sep25_aB7x1)
        base_name = os.path.splitext(os.path.basename(transcript_file))[0]
        summary_filename = f"{base_name}-summary.txt"
        summary_filepath = os.path.join(target_dir, summary_filename)
        
        utc_now = datetime.now(pytz.utc)
        eastern_time = utc_now.astimezone(pytz.timezone('US/Eastern'))
        
        summary_content = f"Summary of Session (USER: {current_user})\n"
        summary_content += f"Date: {eastern_time.strftime('%B %d, %Y %I:%M %p')}\n\n"
        summary_content += f"{response}"

        with open(summary_filepath, 'w', encoding='utf-8') as summary_file:
            summary_file.write(summary_content)

        app.logger.info(f"/get_summary || Summary saved to {summary_filepath}")

        # --- NEW: Call the redaction function AFTER saving the files ---
        _redact_name_from_files(transcript_file, summary_filepath)

        return jsonify({'summary': response}), 200
    
    except Exception as e:
        app.logger.error(f"Error generating summary for {current_user}: {e}")
        return jsonify({'error': 'Failed to generate summary'}), 500


# New warmup endpoint
@app.route('/warmup', methods=['POST'])
def warmup():
    """
    Receives a silent signal from the frontend and calls the dedicated
    warmup function in the orchestrator.
    """
    try:
        # Call the new, explicit warmup function.
        warmup_v4()
        return jsonify({"status": "warmup_signal_received"}), 200
    except Exception as e:
        app.logger.error(f"Error during warmup: {str(e)}")
        return jsonify({"status": "error_during_warmup", "error": str(e)}), 500


################## ---------------- OTHER NON-ENDPOINT HELPER FUNCTIONS --------------------------- #########################

def get_llm():
    if "llm" not in g:
        print("Loading llama3.1:70B...")
        g.llm = OllamaLLM(model="llama3.1:70b")
    return g.llm

# --- NEW HELPER TO STRIP MI CODES ---
def strip_mi_codes(text: str) -> str:
    """
    Removes all MI code tags (e.g., '[RCHT+]', '[EPE]') from anywhere in a string.
    This ensures the user sees a clean, natural response.
    """
    if not isinstance(text, str):
        return text
    # This regex finds any occurrence of a square bracket, followed by
    # any characters that are not a closing bracket, followed by a
    # closing bracket, and an optional space. It replaces them with an empty string.
    return re.sub(r"\[[^\]]+\]\s*", "", text).strip()


def _capture_and_set_name(history: list):
    """
    Captures the user's name from the initial history payload and sets a global variable.
    """
    global current_name
    try:
        # The name is always at index 5 in the initial history.
        if history[5]['role'] == 'user':
            current_name = history[5]['content']
            print(f"--- Captured user name from initial history: {current_name} ---")
    except (IndexError, KeyError):
        # Safety check in case the initial history format is ever different
        print("[WARN] Could not capture name from initial history.")
        current_name = '[unknown]'


#### ----------------------------- V4 PRODUCTION    --------------------------------------- #######
INITIAL_HISTORY_LENGTH_V4 = 8
session_key = "default"

@app.route('/v4', methods=['POST'])
def get_v4():
    print("-----------------------------------------------------------------\n")

    # Get the logged-in user's ID
    global session_key, current_user, current_name

    if not current_user:
        app.logger.warning("/v4 endpoint called with no active user.")
        return jsonify({"error": "No user is logged in."}), 401

    if not request.is_json:
        return jsonify({"error": "Invalid request, JSON data expected"}), 400

    json_data = request.get_json()
    question = json_data.get('question')
    history = json_data.get('chat_history')
    
    # The user's ID serves as the session key for the v4 logic
    session_key = current_user

    print("app.py/get_v4: history length: ", len(history))

    # Detect if this is the start of the conversation to pass initial history
    if len(history) == INITIAL_HISTORY_LENGTH_V4:
        session_key = ''.join(random.choices(character_pool, k=5))

        _capture_and_set_name(history)

        print(f"New V4 session started for user: {current_user}, session_key: {session_key}, name: {current_name}")
        app.logger.info(f"New V4 session started for user: {session_key}")
       
        # Do not include the last user message in the initial history
        initial_history = history[:-1]
        response_data = call_v4(question, session_key, initial_history=initial_history)
    else:
        response_data = call_v4(question, session_key)

    # Strip MI codes from the response before sending to the user
    ai_response_with_codes = response_data["response"]
    clean_ai_response = strip_mi_codes(ai_response_with_codes)

    # Log the conversation to the user's transcript file
    try:
        log_transcript(current_user, "USER", question)
        # Log the clean response that the user actually sees
        log_transcript(current_user, "AI", clean_ai_response)
    except Exception as e:
        app.logger.error(f"Transcript logging failed for user {current_user}: {e}")

    return jsonify({
        'response': clean_ai_response,
        'character_count': len(clean_ai_response)
    })


#### ----------------------------- V4 TEST ------------------------------------------------- #######
session_key4 = "default4"
@app.route('/test_v4', methods=['POST'])
def get_test_v4():
    print("-----------------------------------------------\n")
    global session_key4
    if not request.is_json:
        return jsonify({"error": "Invalid request, JSON data expected"}), 400

    json_data = request.get_json()
    question = json_data.get('question')
    history = json_data.get('chat_history')

    #print("app.py/test_v4: history length: ", len(history))

    # Detect new session
    if len(history) == INITIAL_HISTORY_LENGTH_V4:
        session_key4 = ''.join(random.choices(character_pool, k=5))
        print(f"[TEST] NEW V4 SESSION: {session_key4} key generated ")

        # do not include the last user message in the initial history
        initial_history = history[:-1]
        response_data = call_v4(question, session_key4, initial_history=initial_history)
    else:
        response_data = call_v4(question, session_key4)

    ai_response = response_data["response"]
    clean_ai_response = strip_mi_codes(ai_response)

    test_log_id = f"TEST-{session_key4}"
    try:
        log_transcript(test_log_id, "USER", question)
        # Log what the user actually sees to keep logs consistent with UI:
        log_transcript(test_log_id, "AI", ai_response)
    except Exception as e:
        print(f"[WARN] transcript logging failed: {e}")

    return jsonify({
        'response': clean_ai_response, # Return the clean version
        'character_count': len(clean_ai_response)
    })


if __name__ == "__main__":
    print("Starting backend...")

    # Create a Flask application context
    with app.app_context():
        # Create the database tables if they don't exist
        if not os.path.exists('data/instance/users.db'):
            db.create_all()
            print("Database created.")
        
        # Create records in the database for each VALID_ID
        for user_id in VALID_IDS:
            # Check if the user already exists in the database
            existing_user = Users.query.filter_by(ref=user_id).first()
            if not existing_user:
                # If the user doesn't exist, add it to the database
                user = Users(ref=user_id)
                db.session.add(user)
        db.session.commit()

    print("✅ Backend initialized. Launching Flask server...")
    app.logger.info("✅ Backend initialized. Launching Flask server...")

    # Run locally only, no TLS, no reloader
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False,
        threaded=True,
    )