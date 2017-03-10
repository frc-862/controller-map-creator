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

# Setup the PDF output
pdf = FPDF()

# Setup the font for Pillow
font = ImageFont.truetype('LiberationSans-Regular.ttf', 34)

# Create a hidden main window, used to that file chooser dialogs can be made
root_window = Tk().withdraw()

# Register a default constructor so that yaml objects can be serialized
yaml.add_multi_constructor('', default_ctor, Loader=Loader)

# Load in the RobotBuilder config
data = None
with open('valkyrie.yaml', 'r') as f:
    data = yaml.load(f, Loader=Loader)

# Find the OI section of the RobotBuilder config
oi_section = [x for x in data['Children'] if x['Base'] == 'OI'][0]
controllers = oi_section['Children']  # List of all of the controllers

# For each controller specified in RobotBuilder
for controller in controllers:
    controller_name = controller['Name']  # The name of the controller, ex. "Driver Left"
    bindings = controller['Children']  # All of the button bindings specified for the controller

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

    # Write the name of the controller on the upper-left of the image
    draw.text((0, 0), controller_name, (128, 128, 128), font=font)

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

            # Draw the command name in the area specified by the controller map
            draw.text((btn['x'], btn['y']),
                      btn_name,
                      (0, 0, 0), font=font)

    # Save the finished picture
    img.save('out/' + controller_name + '.jpg')
    pdf.add_page()
    pdf.image('out/' + controller_name + '.jpg', w=200)

# Output pdf
pdf.output('out/out.pdf', 'F')
