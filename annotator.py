import sys
import json
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from PIL import Image, ImageFont, ImageDraw

from tkinter import Tk
from tkinter import filedialog

from fpdf import FPDF


"""
Default constructor for parsing yaml objects
Parses them generically
"""
def default_ctor(loader, tag_suffix, node):
    return loader.construct_mapping(node, deep=True)


# Begin program

# Load in the config file if it exists
config = None
if len(sys.argv) > 1:
    config_file_path = sys.argv[1]
    with open(config_file_path, 'r') as f:
        config = yaml.load(f, Loader=Loader)

"""
Reads a value from the config.
Returns None if not defined or if config doesn't exist
"""
def read_config_val(key):
    if config is None:
        return None

    return config.get(key, None)

config_map_files = read_config_val('mapFiles')

# Setup the PDF output
pdf = FPDF()

# Create a hidden main window, used to that file chooser dialogs can be made
root_window = Tk().withdraw()

# Register a default constructor so that yaml objects can be serialized
yaml.add_multi_constructor('', default_ctor, Loader=Loader)

# Determine RobotBuilder config file location
robotbuilder_config_path = read_config_val('robotbuilderConfig')

# Ask the user to pick the robotbuilder config file if it wasn't in the config
if robotbuilder_config_path is None:
    robotbuilder_config_path = filedialog.askopenfilename(
            title="Choose a RobotBuilder config",
            filetypes=(("RobotBuilder Config", "*.yaml"), ("all files", "*.*")))

# Load in the RobotBuilder config
data = None
with open(robotbuilder_config_path, 'r') as f:
    data = yaml.load(f, Loader=Loader)

# Find the OI section of the RobotBuilder config
oi_section = [x for x in data['Children'] if x['Base'] == 'OI'][0]
controllers = oi_section['Children']  # List of all of the controllers

# For each controller specified in RobotBuilder
for controller in controllers:
    controller_name = controller['Name']  # The name of the controller, ex. "Driver Left"
    bindings = controller['Children']  # All of the button bindings specified for the controller

    map_file = None
    # Try to get the map file from the config
    if config_map_files is not None:
        map_file = config_map_files.get(controller_name, None)

    # If we couldn't get it from the config, ask the user for the map file
    if map_file is None:
        # Ask the user to pick a config file for the controller
        map_file = filedialog.askopenfilename(
            initialdir="controllers",
            title="Choose a controller file for " + controller_name,
            filetypes=(("Controller Map", "*.yaml"), ("all files", "*.*")))

    # If the user closed the window or chose cancel, then skip the controller
    if not isinstance(map_file, str) or map_file == '':
        print('No map file specfied for', controller_name, 'SKIPPING')
        continue

    # Load in the controller config file
    controller_map = None
    with open(map_file, 'r') as f:
        controller_map = yaml.load(f, Loader=Loader)

    controller_buttons = controller_map['buttons']

    # Open the base image for the controller and create a pillow drawing context
    img = Image.open(controller_map['image'])
    draw = ImageDraw.Draw(img)

    # Setup the font for Pillow
    font_size = controller_map['fontSize']
    font = ImageFont.truetype('LiberationSans-Regular.ttf', font_size)

    # Write the name of the controller on the upper-left of the image
    draw.text((0, 0), controller_name, (128, 128, 128), font=font)

    # Dictionary of tuple(x, y) to boolean of positions where a command is drawn already
    taken_positions = {}

    # For each button binding on the controller
    for binding in bindings:
        if binding.get('Base', '') == 'Joystick Button':
            # The ID of the button on the controller
            btn_id = binding['Properties']['Button']['value']

            # The name of the command to run
            command_name = binding['Properties']['Command']['value']

            # The name of the button binding
            btn_name = binding.get('Name', 'No name specified')

            # Find the button on the controller map
            matching_btns = [cbtn for cbtn in controller_buttons if str(cbtn['id']) == btn_id]

            # If the button was not specified in the controller map, give a warning
            if len(matching_btns) == 0:
                print('Warning: No entry in button map', map_file, 'for button', btn_id, '(' + btn_name + ')')
                continue

            btn = matching_btns[0]

            pos = (btn['x'], btn['y'])

            while taken_positions.get(pos, False) != False:
                pos = (pos[0], pos[1] + font_size)

            # Draw the command name in the area specified by the controller map
            draw.text(pos,
                      btn_name,
                      (0, 0, 0), font=font)
            
            taken_positions[pos] = True

    # Save the finished picture
    img.save('out/' + controller_name + '.jpg')
    pdf.add_page()
    pdf.image('out/' + controller_name + '.jpg', w=200)

# Output pdf
pdf.output('out/out.pdf', 'F')
