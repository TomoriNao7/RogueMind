const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let mainWindow = null;
let backendProcess = null;
const BACKEND_PORT = 8000;

function getBackendConfig() {
  // 优先使用打包好的 backend.exe（PyInstaller 独立版，无需 Python 环境）
  const prodExe = path.join(process.resourcesPath, 'backend', 'backend.exe');
  const devPython = 'E:/anaconda/envs/RogueMind/python.exe';
  const devDir = path.join(__dirname, '..', 'backend');

  if (fs.existsSync(prodExe)) {
    return { exe: prodExe, cwd: path.join(process.resourcesPath, 'backend') };
  }
  return { exe: devPython, cwd: devDir };
}

function startBackend() {
  const { exe, cwd } = getBackendConfig();
  console.log(`[RogueMind] Starting backend: ${exe}`);

  const isExe = exe.endsWith('.exe') && !exe.includes('python');
  const args = isExe ? [] : [
    '-m', 'uvicorn', 'app.main:app',
    '--host', '127.0.0.1', '--port', String(BACKEND_PORT),
    '--log-level', 'warning',
  ];

  backendProcess = spawn(exe, args, {
    cwd,
    stdio: 'pipe',
    windowsHide: true,  // 隐藏控制台窗口
  });

  let started = false;
  backendProcess.stderr.on('data', (d) => {
    const msg = d.toString();
    if (msg.includes('Uvicorn running') || msg.includes('Application startup complete')) {
      started = true;
    }
    console.log(`[Backend] ${msg}`);
  });
  backendProcess.stdout.on('data', (d) => console.log(`[Backend] ${d}`));
  backendProcess.on('error', (err) => {
    dialog.showErrorBox('启动失败', `无法启动后端服务：${err.message}\n\n请确认 Python 环境已安装`);
  });
  backendProcess.on('exit', (code) => {
    if (!started && code !== 0) {
      dialog.showErrorBox('后端异常退出', `后端进程意外退出（代码 ${code}）\n请检查：\n1. Python 环境是否完整\n2. 端口 ${BACKEND_PORT} 是否被占用`);
    }
  });
}

function stopBackend() {
  if (backendProcess) { backendProcess.kill(); backendProcess = null; }
}

function waitForBackend(maxRetries = 90) {
  return new Promise((resolve, reject) => {
    let tries = 0;
    const check = () => {
      tries++;
      require('http').get(`http://127.0.0.1:${BACKEND_PORT}/api/health`, (res) => {
        if (res.statusCode === 200) return resolve();
        if (tries < maxRetries) setTimeout(check, 1000);
        else reject(new Error('后端启动超时'));
      }).on('error', () => {
        if (tries < maxRetries) setTimeout(check, 1000);
        else reject(new Error('后端连接失败'));
      });
    };
    check();
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 800, minWidth: 960, minHeight: 640,
    backgroundColor: '#0D0D0D',
    title: 'RogueMind - 明日方舟集成战略助手',
    webPreferences: { nodeIntegration: false, contextIsolation: true },
    autoHideMenuBar: true,
    show: false,  // 等后端就绪后再显示
  });

  // 显示加载提示
  mainWindow.loadURL(`data:text/html,
    <body style="background:#0D0D0D;color:#999;display:flex;align-items:center;justify-content:center;
    height:100vh;font-family:sans-serif;margin:0">
    <div style="text-align:center"><h1 style="color:#fff;font-weight:400">RogueMind</h1>
    <p>正在启动后端服务...</p></div></body>`);

  try {
    await waitForBackend();
  } catch (e) {
    dialog.showErrorBox('启动失败', e.message);
    app.quit();
    return;
  }

  // 加载前端（兼容打包和开发两种模式）
  const paths = [
    path.join(__dirname, 'frontend-dist', 'index.html'),       // 打包后
    path.join(__dirname, '..', 'frontend', 'dist', 'index.html'), // 开发时
  ];

  let loaded = false;
  for (const fp of paths) {
    if (fs.existsSync(fp)) {
      mainWindow.loadFile(fp).then(() => { loaded = true; });
      break;
    }
  }
  if (!loaded) {
    mainWindow.loadURL('http://localhost:5173');
  }

  mainWindow.show();
}

app.whenReady().then(() => { startBackend(); createWindow(); });
app.on('window-all-closed', () => { stopBackend(); app.quit(); });
app.on('before-quit', () => { stopBackend(); });
app.on('activate', () => { if (!mainWindow) createWindow(); });
