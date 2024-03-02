const { app, BrowserWindow, screen } = require('electron');
const { spawn } = require('child_process');
const http  = require('http');
const path = require('path');
const { execFile } = require('child_process');

function createPythonSubprocess() {
  // Define the path to your Python executable
  // If Python is in your PATH, you might just use 'python'
  // Adjust the path to your actual Python script
  const pythonExecutable = 'python'; // or python3 on some systems
  const scriptPath = './dash_app/APIpoller.py';

  // Spawn the Python subprocess
  
const pathToExecutable = path.join(__dirname, 'dist/APIpoller.exe');

execFile(pathToExecutable, (error, stdout, stderr) => {
  if (error) {
    throw error;
  }
  console.log(stdout);
});
}

// Call the function to start the Python script
createPythonSubprocess();

function createWindow() {

  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  // Create the browser window.
  let win = new BrowserWindow({
    width: width,
    height: height,
    webPreferences: {
      nodeIntegration: true
    },
    icon: path.join(__dirname, './dash_app/assets/icon.png')
  });

  // and load the Dash app's URL
  win.loadURL('http://127.0.0.1:8050'); // Use your Dash app's URL
}
function checkDashServerReady() {
    http.get('http://127.0.0.1:8050', (resp) => {
        if (resp.statusCode === 200) {
            // If server is ready, create the Electron window
            setTimeout(createWindow, 1000); 
        } else {
            // If server is not ready, check again after a delay
            console.log('Waiting for Dash server to become ready...');
            setTimeout(checkDashServerReady, 1000);
        }
    }).on("error", (err) => {
        console.log('Waiting for Dash server to start...');
        setTimeout(checkDashServerReady, 1000);
    });
}

app.whenReady().then(checkDashServerReady).catch(err => console.error('Failed to launch:', err));
