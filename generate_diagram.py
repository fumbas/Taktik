import os
import xml.etree.ElementTree as ET
import yaml
import subprocess
import sys
import math
from PIL import Image
import base64
import zlib
import urllib.parse
import webbrowser

# Field size in meters
FIELD_WIDTH_M = 0 # to be configured in load_pitch_dimensions()
FIELD_HEIGHT_M = 0 # to be configured in load_pitch_dimensions()

# Player & disc in pixels
PLAYER_RADIUS = 0 # to be configured in load_pitch_dimensions()
DISC_RADIUS = 0 # to be configured in load_pitch_dimensions()

# Scaling factor for Draw.io (1m = 10px)
SCALE = 10

# Templates
TEMPLATES = {
    "player": "templates/player_template.xml",
    "disc": "templates/disc.xml",
    "marker": "templates/marker_template.xml",
    "pitch": "templates/pitch_indoor.xml",
    "cone": "templates/cone_template.xml",
    "arrow": "templates/arrow_template.xml"
}


def load_yaml(file_path):
    """ Loads the formation from a YAML file. """
    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error loading YAML file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: YAML file '{file_path}' not found!")
        sys.exit(1)


def validate_formation(formation):
    """ Validates the formation data from the YAML file. """
    required_keys = ["export", "field"]
    for key in required_keys:
        if key not in formation:
            print(f"Error: Missing required key '{key}' in formation!")
            sys.exit(1)

    if "type" not in formation["field"]:
        print("Error: Missing 'type' in field settings!")
        sys.exit(1)

    if "export_type" not in formation["export"] or "export_name" not in formation["export"]:
        print("Error: Missing 'export_type' or 'export_name' in export settings!")
        sys.exit(1)

    for player in formation["players"]:
        if "name" not in player or "team" not in player or "x" not in player or "y" not in player:
            print(f"Error: Missing required player attributes in {player}!")
            sys.exit(1)

    if "x" not in formation["disc"] or "y" not in formation["disc"]:
        print("Error: Missing 'x' or 'y' in disc settings!")
        sys.exit(1)


def load_pitch_dimensions():
    """ Lädt die Feldabmessungen aus der pitch.xml Vorlage. """
    global FIELD_WIDTH_M, FIELD_HEIGHT_M, SCALE, PLAYER_RADIUS, DISC_RADIUS
    try:
        tree = ET.parse(TEMPLATES["pitch"])
        root = tree.getroot()
        graph_model = root.find(".//mxGraphModel")
        page_width = int(graph_model.get("pageWidth"))
        page_height = int(graph_model.get("pageHeight"))
        FIELD_WIDTH_M = page_width / SCALE
        FIELD_HEIGHT_M = page_height / SCALE

        # PLAYER_RADIUS = FIELD_HEIGHT_M / 70 * SCALE
        # DISC_RADIUS = FIELD_HEIGHT_M / 100 * SCALE

        print(f"Loaded pitch dimensions: FIELD_WIDTH_M={FIELD_WIDTH_M}, FIELD_HEIGHT_M={FIELD_HEIGHT_M}, PLAYER_RADIUS={PLAYER_RADIUS}, DISC_RADIUS={DISC_RADIUS}")
    except ET.ParseError as e:
        print(f"Error parsing pitch template: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Pitch template '{TEMPLATES['pitch']}' not found!")
        sys.exit(1)


def add_element(root, element_template, data):
    """ Adds an element to the XML structure. """
    element = element_template.format(**data)
    root.append(ET.fromstring(element))


def scale_position(x, y):
    """ Scales a position from meters to pixels. """
    return x * SCALE, (FIELD_HEIGHT_M - y) * SCALE


def calculate_player_positions(x, y):
    """ Calculates the top-left corner of a player based on the center position. """
    x_scaled, y_scaled = scale_position(x, y)
    return x_scaled - PLAYER_RADIUS, y_scaled - PLAYER_RADIUS


def calculate_disc_positions(x, y):
    """ Calculates the top-left corner of the disc based on the center position. """
    x_scaled, y_scaled = scale_position(x, y)
    return x_scaled - DISC_RADIUS, y_scaled - DISC_RADIUS


def calculate_marker_positions(x, y, angle_deg):
    """ Calculates the start and end points of a marker with a fixed length , rotated around the center. """
    angle_rad = math.radians(angle_deg - 90)
    marker_radius = PLAYER_RADIUS * 1.5

    tangent_angle_rad = math.radians(angle_deg)
    x_m = x + marker_radius * math.cos(angle_rad)
    y_m = y + marker_radius * math.sin(angle_rad)

    half_length = PLAYER_RADIUS
    x1 = x_m - half_length * math.cos(tangent_angle_rad)
    y1 = y_m - half_length * math.sin(tangent_angle_rad)
    x2 = x_m + half_length * math.cos(tangent_angle_rad)
    y2 = y_m + half_length * math.sin(tangent_angle_rad)

    return x1, y1, x2, y2


