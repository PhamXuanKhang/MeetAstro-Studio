import { useEffect, useState } from 'react'

import { fallbackDownloadMetadata, fetchDownloadMetadata, siteMedia, type DownloadMetadata } from './config'

const features = [
  {
    icon: 'graphic_eq',
    tag: 'Capture',
    title: 'Thu âm và nhập file cuộc họp',
    text: 'Ghi âm trực tiếp hoặc tải lên audio/video để bắt đầu quy trình xử lý sau cuộc họp.',
  },
  {
    icon: 'record_voice_over',
    tag: 'Transcript',
    title: 'Transcript theo người nói',
    text: 'Tạo transcript dễ đọc, tách speaker và giữ lại ngữ cảnh quan trọng cho bước kiểm duyệt.',
  },
  {
    icon: 'account_tree',
    tag: 'Jira schema',
    title: 'Cấu trúc Epic → Task → Subtask',
    text: 'Chuyển kết luận thành action items có owner, deadline, priority và context để sẵn sàng đồng bộ Jira.',
  },
  {
    icon: 'verified_user',
    tag: 'Review',
    title: 'Kiểm duyệt trước khi đồng bộ',
    text: 'Sửa transcript, duyệt action items và chỉ đẩy sang Jira khi nội dung đã được xác nhận.',
  },
]

const workflow = [
  ['01', 'Nhập audio cuộc họp', 'Ghi âm trực tiếp hoặc tải lên file audio/video từ cuộc họp đã diễn ra.'],
  ['02', 'Kiểm tra transcript', 'Rà soát nội dung theo speaker để đảm bảo các quyết định và cam kết không bị sai lệch.'],
  ['03', 'Tạo kế hoạch thực thi', 'AI tổng hợp summary, decisions và action items theo cấu trúc phù hợp Jira.'],
  ['04', 'Duyệt và đồng bộ Jira', 'Chỉnh sửa cây công việc, approve các item cần thiết rồi đẩy sang Jira.'],
]

const metrics = [
  ['4 bước', 'Từ audio đến Jira'],
  ['3 tầng', 'Epic / Task / Subtask'],
  ['Review', 'Kiểm soát trước khi sync'],
]

const faqs = [
  ['MeetAstro có phải meeting bot không?', 'Không. MeetAstro là desktop app để ghi âm hoặc tải file cuộc họp, sau đó tạo transcript, summary và action items.'],
  ['Có thể sửa trước khi đẩy sang Jira không?', 'Có. Bạn có thể chỉnh transcript, sửa từng action item, approve hoặc reject trước khi đồng bộ.'],
  ['Version tải về được cập nhật như thế nào?', 'Trang web đọc metadata release từ `/downloads/metadata.json`, nên khi pipeline release cập nhật file này thì version và link tải sẽ tự đổi.'],
  ['Tôi có thể gắn video demo ở đâu?', 'Đặt `VITE_DEMO_EMBED_URL` bằng link embed YouTube. Nếu chưa cấu hình, trang sẽ hiển thị khung demo chờ nội dung.'],
]

function formatReleaseDate(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(date)
}

function DownloadButton({ metadata, variant = 'primary' }: { metadata: DownloadMetadata; variant?: 'primary' | 'secondary' }) {
  const className = variant === 'secondary' ? 'btn btn-secondary' : 'btn btn-primary'

  if (!metadata.available || !metadata.url) {
    return (
      <span className={`${className} is-disabled`} aria-disabled="true">
        Sắp có bản tải
      </span>
    )
  }

  return (
    <a className={className} href={metadata.url}>
      Tải app cho Windows
      <span className="material-symbols-outlined" aria-hidden="true">download</span>
    </a>
  )
}

