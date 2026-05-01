flowchart LR
  U[Users<br/>(User 1, user 2,<br/>user ...)]
  F[Frontend (Flet)]
  AU[Auth]
  API[FastAPI API]
  FS[File storage<br/>(audio path)]
  RQ[Redis queue]

  U -->|Request| F --> AU --> API
  API -->|Save audio + create meeting status| FS
  API -->|Enqueue or update job| RQ

  subgraph CW[Celery Workers]
    W1[Worker instance #1]
    WN[Worker instance #N]
  end

  RQ -->|2 jobs in queue concurrently| W1
  RQ -->|2 jobs /x sec concurrently| WN

  subgraph WI[Worker instances]
    AT[Audio transcription<br/>(Whisper API)]
    AI[Action item analysis<br/>(GPT-4o)]
    AT --> AI
  end

  W1 --> AT
  WN --> AT

  PG[(PostgreSQL<br/>db)]
  J[Jira]

  AI -->|Save to| PG
  AI -->|Push to| J
