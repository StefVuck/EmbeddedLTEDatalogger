# Run Instructions
- Have Node.JS installed on your system
- `npm install` in project root
- `electron .` in project root
- Select `EXE` when prompted
  
TEMPORARY:
Ideally close the application like any other, however, quickly check through to make sure all instances of "Electron" are closed, this may include process selection

Currently this project uses an Electron wrapper to load a Dash App as a Desktop App, the python option is made to be a debugging utility for live code changes with the .exe being more stable, and like pre-releases.
For production releases, electron-packager will be used to package into a enviroment that doesn't require any prerequisites.

# Development Requirements:

### Python
- `pip install pandas`
- `pip install arduino-iot-client`
- `pip install requests-oauthlib`
- `pip install dash`

### Javascript:
- Node JS installed

# Rebundling Instructions:
For the python bundling into the executable, from the root directory please run:
`pyinstaller --onefile --add-data "dash_app/assets/*;assets/" --icon="dash_app/assets/icon.ico" "dash_app/APIpoller.py"`

This bundles it all into one file, including the required assets, and in theory should include the icon, though this doesnt seem to work.
This should automatically be put into `./dist` which means electron can use it over the python exe you installed

***PLEASE DO NOT REBUNDLE A BROKEN EXE AND THEN COMMIT THIS TO THE REPO***