def generate_diagram(yaml_file):
    """ Generates a .drawio file with players, disc, cones, and markers from a YAML configuration. """
    
    formation = load_yaml(yaml_file)
    validate_formation(formation)

    if formation["field"]["type"] == "indoor":
        TEMPLATES["pitch"] = "templates/pitch_indoor.xml"
        PLAYER_RADIUS = 10
        DISC_RADIUS = 7.5
    elif formation["field"]["type"] == "outdoor":
        TEMPLATES["pitch"] = "templates/pitch_outdoor.xml"
        PLAYER_RADIUS = 15
        DISC_RADIUS = 10

    load_pitch_dimensions()

    load_pitch_dimensions()

    export_type = formation["export"]["export_type"]
    export_name = formation["export"]["export_name"]

    team_colors = formation.get("colors", {})
    team_colors.setdefault("offense", "#3498db")
    team_colors.setdefault("defense", "#e74c3c")
    team_colors.setdefault("disc", "#FFD700")
    team_colors.setdefault("marker", "#000000")
    team_colors.setdefault("cone", "#FFA500")

    tree = ET.parse(TEMPLATES["pitch"])
    root = tree.getroot().find(".//root")

    templates = {key: open(TEMPLATES[key]).read() for key in TEMPLATES}

    # Add players
    for idx, player in enumerate(formation["players"], start=10):
        x, y = calculate_player_positions(player["x"], player["y"])
        color = team_colors.get(player["team"], "#000000")

        player_data = {
            "id": idx,
            "name": player["name"],
            "x": str(x),
            "y": str(y),
            "color": color,
            "size": str(2 * PLAYER_RADIUS)
        }
        add_element(root, templates["player"], player_data)

        # Paths
        previous_x, previous_y = x, y

        for path_idx, path_point in enumerate(player.get("path", []), start=1):
            if "x" in path_point and "y" in path_point:
                path_x, path_y = calculate_player_positions(path_point["x"], path_point["y"])
            elif "dx" in path_point and "dy" in path_point:
                path_x, path_y = previous_x + path_point["dx"] * SCALE, previous_y - path_point["dy"] * SCALE
            else:
                print(f"Error: Invalid path entry {path_point} for player {player['name']}!")
                sys.exit(1)

            faded_color = color + "7F"
            player_data_faded = {
                "id": f"{idx}_{path_idx}",
                "name": player["name"],
                "x": str(path_x),
                "y": str(path_y), 
                "color": faded_color,
                "size": str(2 * PLAYER_RADIUS)
            }
            add_element(root, templates["player"], player_data_faded)

            # Arrow
            arrow_data = {
                "id": f"arrow_{idx}_{path_idx}",
                "x1": str(previous_x + PLAYER_RADIUS),
                "y1": str(previous_y + PLAYER_RADIUS),
                "x2": str(path_x + PLAYER_RADIUS),
                "y2": str(path_y + PLAYER_RADIUS)
            }
            add_element(root, templates["arrow"], arrow_data)

            previous_x, previous_y = path_x, path_y

    # Add disc
    x, y = calculate_disc_positions(formation["disc"]["x"], formation["disc"]["y"])
    color = team_colors["disc"]
    disc_data = {
        "id": "99",
        "x": str(x),
        "y": str(y),
        "color": color,
        "size": str(2 * DISC_RADIUS)
    }
    add_element(root, templates["disc"], disc_data)

    previous_x, previous_y = x, y

    # path
    for idx, path_point in enumerate(formation["disc"].get("path", []), start=1):
        if "x" in path_point and "y" in path_point:
            path_x, path_y = calculate_disc_positions(path_point["x"], path_point["y"])
        elif "dx" in path_point and "dy" in path_point:
            path_x, path_y = previous_x + path_point["dx"] * SCALE, previous_y - path_point["dy"] * SCALE
        else:
            print(f"Error: Invalid path entry {path_point} for disc!")
            sys.exit(1)

        faded_color = color + "7F"
        disc_data_faded = {
            "id": f"disc_{idx}",
            "x": str(path_x),
            "y": str(path_y),
            "color": faded_color,
            "size": str(2 * DISC_RADIUS)
        }
        add_element(root, templates["disc"], disc_data_faded)

        # Arrow
        arrow_data = {
            "id": f"disc_arrow_{idx}",
            "x1": str(previous_x + DISC_RADIUS),
            "y1": str(previous_y + DISC_RADIUS),
            "x2": str(path_x + DISC_RADIUS), "y2": str(path_y + DISC_RADIUS)
        }
        add_element(root, templates["arrow"], arrow_data)

        previous_x, previous_y = path_x, path_y

    # Add markers
    for idx, marker in enumerate(formation.get("markers", []), start=100):
        if "x" not in marker or "y" not in marker or "rotation" not in marker:
            print(f"Error: Missing required marker attributes in {marker}!")
            sys.exit(1)
        x, y = scale_position(marker["x"], marker["y"])
        x1, y1, x2, y2 = calculate_marker_positions(x, y, marker["rotation"])

        marker_data = {
            "id": idx,
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
            "color": team_colors["marker"]
        }
        add_element(root, templates["marker"], marker_data)

    # Add cones
    for idx, cone in enumerate(formation.get("cones", []), start=200):
        if "x" not in cone or "y" not in cone:
            print(f"Error: Missing required cone attributes in {cone}!")
            sys.exit(1)
        x, y = scale_position(cone["x"], cone["y"])
        cone_data = {
            "id": idx,
            "x": str(x),
            "y": str(y),
            "color": team_colors["cone"],
            "size": str(PLAYER_RADIUS)
        }
        add_element(root, templates["cone"], cone_data)

    # Create export directory
    output_dir = os.path.join(os.getcwd(), export_name)
    os.makedirs(output_dir, exist_ok=True)

    # Save & export
    base_output_file = os.path.join(output_dir, export_name)
    output_file = os.path.join(output_dir, f"{export_name}.drawio")
    counter = 1
    while os.path.exists(output_file):
        output_file = f"{base_output_file}_{counter}.drawio"
        counter += 1

    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"Drawio created: {output_file}")

    # Export & image processing
    export_file = os.path.join(output_dir, f"{export_name}.{export_type}")
    counter = 1
    while os.path.exists(export_file):
        export_file = f"{base_output_file}_{counter}.{export_type}"
        counter += 1

    if export_type == "web":
        open_diagram_in_browser(output_file)
    else: 
        export_with_drawio(output_file, export_file, export_type)
        process_image(export_file, formation["export"].get("scale_factor", 1.0), formation["export"].get("orientation", "portrait"))


