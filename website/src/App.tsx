import { downloadConfig } from './config'

const features = [
  {
    tag: 'Capture',
    title: 'Record or upload every meeting',
    text: 'Bring in live recordings, audio files, or video files and keep the original meeting context intact.',
    tone: 'peach',
  },
  {
    tag: 'Transcript',
    title: 'Readable transcripts with speakers',
    text: 'Review speaker-separated transcripts before AI analysis so the final notes stay grounded in what was said.',
    tone: 'mint',
  },
  {
    tag: 'Decisions',
    title: 'Summaries that keep teams aligned',
    text: 'Turn long conversations into concise summaries, key decisions, and parking-lot notes.',
    tone: 'sky',
  },
  {
    tag: 'Jira-ready',
    title: 'Action items in Epic → Task → Subtask form',
    text: 'MeetAstro structures follow-up work in the same hierarchy your product team pushes to Jira.',
    tone: 'lavender',
  },
]

const workflow = [
  ['01', 'Record or upload', 'Start from system audio, microphone audio, or a meeting file.'],
  ['02', 'Review transcript', 'Clean up speakers and important wording before analysis.'],
  ['03', 'Generate action items', 'Extract summary, decisions, owners, deadlines, and confidence scores.'],
  ['04', 'Push to Jira', 'Approve the work tree and send Epics, Tasks, and Subtasks to Jira.'],
]

const faqs = [
  ['Is MeetAstro a meeting bot?', 'No. MeetAstro is a desktop workflow for turning meeting audio into reviewed notes and Jira-ready work items.'],
  ['Can I review output before Jira?', 'Yes. The review step is central: edit, approve, reject, and add tasks before anything is pushed.'],
  ['What installer is available today?', 'The first Windows build is distributed as a Windows installer from GitHub Releases.'],
  ['Does the web page replace the app?', 'No. The web page explains and distributes the desktop app; the actual workflow runs in MeetAstro.'],
]

function DownloadButton({ variant = 'primary' }: { variant?: 'primary' | 'light' }) {
  const className = variant === 'light' ? 'button button-light' : 'button button-primary'

  if (!downloadConfig.url) {
    return (
      <span className={`${className} is-disabled`} aria-disabled="true">
        Download coming soon
      </span>
    )
  }

  return (
    <a className={className} href={downloadConfig.url} target="_blank" rel="noreferrer">
      Download for Windows
    </a>
  )
}

