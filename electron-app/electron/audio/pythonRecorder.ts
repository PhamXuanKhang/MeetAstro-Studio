import { spawn, ChildProcess } from 'child_process'
import { BrowserWindow, app } from 'electron'
import fs from 'fs'
import path from 'path'

interface RecorderResponse {
  status: string
  segments?: Array<{ speaker: string; start: number; end: number; text: string }>
  output_path?: string
  error?: string
  is_recording?: boolean
}

export class PythonRecorder {
  private process: ChildProcess | null = null
  private isRecording = false
  private outputPath: string | null = null
  private pendingResolve: ((v: RecorderResponse) => void) | null = null
  private buffer = ''

  constructor() {
    this.spawnProcess()
  }

  private spawnProcess() {
    const command = this.resolveCommand()

    try {
      const env = {
        ...process.env,
        MEETASTRO_RECORDER_LOG_DIR: path.join(app.getPath('userData'), 'logs'),
      }
      this.process = spawn(command.executable, command.args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        env,
      })

      this.process.stdout?.on('data', (data: Buffer) => {
        this.buffer += data.toString()
        const lines = this.buffer.split('\n')
        this.buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue
          try {
            const msg: RecorderResponse = JSON.parse(trimmed)
            if (msg.status === 'stream_partial') {
              BrowserWindow.getAllWindows().forEach((window) => {
                window.webContents.send('audio:streamPartial', msg.segments ?? [])
              })
              continue
            }
            if (this.pendingResolve) {
              const resolve = this.pendingResolve
              this.pendingResolve = null
              resolve(msg)
            }
          } catch {
            // ignore non-JSON lines
          }
        }
      })

      this.process.stderr?.on('data', (data: Buffer) => {
        console.error('[PythonRecorder]', data.toString())
      })

      this.process.on('exit', (code) => {
        console.warn(`[PythonRecorder] Process exited with code ${code}`)
        this.process = null
        this.isRecording = false
      })
    } catch (err) {
      console.error('[PythonRecorder] Failed to spawn Python process:', err)
      this.process = null
    }
  }

  private resolveCommand(): { executable: string; args: string[] } {
    if (app.isPackaged) {
      const executable = path.join(process.resourcesPath, 'python', 'recorder_server', 'recorder_server.exe')
      if (!fs.existsSync(executable)) {
        throw new Error(`Bundled recorder sidecar not found at ${executable}`)
      }
      return { executable, args: [] }
    }

    const scriptPath = this.resolveDevScriptPath()
    return { executable: 'python', args: [scriptPath] }
  }

  private resolveDevScriptPath(): string {
    const devFromDist = path.join(__dirname, '../python/recorder_server.py')
    if (fs.existsSync(devFromDist)) return devFromDist

    return path.join(__dirname, '../../python/recorder_server.py')
  }

  private send(payload: Record<string, unknown>): Promise<RecorderResponse> {
    return new Promise((resolve, reject) => {
      const action = String(payload.action ?? 'unknown')
      if (this.pendingResolve) {
        reject(new Error('Python recorder is busy'))
        return
      }

      if (!this.process || !this.process.stdin) {
        // Try to respawn once
        this.spawnProcess()
        if (!this.process?.stdin) {
          reject(new Error('Python recorder process not available'))
          return
        }
      }

      console.info(`[PythonRecorder] sending ${action}`)
      const timeoutMs = action === 'stop' ? 90000 : 30000
      const timeout = setTimeout(() => {
        this.pendingResolve = null
        console.error(`[PythonRecorder] ${action} timed out`)
        reject(new Error('Python recorder timeout'))
      }, timeoutMs)

      this.pendingResolve = (v) => {
        clearTimeout(timeout)
        console.info(`[PythonRecorder] ${action} response: ${v.status}`)
        resolve(v)
      }

      this.process!.stdin!.write(JSON.stringify(payload) + '\n')
    })
  }

  async start(config: Record<string, unknown> = {}): Promise<RecorderResponse> {
    const result = await this.send({ action: 'start', config })
    if (!result.error) {
      this.isRecording = true
      this.outputPath = result.output_path || null
    }
    return result
  }

  async stop(): Promise<RecorderResponse> {
    const result = await this.send({ action: 'stop' })
    this.isRecording = false
    if (result.output_path) this.outputPath = result.output_path
    return result
  }

  getStatus(): { isRecording: boolean; outputPath: string | null } {
    return { isRecording: this.isRecording, outputPath: this.outputPath }
  }

  destroy() {
    if (this.process) {
      try {
        this.process.stdin?.write(JSON.stringify({ action: 'quit' }) + '\n')
        setTimeout(() => {
          if (this.process) {
            this.process.kill()
            this.process = null
          }
        }, 500)
      } catch {
        this.process.kill()
        this.process = null
      }
    }
  }
}
