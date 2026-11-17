[
  {
    "id": "ebPostgres000001",
    "name": "Energy Balance DB",
    "type": "postgres",
    "data": {
      "host": "db",
      "port": 5432,
      "database": "energybalance",
      "user": "eb",
      "password": "__DB_PASSWORD__",
      "ssl": "disable",
      "allowUnauthorizedCerts": false
    }
  },
  {
    "id": "ebSmtpMailpit001",
    "name": "Mailpit SMTP (Gmail-ийн орлуулагч)",
    "type": "smtp",
    "data": {
      "user": "",
      "password": "",
      "host": "mailpit",
      "port": 1025,
      "secure": false,
      "disableStartTls": true
    }
  },
  {
    "id": "ebAnthropic00001",
    "name": "Anthropic (Claude)",
    "type": "anthropicApi",
    "data": {
      "apiKey": "__ANTHROPIC_API_KEY__",
      "url": "https://api.anthropic.com"
    }
  },
  {
    "id": "ebGemini00000001",
    "name": "Google Gemini",
    "type": "googlePalmApi",
    "data": {
      "host": "https://generativelanguage.googleapis.com",
      "apiKey": "__GEMINI_API_KEY__"
    }
  }
]
