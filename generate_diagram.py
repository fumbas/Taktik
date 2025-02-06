import os
import platform
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

# Spielfeld-Größe in Metern
FIELD_WIDTH_M = 37
FIELD_HEIGHT_M = 100

# Spieler & Scheibe in Pixeln
PLAYER_RADIUS = 15
DISC_RADIUS = 10

# Skalierungsfaktor für Draw.io (1m = 10px)
SCALE = 10

# Templates
TEMPLATES = {
    "player": "templates/player_template.xml",
    "disc": "templates/disc.xml",
    "marker": "templates/marker_template.xml",
    "pitch": "templates/pitch.xml",
    "cone": "templates/cone_template.xml",
    "arrow": "templates/arrow_template.xml"
}


def load_yaml(file_path):
    """ Lädt die Formation aus einer YAML-Datei. """
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def add_element(root, element_template, data):
    """ Fügt ein Element in die XML-Struktur ein. """
    element = element_template.format(**data)
    root.append(ET.fromstring(element))


def scale_position(x, y):
    """ Skaliert eine Position vom Meter- in den Pixelbereich. """
    return x * SCALE, (FIELD_HEIGHT_M - y) * SCALE


def calculate_player_positions(x, y):
    """ Berechnet die obere linke Ecke eines Spielers basierend auf der Mittelposition. """
    x_scaled, y_scaled = scale_position(x, y)
    return x_scaled - PLAYER_RADIUS, y_scaled - PLAYER_RADIUS


def calculate_disc_positions(x, y):
    """ Berechnet die obere linke Ecke der Scheibe basierend auf der Mittelposition. """
    x_scaled, y_scaled = scale_position(x, y)
    return x_scaled - DISC_RADIUS, y_scaled - DISC_RADIUS


def calculate_marker_positions(x, y, angle_deg, length=30, radius=20):
    """ Berechnet die Start- und Endpunkte eines Markers mit fester Länge (30px), gedreht um den Mittelpunkt. """
    angle_rad = math.radians(angle_deg - 90)

    tangent_angle_rad = math.radians(angle_deg)
    x_m = x + radius * math.cos(angle_rad)
    y_m = y + radius * math.sin(angle_rad)

    half_length = length / 2
    x1 = x_m - half_length * math.cos(tangent_angle_rad)
    y1 = y_m - half_length * math.sin(tangent_angle_rad)
    x2 = x_m + half_length * math.cos(tangent_angle_rad)
    y2 = y_m + half_length * math.sin(tangent_angle_rad)

    return x1, y1, x2, y2


