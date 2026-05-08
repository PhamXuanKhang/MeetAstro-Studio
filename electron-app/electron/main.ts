import { app, BrowserWindow, ipcMain, dialog, shell, screen } from 'electron'
import { createServer } from 'http'
import path from 'path'
import fs from 'fs'
import { PythonRecorder } from './audio/pythonRecorder'

const AUTH_CALLBACK_PORT = 54321

const AUTH_CALLBACK_HTML = `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>Xác thực thành công</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}
    .card{background:#fff;border-radius:16px;padding:48px 40px;text-align:center;max-width:380px;width:90%;box-shadow:0 4px 32px rgba(0,0,0,.08)}
    .icon{width:56px;height:56px;background:#d1fae5;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-size:24px}
    h1{color:#0f172a;font-size:20px;font-weight:700;margin-bottom:10px}
    p{color:#64748b;font-size:14px;line-height:1.6}
    .app{color:#0ea5e9;font-weight:600}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✓</div>
    <h1>Xác thực thành công!</h1>
    <p>Bạn có thể quay lại <span class="app">MeetAstro</span> để tiếp tục.</p>
  </div>
  <script>
    var s=window.location.search,h=window.location.hash;
    if(s||h) window.location.href='meetastro://auth/callback'+s+h;
  </script>
</body>
</html>`

function startAuthCallbackServer() {
  const server = createServer((_req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' })
    res.end(AUTH_CALLBACK_HTML)
  })
  server.on('error', (err: NodeJS.ErrnoException) => {
    if (err.code === 'EADDRINUSE') {
      console.warn(`[auth] port ${AUTH_CALLBACK_PORT} in use — callback server skipped`)
    } else {
      console.error('[auth] callback server error:', err.message)
    }
  })
  server.listen(AUTH_CALLBACK_PORT, '127.0.0.1', () => {
    console.log(`[auth] callback server listening on http://127.0.0.1:${AUTH_CALLBACK_PORT}`)
  })
}

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow: BrowserWindow | null = null
let pipWindow: BrowserWindow | null = null
let pythonRecorder: PythonRecorder | null = null
let rendererReady = false
const pendingDeepLinks: string[] = []
const approvedReadPaths = new Set<string>()

interface PipState {
  isRecording: boolean
  elapsedSeconds: number
  lastTranscriptLine?: string
}

function isMeetastroUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'meetastro:'
  } catch {
    return false
  }
}

function findDeepLink(argv: string[]): string | null {
  for (const arg of argv) {
    // Windows sometimes wraps protocol URLs in quotes
    const cleaned = arg.replace(/^["']|["']$/g, '')
    if (cleaned.startsWith('meetastro://')) return cleaned
  }
  return null
}

function sendDeepLink(url: string) {
  if (!isMeetastroUrl(url)) return
  console.log('[auth] sendDeepLink:', url)
  if (!mainWindow || mainWindow.isDestroyed() || !rendererReady) {
    console.log('[auth] window not ready, queuing deep link')
    pendingDeepLinks.push(url)
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.focus()
  mainWindow.webContents.send('auth:deepLink', url)
  console.log('[auth] auth:deepLink IPC sent')
}

function flushDeepLinks() {
  while (pendingDeepLinks.length > 0) {
    const url = pendingDeepLinks.shift()
    if (url) sendDeepLink(url)
  }
}

function registerProtocol() {
  if (process.platform === 'win32' && isDev) {
    app.setAsDefaultProtocolClient('meetastro', process.execPath, [path.resolve(process.argv[1])])
    return
  }
  app.setAsDefaultProtocolClient('meetastro')
}

const gotSingleInstanceLock = app.requestSingleInstanceLock()
if (!gotSingleInstanceLock) {
  app.exit(0)
} else {
  app.on('second-instance', (_event, argv) => {
    console.log('[auth] second-instance argv:', JSON.stringify(argv))
    const deepLink = findDeepLink(argv)
    console.log('[auth] deep-link found:', deepLink ?? 'none')
    if (deepLink) sendDeepLink(deepLink)
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })
}

app.on('open-url', (event, url) => {
  event.preventDefault()
  sendDeepLink(url)
})

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1100,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: 'AI Meeting Assistant',
    backgroundColor: '#f8fafc',
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.webContents.once('did-finish-load', () => {
    rendererReady = true
    flushDeepLinks()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    rendererReady = false
  })
}

app.whenReady().then(() => {
  startAuthCallbackServer()
  registerProtocol()
  createWindow()
  pythonRecorder = new PythonRecorder()

  const launchDeepLink = findDeepLink(process.argv)
  if (launchDeepLink) sendDeepLink(launchDeepLink)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (pythonRecorder) {
    pythonRecorder.destroy()
    pythonRecorder = null
  }
  pipWindow = null
  if (process.platform !== 'darwin') app.quit()
})

// IPC: Audio recording
ipcMain.handle('audio:start', async (_event, config: Record<string, unknown>) => {
  if (!pythonRecorder) return { error: 'Recorder not initialized' }
  return pythonRecorder.start(config)
})

ipcMain.handle('audio:stop', async () => {
  if (!pythonRecorder) return { error: 'Recorder not initialized' }
  const result = await pythonRecorder.stop()
  if (result.output_path) approvedReadPaths.add(path.resolve(result.output_path))
  return result
})

ipcMain.handle('audio:status', async () => {
  if (!pythonRecorder) return { isRecording: false }
  return pythonRecorder.getStatus()
})

// IPC: File dialogs
ipcMain.handle('dialog:openFile', async (_event, filters: { name: string; extensions: string[] }[]) => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: filters || [{ name: 'Audio Files', extensions: ['wav', 'mp3', 'm4a', 'ogg', 'flac'] }],
  })
  if (result.canceled || result.filePaths.length === 0) return null
  const chosen = result.filePaths[0]
  approvedReadPaths.add(path.resolve(chosen))
  return chosen
})

