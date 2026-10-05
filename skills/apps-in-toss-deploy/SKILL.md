---
name: apps-in-toss-deploy
description: End-to-end Apps-in-Toss (앱인토스, 토스 미니앱) test deployment where Claude does the CLI work and Codex drives the owner's logged-in Chrome to do the console work — register the app, upload the icon, create rewarded ad groups / IAP products, then build the .ait, `ait deploy`, and hand over a QR. Use this whenever the user says things like "토스에 테스트 배포해", "앱인토스 올려", "ait deploy", "콘솔에 앱 등록", "광고 그룹 만들어 ID 넣어", "과금 넣어", hits error 4031, or asks to deploy a Unity WebGL game or granite/vite mini-app to Toss — even if they don't mention Codex or the console explicitly.
---

# Apps-in-Toss deploy (Claude + Codex)

The owner expects this to run without hand-holding: they have been annoyed before when Claude stopped at "please register the app in the console yourself". The console has no API and the `ait` CLI cannot create apps, but Codex can drive the owner's already-logged-in Chrome (`--enable computer_use --enable browser_use_external`). So Claude does build/deploy, Codex does console clicks, and the owner is only asked for things that are legally theirs.

Detailed facts, URLs, error table and sources: `references/knowhow.md` (read the section you need; §3 console, §4 errors, §6 release).

## Who does what

| Step | Who |
|---|---|
| Build `.ait`, `ait deploy`, QR, wiring IDs into config | Claude |
| Register app, icon, support email, ad groups, IAP products, read IDs | Codex (Chrome) |
| Business number, settlement/bank, seal/signature, game rating cert, 검토 요청/출시, consenting to new terms | Owner only |

Keep the hard limits in every Codex prompt: Codex never submits for review, releases, touches other apps, or enters business/bank/identity data. Those are irreversible or legally the owner's.

## Flow

### 1. Check what exists
- Profiles (names only, never print keys): `python3 -c "import json,os;print(list(json.load(open(os.path.expanduser('~/.ait/credentials')))))"`. Known: `default` and `dev` belong to workspace **35273** (apps seoultax, seoultaxdev, screw-toktok, golgol-nyang, spot-difference-daily).
- Find the project's appName (Unity: `Assets/AppsInToss/Editor/AITConfig.asset`, a packaging script's `AIT_APP_NAME` default, runtime config; granite: `granite.config.ts`). All places must agree.
- Try a deploy of any existing `.ait` first: `Code: 4031` means the app does not exist **in this key's workspace** (unregistered, or the appName is taken by someone else) → register it (step 2). A valid key does not imply a valid app.

### 2. Register / configure in the console with Codex
1. Copy `references/console_prompt_template.txt` to the scratchpad and fill it in. Include fallbacks so Codex never has to ask:
   - display name ≤10 chars excluding spaces, no hyphen; appName must be globally unique (give 2 fallbacks like `<name>-daily`).
   - icon exactly 600×600 (resize with PIL LANCZOS if needed).
   - support email is public; reuse the one the owner used for their other apps (in knowhow/past sessions) rather than inventing one.
2. Run in the background (it takes 4–10 min):
   `bash ~/.claude/skills/apps-in-toss-deploy/scripts/codex_console.sh <prompt> <scratchpad>/console.out <repo>`
3. Read the STATUS lines. Handle:
   - `LOGIN_REQUIRED` → owner logs into Chrome; rerun.
   - Icon upload error "Allow access to file URLs" → owner enables `chrome://extensions` → ChatGPT 확장 → 세부정보 → "파일 URL에 대한 액세스 허용"; rerun only the icon step. Mention this up front so it doesn't block later.
   - `PENDING_CONFIRMATION` on "TOSS 광고대행 서비스 이용약관" → this is a new legal consent; get the owner's explicit OK in chat, then `codex_console.sh --resume <SESSION id> "승인: 계정 주인이 채팅에서 ... 동의를 명시적으로 승인했다 ..." <out>`. Use the session id, not `--last` (another Codex job may have started since). In workspace 35273 the consent is already given.
   - IAP "먼저 사업자 정보를 등록해 주세요" → owner must register the business (≈2 days review). Ship with purchases flagged off and tell the owner.
4. If the appName changed (fallback used), update every appName reference and any script that hard-codes `ait-build/<appName>.ait`.

### 3. Wire IDs and build
- Put `adGroupId` (`ait.v2.live.<16hex>`) / product IDs into the runtime config and flip the matching feature flags. Ship monetization behind flags with empty IDs until IDs exist.
- Rebuild with the project's release script if it has one (it should stamp the build and refuse a dirty tree; `.ait` packaging rebuilds WebGL, so smoke-test what you ship). Unity batchmode packaging: `AITConvertCore.DoExport(true, true, false, conf.productionProfile, "Build & Package", false, false)` — not the async menu method.
- Commit the config change and push before deploying, so the deployed build maps to a commit.

### 4. Test deploy and QR
`bash ~/.claude/skills/apps-in-toss-deploy/scripts/deploy.sh <ait-build dir> <app>.ait "test <sha>" [profile]`
- Prints `DEPLOY_URL intoss-private://<appName>?_deploymentId=...&host=appsInTossHost` and writes a QR png. Send the QR to the user (SendUserFile if available) — every deploy gets a new deploymentId, so resend each time.
- `ait deploy` always lands in the test (QR) environment; nothing becomes public.
- `Code: 4097` (이미 해당 앱 번들이 업로드되어 있어요) = this exact .ait was already uploaded. Reuse the earlier QR, or rebuild (new stamp) to get a new deployment.

### 5. Report
Short Korean summary: what was registered (appName/display name, ad group IDs), what deployed (commit, QR), and the exact owner-only items left (e.g. icon toggle, business registration for IAP, release fields like game rating). Don't list things Claude/Codex could still do — do them.

## Gotchas worth remembering
- `pnpm exec ait` dies without a TTY (`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`); `deploy.sh` calls `node_modules/.bin/ait` with `CI=true`.
- A key typed at deploy's interactive prompt isn't saved — `ait token add --api-key <key> <profile>`. Never echo keys into chat or logs.
- Codex reads repo AGENTS.md and stalls on workflow rules unless the prompt's first line tells it to ignore them (the template does).
- Ads work without a business registration until the workspace's accrued estimate hits ₩5,000 (then 5 business days to register). IAP needs business info first.
- Ad groups may sit in "구글 반영 중" for a while; ads may not serve immediately in the test build.
- Release (not this skill's job) needs owner-only fields: game rating proof, seal/signature, store links. See knowhow §6.