def generate_diagram(yaml_file):
    """ Erzeugt eine .drawio-Datei mit Spielern, Scheibe, Cones und Markern aus einer YAML Konfiguration. """
    
    formation = load_yaml(yaml_file)
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

    # Spieler hinzufügen
    for idx, player in enumerate(formation["players"], start=10):
        x, y = calculate_player_positions(player["x"], player["y"])
        color = team_colors.get(player["team"], "#000000")

        player_data = {"id": idx, "name": player["name"], "x": str(x), "y": str(y), "color": color}
        add_element(root, templates["player"], player_data)

        # Laufwege
        previous_x, previous_y = x, y

        for path_idx, path_point in enumerate(player.get("path", []), start=1):
            if "x" in path_point and "y" in path_point:
                path_x, path_y = calculate_player_positions(path_point["x"], path_point["y"])
            elif "dx" in path_point and "dy" in path_point:
                path_x, path_y = previous_x + path_point["dx"] * SCALE, previous_y - path_point["dy"] * SCALE
            else:
                raise ValueError(f"Path-Eintrag {path_point} ist ungültig!")

            faded_color = color + "7F"
            player_data_faded = {
                "id": f"{idx}_{path_idx}",
                "name": player["name"],
                "x": str(path_x),
                "y": str(path_y), 
                "color": faded_color
            }
            add_element(root, templates["player"], player_data_faded)

            # Pfeil
            arrow_data = {
                "id": f"arrow_{idx}_{path_idx}",
                "x1": str(previous_x + PLAYER_RADIUS),
                "y1": str(previous_y + PLAYER_RADIUS),
                "x2": str(path_x + PLAYER_RADIUS),
                "y2": str(path_y + PLAYER_RADIUS)
            }
            add_element(root, templates["arrow"], arrow_data)

            previous_x, previous_y = path_x, path_y

    # Scheibe hinzufügen + Passwege
    x, y = calculate_disc_positions(formation["disc"]["x"], formation["disc"]["y"])
    color = team_colors["disc"]
    disc_data = {
        "id": "99",
        "x": str(x),
        "y": str(y),
        "color": color
    }
    add_element(root, templates["disc"], disc_data)

    previous_x, previous_y = x, y

    for idx, path_point in enumerate(formation["disc"].get("path", []), start=1):
        if "x" in path_point and "y" in path_point:
            path_x, path_y = calculate_disc_positions(path_point["x"], path_point["y"])
        elif "dx" in path_point and "dy" in path_point:
            path_x, path_y = previous_x + path_point["dx"] * SCALE, previous_y - path_point["dy"] * SCALE
        else:
            raise ValueError(f"Path-Eintrag {path_point} ist ungültig!")

        faded_color = color + "7F"
        disc_data_faded = {
            "id": f"disc_{idx}",
            "x": str(path_x),
            "y": str(path_y),
            "color": faded_color
        }
        add_element(root, templates["disc"], disc_data_faded)

        # Pfeil
        arrow_data = {
            "id": f"disc_arrow_{idx}",
            "x1": str(previous_x + DISC_RADIUS),
            "y1": str(previous_y + DISC_RADIUS),
            "x2": str(path_x + DISC_RADIUS), "y2": str(path_y + DISC_RADIUS)
        }
        add_element(root, templates["arrow"], arrow_data)

        previous_x, previous_y = path_x, path_y

    # Marker hinzufügen
    for idx, marker in enumerate(formation.get("markers", []), start=100):
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

    # Cones hinzufügen
    for idx, cone in enumerate(formation.get("cones", []), start=200):
        x, y = scale_position(cone["x"], cone["y"])
        cone_data = {"id": idx, "x": str(x), "y": str(y), "color": team_colors["cone"]}
        add_element(root, templates["cone"], cone_data)

    # Export-Verzeichnis erstellen
    output_dir = os.path.join(os.getcwd(), export_name)
    os.makedirs(output_dir, exist_ok=True)

    # Speichern & Export
    base_output_file = os.path.join(output_dir, export_name)
    output_file = os.path.join(output_dir, f"{export_name}.drawio")
    counter = 1
    while os.path.exists(output_file):
        output_file = f"{base_output_file}_{counter}.drawio"
        counter += 1

    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"Drawio wurde erstellt: {output_file}")

    # Export & Bildbearbeitung
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
    try:
        subprocess.run(["drawio", "-x", "-f", export_type, "-o", output_file, "--border", str(border), input_file], check=True)
        print(f"Diagramm erfolgreich exportiert als {output_file}")
    except FileNotFoundError:
        print("Fehler: Draw.io CLI nicht gefunden!")
    except subprocess.CalledProcessError:
        print("Fehler beim Export mit Draw.io CLI.")


def extract_mxfile_from_drawio(drawio_file):
    """ Extrahiert das `<mxfile>`-Element aus einer `.drawio`-Datei. """
    tree = ET.parse(drawio_file)
    root = tree.getroot()

    mxfile_content = ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")
    
    return mxfile_content

def generate_diagram_link(drawio_file):
    """
    Erstellt eine Draw.io-URL mit komprimiertem und base64-kodiertem XML.
    
    :param drawio_file: Der Pfad zur .drawio-Datei
    :return: Eine vollständige Viewer-URL für Draw.io
    """
    xml_content = extract_mxfile_from_drawio(drawio_file)
    if not xml_content:
        return None

    xml_content = xml_content.replace("\n", "").replace("\r", "").strip()

    compressed_data = zlib.compress(xml_content.encode("utf-8"))[2:-4]  # Entfernt den Header (2 Byte) & Footer (4 Byte)

    xml_encoded = base64.b64encode(compressed_data).decode("utf-8")

    xml_url_encoded = urllib.parse.quote(xml_encoded, safe="")

    drawio_url = f"https://app.diagrams.net/?title={urllib.parse.quote(drawio_file)}#R{xml_url_encoded}"

    return drawio_url

def open_diagram_in_browser(drawio_file):
    """
    Öffnet das generierte Diagramm direkt im Browser.
    
    :param drawio_file: Der Pfad zur .drawio-Datei
    """
    url = generate_diagram_link(drawio_file)
    if url:
        print(f"Öffne Diagramm im Browser: {url}")
        webbrowser.open(url)


def process_image(image_path, scale_factor=1.0, orientation="portrait"):
    """ Skaliert und dreht das Bild nach dem Export. """
    try:
        img = Image.open(image_path)

        if orientation.lower() == "landscape":
            img = img.rotate(270, expand=True)

        if scale_factor != 1.0:
            new_width, new_height = int(img.width * scale_factor), int(img.height * scale_factor)
            img = img.resize((new_width, new_height), Image.ANTIALIAS)

        img.save(image_path)
        print(f"Bildbearbeitung abgeschlossen: {image_path} ({img.width}x{img.height}px)")
    
    except Exception as e:
        print(f"Fehler bei der Bildbearbeitung: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Fehler: Bitte eine YAML-Datei angeben!")
        sys.exit(1)

    yaml_file = sys.argv[1]
    generate_diagram(yaml_file)
