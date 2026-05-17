export type DownloadMetadata = {
  available: boolean
  url: string
  filename: string
  version: string
  size: string
  platform: string
  publishedAt?: string
}

export type SiteMedia = {
  heroImageUrl: string
  demoEmbedUrl: string
}

export const fallbackDownloadMetadata: DownloadMetadata = {
  available: false,
  url: '',
  filename: '',
  version: '',
  size: '',
  platform: 'Windows',
}

export const siteMedia: SiteMedia = {
  heroImageUrl: '/banner.png',
  demoEmbedUrl: import.meta.env.VITE_DEMO_EMBED_URL || 'https://www.youtube.com/embed/P8OAuSqKbho?si=yMzhcDnSgBks1mFE',
}

export async function fetchDownloadMetadata(): Promise<DownloadMetadata> {
  const response = await fetch('/downloads/metadata.json', { cache: 'no-store' })
  if (!response.ok) {
    throw new Error('Download metadata unavailable')
  }
  return response.json()
}
