import os
from flask import Flask
import annotator
import urllib.request

CONFIG_URL = 'https://raw.githubusercontent.com/frc-862/valkyrie/master/valkyrie.yaml'

app = Flask(__name__, static_folder='out')

@app.route('/update-mapping')
def update_mapping():
    # Download the latest Valkyrie yaml
    urllib.request.urlretrieve(CONFIG_URL, 'valkyrie.yaml')

    # Create the annotated controller images
    annotation = annotator.ControllerAnnotation('config.yaml')
    annotation.create_mapping_files()

    return 'Done'

@app.route('/pdf')
def serve_pdf():
    return app.send_static_file('out.pdf')

# Run the webapp if we're not a library
if __name__ == "__main__":
    app.run(port=os.environ.get('PORT', 5000), host='0.0.0.0')