import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import path from 'path'
import fs from 'fs'
import { PythonRecorder } from './audio/pythonRecorder'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow: BrowserWindow | null = null
let pythonRecorder: PythonRecorder | null = null

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

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(() => {
  createWindow()
  pythonRecorder = new PythonRecorder()

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
