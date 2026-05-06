import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron'
import path from 'path'
import fs from 'fs'
import { PythonRecorder } from './audio/pythonRecorder'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow: BrowserWindow | null = null
let pythonRecorder: PythonRecorder | null = null
let rendererReady = false
const pendingDeepLinks: string[] = []

function isMeetastroUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'meetastro:'
  } catch {
    return false
  }
}

function findDeepLink(argv: string[]): string | null {
  return argv.find((arg) => arg.startsWith('meetastro://')) ?? null
}

function sendDeepLink(url: string) {
  if (!isMeetastroUrl(url)) return
  if (!mainWindow || mainWindow.isDestroyed() || !rendererReady) {
    pendingDeepLinks.push(url)
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.focus()
  mainWindow.webContents.send('auth:deepLink', url)
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
    const deepLink = findDeepLink(argv)
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
  if (process.platform !== 'darwin') app.quit()
})

// IPC: Audio recording
ipcMain.handle('audio:start', async (_event, config: Record<string, unknown>) => {
  if (!pythonRecorder) return { error: 'Recorder not initialized' }
  return pythonRecorder.start(config)
})

ipcMain.handle('audio:stop', async () => {
  if (!pythonRecorder) return { error: 'Recorder not initialized' }
  return pythonRecorder.stop()
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
  return result.filePaths[0]
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
  const bytes = await fs.promises.readFile(resolved)
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)
})

// IPC: Config
ipcMain.handle('config:getApiUrl', () => {
  return process.env.VITE_API_BASE_URL || 'http://localhost:8000'
})

// IPC: Auth
ipcMain.handle('auth:openExternalUrl', async (_event, url: string) => {
  const parsed = new URL(url)
  const allowedHost = parsed.hostname.endsWith('.supabase.co') || parsed.hostname === 'accounts.google.com'
  if (parsed.protocol !== 'https:' || !allowedHost) {
    throw new Error('Auth URL không hợp lệ.')
  }
  await shell.openExternal(url)
})
