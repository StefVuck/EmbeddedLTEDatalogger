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
  const subprocess = spawn(pythonExecutable, [scriptPath]);

  // Optional: Log stdout and stderr from the subprocess
  subprocess.stdout.on('data', (data) => {
    console.log(`stdout: ${data}`);
  });
  subprocess.stderr.on('data', (data) => {
    console.error(`stderr: ${data}`);
  });  

  // const pathToExecutable = path.join(__dirname, 'dist/APIpoller.exe');

  // execFile(pathToExecutable, (error, stdout, stderr) => {
  //   if (error) {
  //     throw error;
  //   }
  //   console.log(stdout);
  // });
}

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  // Create the browser window.
  let win = new BrowserWindow({
    width: width,
    height: height,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false, // Adjust based on security requirements
    },
    icon: path.join(__dirname, './dash_app/assets/icon.png')
  });

  // Load the Dash app's URL
  win.loadURL('http://127.0.0.1:8050'); // Use your Dash app's URL
}

function checkDashServerReady() {
  http.get('http://127.0.0.1:8050', (resp) => {
    if (resp.statusCode === 200) {
      console.log('Dash server is ready.');
      createWindow();
    } else {
      console.log('Waiting for Dash server to become ready...');
      setTimeout(checkDashServerReady, 1000);
    }
  }).on("error", (err) => {
    console.log('Waiting for Dash server to start...');
    setTimeout(checkDashServerReady, 1000);
  });
}

app.whenReady().then(() => {
  createPythonSubprocess(); // Start the Python script
  checkDashServerReady(); // Check if the Dash server is ready
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

