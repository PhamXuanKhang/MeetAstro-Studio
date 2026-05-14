import { spawn, ChildProcess } from 'child_process'
import path from 'path'

interface RecorderResponse {
  status: string
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
    const scriptPath = this.resolveScriptPath()

    try {
      this.process = spawn('python', [scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
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
    }
  }

  private resolveScriptPath(): string {
    const fs = require('fs')

    // In packaged app, extraResources lands next to app.asar.
    const packaged = path.join(process.resourcesPath, 'python', 'recorder_server.py')
    if (fs.existsSync(packaged)) return packaged

    // Dev build output lives at electron-app/dist-electron.
    const devFromDist = path.join(__dirname, '../python/recorder_server.py')
    if (fs.existsSync(devFromDist)) return devFromDist

    // Fallback for direct ts-node-style execution from electron/audio.
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
      const timeout = setTimeout(() => {
        this.pendingResolve = null
        console.error(`[PythonRecorder] ${action} timed out`)
        reject(new Error('Python recorder timeout'))
      }, 30000)

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
