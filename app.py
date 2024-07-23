from flask import Flask, request, jsonify, send_file
import subprocess
import os
import threading
import shutil
import tempfile

app = Flask(__name__)

@app.route('/run-command', methods=['POST'])
def run_command():
    data = request.json
    
    description = data.get('description')
    name = data.get('name')
    
    if not description or not name:
        return jsonify({'error': 'Missing description or name parameter'}), 400

    # Set environment variables
    # Read the API key from the environment variable
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        return jsonify({'error': 'API key not found in environment variables'}), 500

    os.environ['OPENAI_API_KEY'] = openai_api_key
    os.environ['PYTHONIOENCODING'] = "utf-8"

    # Construct the command as a single line
    command = f'python run.py --task "{description}" --name "{name}"'

    def execute_command():
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=100)
            
            # Log the output and errors
            output_log = result.stdout
            error_log = result.stderr

            # Check for errors
            if result.returncode != 0:
                print(f'Error: {error_log}')
            else:
                print(f'Output: {output_log}')
        except subprocess.TimeoutExpired:
            print('The command timed out.')
        except Exception as e:
            print(f'Error: {str(e)}')

    # Run the command in a separate thread
    command_thread = threading.Thread(target=execute_command)
    command_thread.start()

    return jsonify({'message': 'Command sent successfully'}), 200

@app.route('/get-folder', methods=['GET'])
def get_folder():
    name = request.args.get('name')
    organization = request.args.get('organization')

    if not name or not organization:
        return jsonify({'error': 'Missing name or organization parameter'}), 400

    base_directory = 'warehouse'

    try:
        # Iterate through folders in the base directory
        for folder_name in os.listdir(base_directory):
            if folder_name.startswith(f'{name}_{organization}_') and os.path.isdir(os.path.join(base_directory, folder_name)):
                folder_path = os.path.join(base_directory, folder_name)
                # Replace backslashes with forward slashes for universal compatibility
                folder_path = folder_path.replace('\\', '/')
                
                # Create a temporary ZIP file
                temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
                shutil.make_archive(temp_zip.name[:-4], 'zip', folder_path)
                
                # Return the ZIP file
                return send_file(temp_zip.name, as_attachment=True, download_name=f'{name}_{organization}.zip')

        return jsonify({'error': 'Folder not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
