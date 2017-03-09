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

# For each controller specified in RobotBuilder
for controller in oi_section['Children']:
    controller_name = controller['Name']

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

    # Open the base image for the controller and create a pillow drawing context
    img = Image.open(controller_map['image'])
    draw = ImageDraw.Draw(img)

    # Write the name of the controller on the upper-left of the image
    draw.text((0, 0), controller_name, (128, 128, 128), font=font)

    # For each button binding on the controller
    for x in controller['Children']:
        if x.get('Base', '') == 'Joystick Button':
            # The ID of the button on the controller
            btn_id = x['Properties']['Button']['value']

            # The name of the command to run
            btn_name = x['Properties']['Command']['value']

            print(btn_id, x['Properties']['Joystick']['value'], btn_name)

            # Find the button on the controller map
            matching_btns = [btn for btn in controller_map['buttons'] if str(btn['id']) == btn_id]

            # If the button was not specified in the controller map, give a warning
            if len(matching_btns) == 0:
                print('Warning: No entry in button map', map_file, 'for button', btn_id)
                continue

            btn = matching_btns[0]

            # Draw the command name in the area specified by the controller map
            draw.text((btn['x'], btn['y']),
                      x.get('Name', 'No name specified'),
                      (0, 0, 0), font=font)

    # Save the finished picture
    img.save('out/' + controller_name + '.jpg')
    pdf.add_page()
    pdf.image('out/' + controller_name + '.jpg', w=200)

# Output pdf
pdf.output('out/out.pdf', 'F')

print(controller_map)
print([btn for btn in controller_map['buttons'] if btn['id'] == 0])
