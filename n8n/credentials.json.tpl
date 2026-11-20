[
  {
    "id": "ebPostgres000001",
    "name": "Energy Balance DB",
    "type": "postgres",
    "data": {
      "host": "__DB_HOST__",
      "port": __DB_PORT__,
      "database": "__DB_NAME__",
      "user": "__DB_USER__",
      "password": "__DB_PASSWORD__",
      "ssl": "disable",
      "allowUnauthorizedCerts": false
    }
  },
  {
    "id": "ebSmtpMailpit001",
    "name": "SMTP и-мэйл (локал: Mailpit, сервер: Gmail)",
    "type": "smtp",
    "data": {
      "user": "__SMTP_USER__",
      "password": "__SMTP_PASSWORD__",
      "host": "__SMTP_HOST__",
      "port": __SMTP_PORT__,
      "secure": __SMTP_SECURE__,
      "disableStartTls": __SMTP_DISABLE_STARTTLS__
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
    "id": "ebHookAuth000001",
    "name": "Webhook token (X-Internal-Token)",
    "type": "httpHeaderAuth",
    "data": {
      "name": "X-Internal-Token",
      "value": "__INTERNAL_TOKEN__"
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
  },
  {
    "id": "ebBrevoApiKey001",
    "name": "Brevo API key",
    "type": "httpHeaderAuth",
    "data": {
      "name": "api-key",
      "value": "__BREVO_API_KEY__"
    }
  },
  {
    "id": "ebSmtp2goKey0001",
    "name": "SMTP2GO API key",
    "type": "httpHeaderAuth",
    "data": {
      "name": "X-Smtp2go-Api-Key",
      "value": "__SMTP2GO_API_KEY__"
    }
  }
]