def export_with_drawio(input_file, output_file, export_type, border=50):
    """ Exports the diagram using the Draw.io CLI. """
    try:
        subprocess.run(["drawio", "-x", "-f", export_type, "-o", output_file, "--border", str(border), input_file], check=True)
        print(f"Diagram successfully exported as {output_file}")
    except FileNotFoundError:
        print("Error: Draw.io CLI not found!")
    except subprocess.CalledProcessError:
        print("Error exporting with Draw.io CLI.")


def extract_mxfile_from_drawio(drawio_file):
    """ Extracts the `<mxfile>` element from a `.drawio` file. """
    try:
        tree = ET.parse(drawio_file)
        root = tree.getroot()

        mxfile_content = ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")
        
        return mxfile_content
    except ET.ParseError as e:
        print(f"Error parsing .drawio file: {e}")
        return None


def generate_diagram_link(drawio_file):
    """
    Creates a Draw.io URL with compressed and base64-encoded XML.
    """
    xml_content = extract_mxfile_from_drawio(drawio_file)
    if not xml_content:
        return None

    xml_content = xml_content.replace("\n", "").replace("\r", "").strip()

    compressed_data = zlib.compress(xml_content.encode("utf-8"))[2:-4]  # Removes the header (2 bytes) & footer (4 bytes)

    xml_encoded = base64.b64encode(compressed_data).decode("utf-8")

    xml_url_encoded = urllib.parse.quote(xml_encoded, safe="")

    drawio_url = f"https://app.diagrams.net/?title={urllib.parse.quote(drawio_file)}#R{xml_url_encoded}"

    return drawio_url


def open_diagram_in_browser(drawio_file):
    """ Opens the generated diagram directly in the browser.    """
    url = generate_diagram_link(drawio_file)
    if url:
        print(f"Opening diagram in browser: {url}")
        webbrowser.open(url)


def process_image(image_path, scale_factor=1.0, orientation="portrait"):
    """ Scales and rotates the image after export. """
    try:
        img = Image.open(image_path)

        if orientation.lower() == "landscape":
            img = img.rotate(270, expand=True)

        if scale_factor != 1.0:
            new_width, new_height = int(img.width * scale_factor), int(img.height * scale_factor)
            img = img.resize((new_width, new_height), Image.ANTIALIAS)

        img.save(image_path)
        print(f"Image processing completed: {image_path} ({img.width}x{img.height}px)")
    
    except Exception as e:
        print(f"Error processing image: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please specify a YAML file!")
        sys.exit(1)

    yaml_file = sys.argv[1]
    generate_diagram(yaml_file)