ipcMain.handle('dialog:saveFile', async (_event, opts: { content: string; defaultName: string; filters?: { name: string; extensions: string[] }[] }) => {
  const result = await dialog.showSaveDialog({
    defaultPath: opts.defaultName,
    filters: opts.filters || [{ name: 'All Files', extensions: ['*'] }],
  })
  if (result.canceled || !result.filePath) return null
  fs.writeFileSync(result.filePath, opts.content, 'utf-8')
  return result.filePath
})

// IPC: Local file access for audio upload
ipcMain.handle('file:readBytes', async (_event, filePath: string) => {
  const resolved = path.resolve(filePath)
  if (!approvedReadPaths.has(resolved)) {
    throw new Error('Access denied: file path was not approved via file dialog or recorder.')
  }
  const bytes = await fs.promises.readFile(resolved)
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)
})

// IPC: Config
ipcMain.handle('config:getApiUrl', () => {
  return process.env.VITE_API_BASE_URL || 'http://localhost:8000'
})

// IPC: PIP mini-window
function createPipWindow(initialState?: PipState) {
  const { workAreaSize } = screen.getPrimaryDisplay()
  pipWindow = new BrowserWindow({
    width: 300,
    height: 148,
    x: workAreaSize.width - 316,
    y: workAreaSize.height - 164,
    alwaysOnTop: true,
    frame: false,
    resizable: false,
    skipTaskbar: true,
    backgroundColor: '#1e293b',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: ['--pip-mode'],
    },
  })

  if (isDev) {
    pipWindow.loadURL('http://localhost:5173')
  } else {
    pipWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  if (initialState) {
    pipWindow.webContents.once('did-finish-load', () => {
      pipWindow?.webContents.send('pip:state', initialState)
    })
  }

  pipWindow.on('closed', () => {
    pipWindow = null
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('pip:closed')
    }
  })
}

ipcMain.handle('pip:open', (_event, state: PipState) => {
  if (pipWindow && !pipWindow.isDestroyed()) {
    pipWindow.webContents.send('pip:state', state)
    if (pipWindow.isMinimized()) pipWindow.restore()
    pipWindow.show()
    return
  }
  createPipWindow(state)
})

ipcMain.handle('pip:close', () => {
  pipWindow?.close()
  pipWindow = null
})

ipcMain.handle('pip:updateState', (_event, state: PipState) => {
  if (pipWindow && !pipWindow.isDestroyed()) {
    pipWindow.webContents.send('pip:state', state)
  }
})

ipcMain.handle('pip:stopRecording', () => {
  // Stop signal from PIP → forward to main renderer
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('recording:stopFromPip')
  }
  // Bring main window to foreground
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  }
  pipWindow?.close()
  pipWindow = null
})

ipcMain.handle('pip:focusMain', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  }
  pipWindow?.close()
  pipWindow = null
})

// IPC: Auth
ipcMain.handle('auth:openExternalUrl', async (_event, url: string) => {
  const parsed = new URL(url)
  const allowedHost =
    parsed.hostname.endsWith('.supabase.co') ||
    parsed.hostname === 'accounts.google.com'
  if (parsed.protocol !== 'https:' || !allowedHost) {
    throw new Error('Auth URL không hợp lệ.')
  }
  await shell.openExternal(url)
})

