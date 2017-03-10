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

from datetime import datetime


"""
Default constructor for parsing yaml objects
Parses them generically
"""
def default_ctor(loader, tag_suffix, node):
    return loader.construct_mapping(node, deep=True)

"""
Load a YAML config from a file

Returns a dict representing the RobotBuilder config
"""
def _load_yaml(path):
    yaml.add_multi_constructor('', default_ctor, Loader=Loader)

    data = None
    with open(path, 'r') as f:
        yaml_elements = yaml.load_all(f, Loader=Loader)
        for x in yaml_elements:
            data = x
    
    return data

"""
Get controllers from a RobotBuilder config
Returns a list of controllers (OI devices)
"""
def _get_controllers(rb_conf):
    # Find the OI section of the RobotBuilder config
    oi_section = [x for x in rb_conf['Children'] if x['Base'] == 'OI'][0]
    
    # List of all of the controllers
    controllers = oi_section['Children']
    return controllers

"""
Get button bindings on a RobotBuilder controller

Returns a list of buttons
"""
def _get_bindings(controller):
    return controller['Children']

class ControllerAnnotation:
    def __init__(self, config_file_path=None, gui=False):
        self.gui = gui

        self.config = None
        if config_file_path is not None:
            self.config = _load_yaml(config_file_path)

        self.config_map_files = self.__read_config_val('mapFiles')
    
    """
    Reads a value from the config.
    Returns None if not defined or if config doesn't exist
    """
    def __read_config_val(self, key):
        if self.config is None:
            return None

        return self.config.get(key, None)

        return data

    """
    Get the path to the controller config

    If returns None, then skip the controller
    """
    def __get_controller_config_path(self, controller_name):
        map_file = None
        # Try to get the map file from the config
        if self.config_map_files is not None:
            map_file = self.config_map_files.get(controller_name, None)

        # If we couldn't get it from the config, ask the user for the map file
        if map_file is None and self.gui:
            # Ask the user to pick a config file for the controller
            map_file = filedialog.askopenfilename(
                initialdir="controllers",
                title="Choose a controller file for " + controller_name,
                filetypes=(("Controller Map", "*.yaml"), ("all files", "*.*")))
        
        return map_file

    """
    Get the controller config for a controller
    Specifies the x/y of the buttons, the font size, the controller image, etc

    If returns None, then skip the controller
    """
    def __get_controller_config(self, controller_name):
        path = self.__get_controller_config_path(controller_name)

        if path is None or len(path) == 0:
            return None
        
        return _load_yaml(path)
    
    """
    Draw a mapping image for a RobotBuilder controller

    Saves to out/controller_name.jpg

    Returns the filename of the output image, or None if the controller doesn't have a config
    """
    def __draw_mapping_img(self, controller):
        controller_name = controller['Name']  # The name of the controller, ex. "Driver Left"

        controller_map = self.__get_controller_config(controller_name)
        if controller_map is None:  # No controller map available, skip
            return None
        
        # Get the buttons from the controller map
        controller_buttons = controller_map['buttons']

        # Open the base image for the controller and create a pillow drawing context
        img = Image.open(controller_map['image'])
        draw = ImageDraw.Draw(img)

        # Setup the font for Pillow
        font_size = controller_map['fontSize']
        font = ImageFont.truetype('LiberationSans-Regular.ttf', font_size)

        # Write the name of the controller on the upper-left of the image
        draw.text((0, 0), controller_name, (128, 128, 128), font=font)

        # Write the date and time under the controller name
        cur_datetime = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
        draw.text((0, font_size), 'As of ' + cur_datetime + ' UTC', (128, 128, 128), font=font)

        # Dictionary of tuple(x, y) to boolean of positions where a command is drawn already
        taken_positions = {}

        for binding in _get_bindings(controller):
            # Skip bindings that aren't to buttons
            if binding.get('Base', '') != 'Joystick Button':
                continue

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
                print('Warning: No entry in button map', self.__get_controller_config_path(controller_name), 'for button', btn_id, '(' + btn_name + ')')
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

        # Save the finished image to a file
        output_path = 'out/' + controller_name + '.jpg'
        img.save(output_path)

        return output_path
    
    """
    Gets the RobotBuilder config path,
    either from the config or via file chooser
    """
    def __get_rb_config_path(self):
        # Determine RobotBuilder config file location from config
        robotbuilder_config_path = self.__read_config_val('robotbuilderConfig')

        # Ask the user to pick the robotbuilder config file if it wasn't in the config
        if robotbuilder_config_path is None and self.gui:
            robotbuilder_config_path = filedialog.askopenfilename(
                    title="Choose a RobotBuilder config",
                    filetypes=(("RobotBuilder Config", "*.yaml"), ("all files", "*.*")))
        
        return robotbuilder_config_path

    """
    Create all of the controller mapping images
    and the final controller mapping pdf
    """
    def create_mapping_files(self):
        # Load the RobotBuilder config
        rb_conf = _load_yaml(self.__get_rb_config_path())

        # Create the PDF
        pdf = FPDF()

        # Draw all of the images and merge to PDF
        for controller in _get_controllers(rb_conf):
            img_path = self.__draw_mapping_img(controller)

            if img_path is None:  # Skipping controller
                continue
            
            # Add image to PDF
            pdf.add_page()
            pdf.image(img_path, w=200)

        pdf.output('out/out.pdf')


# If we're not a library, then execute the annotator
if __name__ == '__main__':
    # Load in the config file if it exists
    config_file_path = None
    if len(sys.argv) > 1:
        config_file_path = sys.argv[1]

    annotation = ControllerAnnotation(config_file_path, True)
    annotation.create_mapping_files()
