flowchart TB
  U[User]
  M((MeetAstro System))
  J[Jira]
  A[AI Services]

  %% User <-> MeetAstro
  U -->|Upload Audio or Record meeting| M
  U -->|Edit transcripts or Action items| M
  U -->|Configures Jira credentials| M

  M -->|Show transcript, summary, action items| U
  M -->|Show meeting history| U

  %% MeetAstro <-> Jira
  M -->|Create epic / Task / Subtask| J
  J -->|Return issue keys and URLs| M

  %% MeetAstro <-> AI Services
  M -->|Send audio chunks and transcripts| A
  A -->|Return transcripts, summary, action items| M
