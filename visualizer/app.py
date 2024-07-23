import logging
import requests
import os
import subprocess
import threading
import shutil
import tempfile
from flask import Flask, send_from_directory, request, jsonify, send_file

app = Flask(__name__, static_folder='static')
app.logger.setLevel(logging.ERROR)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
messages = []
port = [8000]

def send_msg(role, text):
    try:
        data = {"role": role, "text": text}
        response = requests.post(f"http://127.0.0.1:{port[-1]}/send_message", json=data)
    except:
        logging.info("flask app.py did not start for online log")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chain_visualizer")
def chain_visualizer():
    return send_from_directory("static", "chain_visualizer.html")


@app.route("/replay")
def replay():
    return send_from_directory("static", "replay.html")


@app.route("/get_messages")
def get_messages():
    return jsonify(messages)


@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.get_json()
    role = data.get("role")
    text = data.get("text")

    avatarUrl = find_avatar_url(role)

    message = {"role": role, "text": text, "avatarUrl": avatarUrl}
    messages.append(message)
    return jsonify(message)


def find_avatar_url(role):
    role = role.replace(" ", "%20")
    avatar_filename = f"avatars/{role}.png"
    avatar_url = f"/static/{avatar_filename}"
    return avatar_url

@app.route('/run-command', methods=['POST'])
def run_command():
    data = request.json
    description = data.get('description')
    name = data.get('name')

    if not description or not name:
        return jsonify({'error': 'Missing description or name parameter'}), 400

    # Set environment variables
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        return jsonify({'error': 'API key not found in environment variables'}), 500

    os.environ['OPENAI_API_KEY'] = openai_api_key
    os.environ['PYTHONIOENCODING'] = "utf-8"

    # Get the base directory of the project
# Get the directory containing the Flask app
    base_directory = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory of the directory containing run.py
    parent_directory = os.path.dirname(base_directory)

    # Path to the run.py script
    run_script_path = os.path.join(parent_directory, 'run.py')

    # Construct the command as a single line
    command = f'python {run_script_path} --task "{description}" --name "{name}"'

    def execute_command():
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=100, cwd=base_directory)
            output_log = result.stdout
            error_log = result.stderr

            if result.returncode != 0:
                print(f'Error: {error_log}')
            else:
                print(f'Output: {output_log}')
        except subprocess.TimeoutExpired:
            print('The command timed out.')
        except Exception as e:
            print(f'Error: {str(e)}')

    command_thread = threading.Thread(target=execute_command)
    command_thread.start()

    return jsonify({'message': 'Command sent successfully'}), 200
# Endpoint to handle /get-folder
@app.route('/get-folder', methods=['GET'])
def get_folder():
    name = request.args.get('name')
    organization = request.args.get('organization')

    if not name or not organization:
        return jsonify({'error': 'Missing name or organization parameter'}), 400

    base_directory = 'warehouse'

    try:
        for folder_name in os.listdir(base_directory):
            if folder_name.startswith(f'{name}_{organization}_') and os.path.isdir(os.path.join(base_directory, folder_name)):
                folder_path = os.path.join(base_directory, folder_name)
                folder_path = folder_path.replace('\\', '/')
                
                temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
                shutil.make_archive(temp_zip.name[:-4], 'zip', folder_path)
                
                return send_file(temp_zip.name, as_attachment=True, download_name=f'{name}_{organization}.zip')

        return jsonify({'error': 'Folder not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='argparse')
    parser.add_argument('--port', type=int, default=8000, help="port")
    args = parser.parse_args()
    port.append(args.port)
    print(f"Please visit http://127.0.0.1:{port[-1]}/ for the front-end display page. \nIn the event of a port conflict, please modify the port argument (e.g., python3 app.py --port 8012).")
    app.run(host='0.0.0.0', debug=False, port=port[-1])
