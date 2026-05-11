export const downloadConfig = {
  url: import.meta.env.VITE_APP_DOWNLOAD_URL?.trim() ?? '',
  version: import.meta.env.VITE_APP_DOWNLOAD_VERSION?.trim() || '0.1.0',
  size: import.meta.env.VITE_APP_DOWNLOAD_SIZE?.trim() ?? '',
}
