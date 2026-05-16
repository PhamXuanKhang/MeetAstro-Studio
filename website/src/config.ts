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
  version: '0.1.0',
  size: '',
  platform: 'Windows',
}

export const siteMedia: SiteMedia = {
  heroImageUrl: import.meta.env.VITE_HERO_IMAGE_URL || '/og-image.svg',
  demoEmbedUrl: import.meta.env.VITE_DEMO_EMBED_URL || '',
}

export async function fetchDownloadMetadata(): Promise<DownloadMetadata> {
  const response = await fetch('/downloads/metadata.json', { cache: 'no-store' })
  if (!response.ok) {
    throw new Error('Download metadata unavailable')
  }
  return response.json()
}