export default function App() {
  const releaseMeta = [
    'Windows installer',
    `v${downloadConfig.version}`,
    downloadConfig.size,
  ].filter(Boolean).join(' · ')

  return (
    <div className="site-shell">
      <header className="top-nav" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="MeetAstro home">
          <span className="brand-mark">M</span>
          <span>MeetAstro</span>
        </a>
        <nav className="nav-links" aria-label="Landing page sections">
          <a href="#features">Features</a>
          <a href="#workflow">Workflow</a>
          <a href="#security">Security</a>
          <a href="#faq">FAQ</a>
        </nav>
        <DownloadButton />
      </header>

      <main id="top">
        <section className="hero-band" aria-labelledby="hero-title">
          <div className="hero-dots" aria-hidden="true">
            <span className="dot dot-pink" />
            <span className="dot dot-yellow" />
            <span className="dot dot-teal" />
            <span className="wire wire-left" />
            <span className="wire wire-right" />
          </div>
          <div className="hero-content">
            <p className="eyebrow">AI meeting minutes for Jira teams</p>
            <h1 id="hero-title">Turn meetings into Jira-ready work.</h1>
            <p className="hero-subtitle">
              MeetAstro converts meeting audio into transcripts, decisions, and reviewed action items structured as Epics, Tasks, and Subtasks.
            </p>
            <div className="hero-actions">
              <DownloadButton variant="light" />
              <a className="button button-outline-dark" href="#workflow">See how it works</a>
            </div>
            <p className="download-meta">{releaseMeta}</p>
          </div>
          <div className="mockup-card" role="img" aria-label="MeetAstro workspace mockup showing a meeting summary, transcript, action items, and Jira sync progress">
            <div className="mockup-sidebar">
              <span className="mockup-logo">M</span>
              <span className="mockup-pill active">Summary</span>
              <span className="mockup-pill">Transcript</span>
              <span className="mockup-pill">Action Items</span>
            </div>
            <div className="mockup-main">
              <div className="mockup-header">
                <div>
                  <p className="mockup-kicker">Sprint planning</p>
                  <h2>Launch follow-up</h2>
                </div>
                <span className="badge purple">Draft</span>
              </div>
              <div className="mockup-grid">
                <article className="mini-card yellow">
                  <span>Key decision</span>
                  <strong>Ship the beta with Jira sync enabled.</strong>
                </article>
                <article className="mini-card mint">
                  <span>Owner</span>
                  <strong>Speaker A · Friday</strong>
                </article>
              </div>
              <div className="task-tree">
                <div className="tree-row epic">Epic · Beta launch readiness</div>
                <div className="tree-row task">Task · Validate installer download</div>
                <div className="tree-row subtask">Subtask · Confirm release asset link</div>
              </div>
            </div>
          </div>
        </section>

        <section className="section intro" aria-labelledby="intro-title">
          <p className="eyebrow dark">Why MeetAstro</p>
          <h2 id="intro-title">Meetings create momentum only when follow-up is clear.</h2>
          <p>
            Teams already discuss decisions, owners, deadlines, and blockers in calls. MeetAstro captures that context, gives humans a review step, and turns the final output into Jira-shaped work.
          </p>
        </section>

        <section className="section feature-grid" id="features" aria-labelledby="features-title">
          <div className="section-heading">
            <p className="eyebrow dark">Features</p>
            <h2 id="features-title">From conversation to structured delivery.</h2>
          </div>
          <div className="cards-grid">
            {features.map((feature) => (
              <article className={`feature-card ${feature.tone}`} key={feature.title}>
                <span className="tag">{feature.tag}</span>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section workflow" id="workflow" aria-labelledby="workflow-title">
          <div>
            <p className="eyebrow dark">Workflow</p>
            <h2 id="workflow-title">A review-first path from audio to Jira.</h2>
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

        <section className="section security" id="security" aria-labelledby="security-title">
          <div className="security-card">
            <p className="eyebrow dark">Trust & control</p>
            <h2 id="security-title">Human review before automation.</h2>
            <p>
              MeetAstro is designed for teams that need AI speed without skipping accountability. Users review transcripts and action items before Jira sync, provider keys are configured by the user, and backend data paths stay aligned with Supabase auth.
            </p>
          </div>
          <div className="audience-card">
            <span className="tag green">Built for</span>
            <h3>Product, engineering, and delivery teams</h3>
            <p>Best for sprint planning, project reviews, customer calls, and any meeting where outcomes must become trackable work.</p>
          </div>
        </section>

        <section className="section faq" id="faq" aria-labelledby="faq-title">
          <div className="section-heading">
            <p className="eyebrow dark">FAQ</p>
            <h2 id="faq-title">Everything needed to try the app.</h2>
          </div>
          <div className="faq-list">
            {faqs.map(([question, answer]) => (
              <article className="faq-item" key={question}>
                <h3>{question}</h3>
                <p>{answer}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section final-cta" aria-labelledby="final-cta-title">
          <h2 id="final-cta-title">Bring meeting follow-up into one reviewed workflow.</h2>
          <p>Download MeetAstro for Windows and turn your next conversation into structured execution.</p>
          <DownloadButton />
          <span>{releaseMeta}</span>
        </section>
      </main>

      <footer className="footer">
        <div>
          <a className="brand" href="#top" aria-label="MeetAstro home">
            <span className="brand-mark">M</span>
            <span>MeetAstro</span>
          </a>
          <p>AI meeting minutes, transcript review, and Jira-ready action items.</p>
        </div>
        <nav aria-label="Footer links">
          <a href="#features">Features</a>
          <a href="#workflow">Workflow</a>
          <a href="#security">Security</a>
          <a href="#faq">FAQ</a>
        </nav>
      </footer>
    </div>
  )
}
