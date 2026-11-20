# TODO

## 1. Connect Facebook Messenger to the chat agent (~15 min)

The code is already live on Railway. These steps need your Facebook account.
Full details: [docs/MESSENGER.md](docs/MESSENGER.md)

- [ ] Make sure you are an admin of the Energy Balance Facebook Page (create the Page first if there isn't one)
- [ ] Go to https://developers.facebook.com/apps → **Create app** → choose the **Messenger** use case
- [ ] In the app: **Messenger → Messenger API Settings → Configure webhooks**
  - Callback URL: `https://web-production-759272bf.up.railway.app/webhooks/messenger`
  - Verify token: the `FB_VERIFY_TOKEN` value in `.env.railway`
  - Click **Verify and save**, then tick the fields `messages` and `messaging_postbacks`
- [ ] **Generate access tokens** → connect the Page → **Generate** → copy the Page access token (starts with `EAA…`)
- [ ] Check the Page row shows the `messages` webhook subscription as active
- [ ] (Recommended) **App settings → Basic → App secret** → copy it
- [ ] In the project folder, run (Railway restarts the site by itself):
  ```bash
  railway variables --service web --set FB_PAGE_TOKEN=EAA... --set FB_APP_SECRET=...
  ```
- [ ] Test: message the Page from Messenger, e.g. «Барилгын аудит хэд вэ?» — the bot should answer within ~10–20 seconds
- [ ] Check the conversation appears in the admin **Чат** page with the "Messenger" label

Good to know:
- Until Meta reviews the app, the bot only answers people who have a role on the app (admin / developer / tester). For the defense, message from your own account, or add the instructor under **App roles → Roles** as a tester.
- It answers text messages only.
- If it doesn't reply: `railway logs --service web` and look for lines starting with `[messenger]`.
- To switch it off: remove `FB_PAGE_TOKEN` from the web service variables.

## 2. Before the defense

- [ ] Commit and push the latest changes (Brevo email, Messenger, README screenshots, new diagrams):
  ```bash
  git add -A && git commit -m "feat: real email (Brevo), Messenger webhook, docs" && git push
  ```
  The repo is public — `.env` and `.env.railway` are gitignored, but check `git status` shows neither before pushing.
- [ ] Create the n8n owner account on Railway: https://n8n-production-0a370bb0.up.railway.app (needed to show the workflows and Executions live)
- [ ] Delete the test bookings "Brevo Тест" / "Brevo Тест 2" (#17, #19) and "Railway Тест" from the admin panel
- [ ] Do one full run-through on the live site: booking form → email arrives in Gmail (check spam), chat question, energy calculator, content post → approve
- [ ] Update the guide book for mom: it still shows the old "SMTP" diagrams and may mention Mailpit for customer emails (they now go to real inboxes via Brevo)

## 3. After the defense

- [ ] Rotate the keys that were pasted into chat: Gemini API key and Brevo API key, then update them with `railway variables --service n8n --set ...`
- [ ] Decide whether to keep the repo public
- [ ] Optional: get a mailbox at `@energybalance.mn` so emails come from your own domain instead of a `brevosend.com` address
