const { app, BrowserWindow, screen, dialog } = require('electron')
const { spawn, execFile, fork } = require('child_process');
const http = require('http');
const path = require('path');

function createPythonSubprocess(option) {
  const pythonExecutable = 'python'; // or python3 on some systems
  const scriptPath = './dash_app/APIpoller.py';
  const pathToExecutable = path.join(__dirname, 'dist/APIpoller.exe');

  if (option === 'Python') {
    // Spawn the Python subprocess
    const subprocess = spawn(pythonExecutable, [scriptPath]);

    // Optional: Log stdout and stderr from the subprocess
    subprocess.stdout.on('data', (data) => {
      console.log(`stdout: ${data}`);
    });

    subprocess.stderr.on('data', (data) => {
      console.error(`stderr: ${data}`);
    });

  } else if (option === 'EXE') {
    // Execute the .exe file
    execFile(pathToExecutable, (error, stdout, stderr) => {
      if (error) {
        throw error;
      }
      console.log(stdout);
      if (stderr) {
        console.error(`stderr: ${stderr}`);
      }
    });
  }
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
function promptUserWithDialog() {
  const options = {
    type: 'question',
    buttons: ['Python', 'EXE'],
    title: 'Process Selection',
    message: 'Do you want to run the Python process or the .EXE?',
  };

  dialog.showMessageBox(null, options).then((response) => {
    if (response.response === 0) { // Python was chosen
      createPythonSubprocess('Python');
    } else { // EXE was chosen
      createPythonSubprocess('EXE');
    }
    checkDashServerReady();
  });
}

app.whenReady().then(promptUserWithDialog);

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