function ProductDemo() {
  if (siteMedia.demoEmbedUrl) {
    return (
      <div className="demo-frame video-embed-frame">
        <iframe
          src={siteMedia.demoEmbedUrl}
          title="Video demo MeetAstro"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>
    )
  }

  return (
    <div className="demo-frame">
      <div className="demo-toolbar" aria-hidden="true">
        <span />
        <span />
        <span />
        <p>MeetAstro demo</p>
      </div>
      <div className="video-placeholder" role="img" aria-label="Khung video demo quy trình MeetAstro">
        <div className="play-button">
          <span className="material-symbols-outlined" aria-hidden="true">play_arrow</span>
        </div>
        <div>
          <p className="eyebrow">Video demo</p>
          <h3>Quy trình từ audio cuộc họp đến Jira-ready action items</h3>
          <p>Video demo sẽ hiển thị tại đây khi link YouTube embed được cấu hình.</p>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [downloadMetadata, setDownloadMetadata] = useState<DownloadMetadata>(fallbackDownloadMetadata)

  useEffect(() => {
    fetchDownloadMetadata()
      .then(setDownloadMetadata)
      .catch(() => setDownloadMetadata(fallbackDownloadMetadata))
  }, [])

  const releaseDate = formatReleaseDate(downloadMetadata.publishedAt)
  const releaseMeta = [
    downloadMetadata.platform ? `Bản ${downloadMetadata.platform}` : 'Bản Windows',
    `v${downloadMetadata.version}`,
    downloadMetadata.size,
    releaseDate ? `phát hành ${releaseDate}` : '',
  ].filter(Boolean).join(' · ')

  return (
    <div className="site-shell">
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />
      <div className="landing-grid" aria-hidden="true" />

      <header className="top-nav" aria-label="Điều hướng chính">
        <a className="brand" href="#top" aria-label="MeetAstro home">
          <span className="brand-mark">
            <span className="material-symbols-outlined" aria-hidden="true">hub</span>
          </span>
          <span>MeetAstro</span>
        </a>
        <nav className="nav-links" aria-label="Các khu vực trên trang">
          <a href="#features">Tính năng</a>
          <a href="#demo">Demo</a>
          <a href="#workflow">Quy trình</a>
          <a href="#download">Tải app</a>
          <a href="#faq">FAQ</a>
        </nav>
        <DownloadButton metadata={downloadMetadata} />
      </header>

      <main id="top">
        <section className="hero-section" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="live-badge"><span /> AI meeting minutes cho đội dùng Jira</p>
            <h1 id="hero-title">Biến cuộc họp thành kế hoạch Jira có thể triển khai</h1>
            <p className="hero-subtitle">
              MeetAstro giúp ghi âm hoặc nhập file cuộc họp, tạo transcript, rút ra quyết định và chuyển follow-up thành Epic → Task → Subtask có thể kiểm duyệt trước khi đồng bộ Jira.
            </p>
            <div className="hero-actions">
              <DownloadButton metadata={downloadMetadata} />
              <a className="btn btn-secondary" href="#demo">
                Xem demo
                <span className="material-symbols-outlined" aria-hidden="true">play_circle</span>
              </a>
            </div>
            <p className="release-meta">{releaseMeta}</p>
          </div>

          <div className="product-showcase" aria-label="Ảnh giới thiệu giao diện MeetAstro">
            <img src={siteMedia.heroImageUrl} alt="Giao diện MeetAstro" />
          </div>

          <div className="metric-row" aria-label="Điểm nổi bật của sản phẩm">
            {metrics.map(([value, label]) => (
              <div className="metric-card" key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="section feature-section" id="features" aria-labelledby="features-title">
          <div className="section-heading">
            <p className="eyebrow">Tính năng chính</p>
            <h2 id="features-title">Tập trung vào kết quả sau cuộc họp, không chỉ ghi chú</h2>
            <p>MeetAstro kết nối recording, transcript, review và Jira sync trong một workflow rõ ràng cho đội sản phẩm và kỹ thuật.</p>
          </div>
          <div className="feature-grid">
            {features.map((feature) => (
              <article className="feature-card" key={feature.title}>
                <span className="feature-icon material-symbols-outlined" aria-hidden="true">{feature.icon}</span>
                <div className="feature-content">
                  <span className="chip">{feature.tag}</span>
                  <h3>{feature.title}</h3>
                  <p>{feature.text}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="section demo-section" id="demo" aria-labelledby="demo-title">
          <div className="section-heading centered">
            <p className="eyebrow">Video demo</p>
            <h2 id="demo-title">Xem cách MeetAstro tạo action items từ một cuộc họp</h2>
            <p>Theo dõi luồng nhập audio, kiểm tra transcript, duyệt action items và chuẩn bị đồng bộ Jira.</p>
          </div>
          <ProductDemo />
        </section>

        <section className="section workflow-section" id="workflow" aria-labelledby="workflow-title">
          <div className="section-heading">
            <p className="eyebrow">Quy trình</p>
            <h2 id="workflow-title">Từ cuộc họp đến công việc có người chịu trách nhiệm</h2>
          </div>
          <div className="workflow-list">
            {workflow.map(([step, title, text]) => (
              <article className="workflow-step" key={step}>
                <span>{step}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="section download-section" id="download" aria-labelledby="download-title">
          <div>
            <p className="eyebrow">Tải ứng dụng</p>
            <h2 id="download-title">Cài desktop app để chạy workflow đầy đủ</h2>
            <p>
              Bản desktop hỗ trợ ghi âm, nhập file, kiểm duyệt transcript, tạo action items và đồng bộ Jira. Thông tin version và link tải được lấy từ metadata release.
            </p>
            <DownloadButton metadata={downloadMetadata} />
            <span className="release-meta dark">{releaseMeta}</span>
          </div>
          <div className="download-card">
            <span className="material-symbols-outlined" aria-hidden="true">desktop_windows</span>
            <h3>{downloadMetadata.platform || 'Windows'} installer</h3>
            <p>{downloadMetadata.filename || 'Bản cài đặt sẽ hiển thị khi release được publish.'}</p>
            <ul>
              <li>Desktop app trên Electron</li>
              <li>Đăng nhập Supabase</li>
              <li>AI analysis và Jira sync</li>
            </ul>
          </div>
        </section>

        <section className="section faq-section" id="faq" aria-labelledby="faq-title">
          <div className="section-heading centered">
            <p className="eyebrow">FAQ</p>
            <h2 id="faq-title">Thông tin nhanh trước khi thử MeetAstro</h2>
          </div>
          <div className="faq-grid">
            {faqs.map(([question, answer]) => (
              <article className="faq-item" key={question}>
                <h3>{question}</h3>
                <p>{answer}</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="footer">
        <a className="brand" href="#top" aria-label="MeetAstro home">
          <span className="brand-mark"><span className="material-symbols-outlined" aria-hidden="true">hub</span></span>
          <span>MeetAstro</span>
        </a>
        <p>AI meeting minutes, reviewed action items và Jira-ready execution plan cho đội sản phẩm/kỹ thuật.</p>
      </footer>
    </div>
  )
}
