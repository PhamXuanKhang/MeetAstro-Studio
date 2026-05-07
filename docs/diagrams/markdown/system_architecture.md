flowchart LR
  U[Users<br/>(User 1, User 2,<br/>User ...)]
  E[Frontend<br/>(Electron)]
  SB[(Supabase<br/>DB + Auth + Realtime)]
  API[FastAPI API<br/>/api/v1]
  FS[Audio<br/>(local — user machine)]
  RQ[Redis queue]

  U -->|Interact| E
  E -->|Supabase SDK<br/>Auth, CRUD, Realtime| SB
  E -->|HTTP<br/>Upload, AI jobs,<br/>Jira push, Provider settings| API

  API -->|audio_storage_path ref| FS
  API -->|Enqueue job| RQ

  subgraph CW[Celery Workers]
    W1[Worker instance #1]
    WN[Worker instance #N]
  end

  RQ -->|2 jobs in queue concurrently| W1
  RQ -->|2 jobs /x sec concurrently| WN

  subgraph WI[Worker pipeline]
    AT[Audio transcription<br/>(Whisper API)]
    AI[Action item analysis<br/>(GPT-4o)]
    AT --> AI
  end

  W1 --> AT
  WN --> AT

  J[Jira]

  AI -->|Save transcript_segments,<br/>analysis_results, action_items| SB
  AI -->|Push issues| J
  SB -->|Realtime events<br/>(status, segments, sync_status)| E
