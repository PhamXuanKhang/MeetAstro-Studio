import { useCallback } from 'react'

type ElectronAPI = {
  openFileDialog: (filters?: { name: string; extensions: string[] }[]) => Promise<string | null>
  saveFile: (opts: { content: string; defaultName: string; filters?: { name: string; extensions: string[] }[] }) => Promise<string | null>
}

function getElectronAPI(): ElectronAPI | null {
  return (window as unknown as { electronAPI?: ElectronAPI }).electronAPI ?? null
}

export function useFileDialog() {
  const openFile = useCallback(
    async (filters?: { name: string; extensions: string[] }[]): Promise<string | null> => {
      const api = getElectronAPI()
      if (!api) {
        // Fallback: HTML file input (for browser dev mode)
        return new Promise((resolve) => {
          const input = document.createElement('input')
          input.type = 'file'
          input.accept = '.wav,.mp3,.m4a,.ogg,.flac'
          input.onchange = () => {
            const file = input.files?.[0]
            resolve(file ? URL.createObjectURL(file) : null)
          }
          input.click()
        })
      }
      return api.openFileDialog(
        filters ?? [{ name: 'Audio Files', extensions: ['wav', 'mp3', 'm4a', 'ogg', 'flac'] }]
      )
    },
    []
  )

  const saveFile = useCallback(
    async (
      content: string,
      defaultName: string,
      filters?: { name: string; extensions: string[] }[]
    ): Promise<string | null> => {
      const api = getElectronAPI()
      if (!api) {
        // Fallback: browser download
        const blob = new Blob([content], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = defaultName
        a.click()
        URL.revokeObjectURL(url)
        return defaultName
      }
      return api.saveFile({ content, defaultName, filters })
    },
    []
  )

  return { openFile, saveFile }
}
