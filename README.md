# Taktik Diagram Generator

This repository contains a Python script for generating tactical diagrams in Draw.io format from YAML configuration files. The script can create diagrams with players, discs, cones, and markers, and export them in various formats.
## Usage
### Prerequisites
- Python 3.x
- Required Python packages (listed in requirements.txt)

### Steps to Run

#### 1. Clone the repository:
```sh
git clone https://github.com/fumbas/Taktik.git
cd Taktik
```

#### 2. Install the required Python packages
```sh
pip install -r requirements.txt
```

#### 3. Create a YAML configuration for the formation to be shown. Refer to the options below

##### 4. Run the script with the YAML file as an argument
```sh
python3 generate_diagram.py path/to/your/formation.yaml
```

### YAML Configuration Options
- `export`: Export settings
  - `export_type`: The format to export (e.g., `png`, `pdf`, `svg`, `web`)
    - Use `png`, `pdf`, `svg` if you have drawio installed locally. Otherwise choose `web`.
  - `export_name`: The base name for the export file
  - `orientation`: `landscape` or `portrait`
  - `scale_factor`: value `<1` to make the resulting export smaller

- `field`
  - `type`: `outdoor` or `indoor`

- `colors`: Team colors
  - `offense`: Color for the offense team
  - `defense`: Color for the defense team
  - `disc`: Color for the disc
  - `marker`: Color for the markers
  - `cone`: Color for the cones

- `players`: List of players
  - `name`: Player's name
  - `team`: Team of the player (offense or defense)
  - `x`: X-coordinate in meters
  - `y`: Y-coordinate in meters
  - `path`: List of path points (each with `x`, `y` or `dx`, `dy`)

- `disc`: Disc position and path
  - `x`: X-coordinate in meters
  - `y`: Y-coordinate in meters
  - `path`: List of path points (each with `x`, `y` or `dx`, `dy`)

- `markers`: List of markers
  - `x`: X-coordinate in meters
  - `y`: Y-coordinate in meters
  - `rotation`: Rotation angle in degrees

- `cones`: List of cones
  - `x`: X-coordinate in meters
  - `y`: Y-coordinate in meters

