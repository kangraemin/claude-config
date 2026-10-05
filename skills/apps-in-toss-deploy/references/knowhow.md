# Apps-in-Toss (앱인토스) deploy know-how: building, deploying with the CLI, and driving the console through Codex

Collected 2026-10-05 from this user's Claude Code sessions, Codex rollouts, project files and `~/claude-library`.
Secrets are redacted. "Owner's email" stands in for the real support address.

**Source keys** (used in brackets after each fact):
- `[SP]` screw-puzzle session `79fa62bd`, 2026-10-04 to 10-05 (나사톡톡 / appName `screw-toktok`). This is the session that first got the full flow working.
- `[SD]` spot-difference session `609cc2a4`, 2026-10-04 to 10-05 (오늘의 눈썰미 / `spot-difference-daily`).
- `[CP]` cat-petting session `7b1162c9`, 2026-10-04 to 10-05 (골골냥 / `golgol-nyang`), plus `cat-petting/docs/DEPLOY.md`.
- `[TW]` tax-watcher session `511faaac`, 2026-09-21 to 09-22 (deploying 어디썼 `seoultax`/`seoultaxdev` from seoul-expense-app).
- `[SE]` seoul-expense-app repo files (`package.json`, `granite.config.ts`, `.claude/CLAUDE.md`, `docs/RUN_LOCAL.md`, `qa/README.md`).
- `[CX]` Codex rollouts in `~/.codex/sessions/2026/10/05/` (the console runs for SP and SD).
- `[LIB:<file>]` `~/claude-library/library/api/apps-in-toss/<file>.md`, unless another path is given.

---

## 0. The whole flow at a glance

```
(1) Build the .ait          Unity SDK batchmode  |  granite: `ait build`
(2) Register the app        Console, once per app (Codex drives Chrome). The CLI cannot create apps.
(3) Register the API key    `ait token add --api-key <key> <profile>`, once per machine
(4) Test deploy             `ait deploy --profile <p> --location <file>.ait -m "<memo>"`
                            -> intoss-private://<appName>?_deploymentId=...&host=appsInTossHost -> make a QR
(5) Monetization (optional) Console: ad terms -> rewarded ad group -> adGroupId into the build -> rebuild -> redeploy
(6) Release (owner)         Console: fill the release fields -> 검토 요청하기 -> wait for approval -> press 출시
```
`ait deploy` always lands in the **test (QR) environment**. Only the console review and release step makes a build public. [SP: SDK `AppsInTossMenu.cs` comment; CP DEPLOY.md]

---

## 1. Build and package

### 1.1 Unity SDK (`im.toss.apps-in-toss-unity-sdk`)
- Install with the UPM git URL `https://github.com/toss/apps-in-toss-unity-sdk.git`. The SDK in use is 3.5.0, and its only dependency is `com.unity.nuget.newtonsoft-json`. [LIB:unity-sdk-haptic-docs-example-wrong-use-sdk-source]
- Supported Unity versions: 2021.3+. `package.json` declares `unityRelease 45f1`, but 2021.3.25f1 also imports, compiles and builds. [LIB: same]
- Editor menus: `AIT/Configuration`, `AIT/Deploy for Online Test`, `AIT/Deploy Release Candidate`, `AIT/Advanced/Build & Package` (`AppsInTossMenu.BuildAndPackage()`), `AIT/Clean`. [SP 2026-10-04, SDK source]
- Config asset: `Assets/AppsInToss/Editor/AITConfig.asset`. Its fields include `appName`, `displayName`, `version`, `primaryColor`, `iconUrl` and `productionProfile`. [CP DEPLOY.md, SP SDK grep]
  - `IsIconUrlValid()` requires the icon URL to start with http(s). Packaging still succeeds with an empty `iconUrl`. [SP, CP DEPLOY.md]
  - SDK `IsAppNameValid()` allows English letters, digits and hyphens. [SP SDK source]

**Batchmode packaging.** Don't call the SDK's `async void` menu method and then `-quit`, because that cuts the export short. Call the synchronous export instead. [CP DEPLOY.md]

```csharp
// Same path as AITDeployManager.RunBuildAndPackage (SDK 3.5.0)
var conf = UnityUtil.GetEditorConf();
conf.appName = Environment.GetEnvironmentVariable("AIT_APP_NAME") ?? "<console appName>";
conf.displayName = "..."; conf.primaryColor = "#RRGGBB"; conf.version = "x.y.z";
EditorUtility.SetDirty(conf); AssetDatabase.SaveAssets();
var r = AITConvertCore.DoExport(true /*build WebGL*/, true /*package .ait*/, false,
                                conf.productionProfile, "Build & Package", false, false);
// Check that r == SUCCEED AND that ait-build/*.ait exists, then EditorApplication.Exit(0/1)
```
- Simpler variant that also works: `AITConvertCore.DoExport(buildWebGL: true, doPackaging: true, cleanBuild: true)`. [SP `Assets/Scripts/Editor/AitBuild.cs`]
- Reflection variant, which keeps `compile-check` working before the SDK assembly loads: `spot-difference/Assets/Scripts/Editor/AitPackaging.cs`. [SD]
- Command: `AIT_APP_NAME=<appName> /Applications/Unity/Hub/Editor/2021.3.25f1/Unity.app/Contents/MacOS/Unity -batchmode -quit -projectPath . -buildTarget WebGL -executeMethod <Ns>.AitPackaging.Build -logFile Logs/ait.log`. [SP, SD `tools/unity.sh ait`]
- Output: `ait-build/<appName>.ait`. The file is named after the appName, so if the appName changes, update scripts that hard-code the path (SD `tools/release.sh` broke this way). Example sizes: 2.9–6 MB for the screw puzzle and 11–15 MB for cat-petting. [SP, SD, CP]
- **`.ait` packaging rebuilds WebGL.** The wasm/data md5 inside the `.ait` differ from `Build/WebGL`, so a smoke test on `Build/WebGL` does not cover the binary you ship. Put a release stamp (`<sha>-<timestamp>`) into both builds, compare them, and refuse to release from a dirty tree (`git status --porcelain` including untracked files and `ProjectSettings/` defines such as `AIT_SDK`). [LIB:../tooling/unity/ait-packaging-rebuilds-webgl-so-smoke-tested-binary-is-not-shipped, SD `tools/release.sh`]
- The SDK `productionProfile` changes templates, compression and Data Caching. cat-petting restores its own settings after `unity.sh ait`. [CP DEPLOY.md C5]
- The uncompressed bundle must be ≤100 MB, or the app shows a white screen on memory overflow. Landscape games can't be tested in the sandbox. [LIB:unity-sdk-games-vs-nongame-constraints]

### 1.2 Granite / React Native web mini-app (seoultax)
- `granite.config.ts`: `defineConfig({ scheme: 'intoss', appName, plugins: [appsInToss({ brand: { displayName, primaryColor, icon } })] })`. `brand.icon` must be a string URL or data URI; `require()` doesn't work. [SE, LIB:../tooling/granite-rn/brand-icon-string-url-only-and-no-native-splash-api]
- **appName = console app name = scheme path (`intoss://<appName>`). All three must match.** Otherwise the sandbox shows 404 or "스키마를 여는데 실패". [SE `docs/RUN_LOCAL.md`]
- `ait build` reads the config and builds two RN targets (0.84.0 and 0.72.6). It prints `deploymentId: ...` and writes `<appName>.ait` in the repo root. [TW 2026-09-22]
- Dev and prod run as **two separate console apps** (`seoultaxdev` and `seoultax`), switched by `APP_ENV` in `granite.config.ts`:
  `"deploy:dev": "... APP_ENV=dev ait build && ait deploy --profile dev --location ./seoultaxdev.ait"`,
  `"deploy:prod": "... APP_ENV=prod ait build && ait deploy --location ./seoultax.ait"` (no `--profile`, so it uses `default`). [SE `package.json`, TW]
- Env values injected with `@granite-js/plugin-env` are fixed at build time; changing one means rebuilding. [SE `.claude/CLAUDE.md`]
- Vite plus `@apps-in-toss/web-framework` is the officially supported path. Next.js has no official example. Non-game apps must use TDS. [LIB:nextjs-not-in-official-examples-vite-standard]

---

## 2. The `ait` CLI

### 2.1 Where it lives (Unity projects)
- The Unity SDK installs its own Node and pnpm at `~/.ait-unity-sdk/nodejs/v24.13.0/darwin-arm64/bin/{node,pnpm}`, and the CLI at `<project>/ait-build/node_modules/.bin/ait` (Apps in Toss CLI 3.5.0). Use this copy rather than a fresh `npx ait`. [CP DEPLOY.md, SD 2026-10-04]
- Granite projects: `npx ait ...` from the repo, where the CLI is a dev dependency. [TW]

### 2.2 The pnpm TTY problem
- `pnpm exec ait ...` inside `ait-build/` reruns `pnpm install` as a dependency check. In a shell with no TTY (Claude Code's Bash), it dies with `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`. [SP 2026-10-04 17:01, SD 17:11]
- Fix A (used in SP for every deploy): `export CI=true PATH="$PWD/node_modules/.bin:$HOME/.ait-unity-sdk/nodejs/v24.13.0/darwin-arm64/bin:$PATH"; pnpm exec ait deploy ...`
- Fix B (SD, in the library): skip pnpm and run `./node_modules/.bin/ait deploy ...` with the SDK Node on PATH. [LIB:ait-deploy-4031-means-app-not-registered-and-pnpm-no-tty]
- Add `< /dev/null` and `timeout 300..600`. Strip ANSI codes from the output: `sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g'`. [SP, SD]

### 2.3 Commands (from `ait --help`, CLI 3.5.0)
```
ait token add [--api-key <key>] [profile]     # stores the key in ~/.ait/credentials (JSON keyed by profile, e.g. {"dev":…, "default":…})
ait token remove [profile]
ait build                                      # reads apps-in-toss.config, builds a .ait
ait deploy [--api-key] [--workspace(deprecated)] [--profile] [--base-url] [--location] [--scheme-only] [-m|--memo]
ait migrate [--dry-run] [target]
```
- `--profile` defaults to `default`. Key lookup order: the saved token for the profile first, then `--api-key`. [SD `ait deploy --help`]
- `--location` is optional; without it the CLI uses the first `.ait` in the package root. `--scheme-only` prints only the intoss-private scheme. `-m` takes up to 1000 characters. [SD]
- **The CLI has no command to create an app.** Apps are created in the console. [LIB:ait-deploy-4031…]

### 2.4 API key
- Where to issue it: console `apps-in-toss.toss.im` → choose the **workspace** → left menu "키" → 콘솔 API 키. This is a workspace-level menu, not inside an app. [LIB:ait-deploy-interactive-key-not-persisted, TW 2026-09-22]
  - Reported but not verified: the key can be scoped to all apps or to specific apps. [TW, from web search]
- **A key typed at the interactive deploy prompt is used once and not saved.** `~/.ait/credentials` stays empty. Save it with `ait token add --api-key <key> <profile>`. The profile name must match `--profile` in the scripts. [TW, LIB:ait-deploy-interactive-key-not-persisted]
- If a key does get pasted into chat, rotate it afterwards. To type a key into a waiting prompt without echoing it: `tmux load-buffer <file>; tmux paste-buffer -t <session>; tmux send-keys Enter`, then delete the temp file. [TW]
- The current machine already has `dev` and `default` profiles for workspace 35273. Check with `python3 -c "import json;print(list(json.load(open('$HOME/.ait/credentials'))))"`, which prints names only. [TW, CP 2026-10-05]
- Community reports: a re-issued key can still return HTTP 403, usually because of workspace or app scope. [LIB:ait-deploy-interactive-key-not-persisted]

### 2.5 Deploy, deploymentId and the QR link
```bash
cd ait-build
export CI=true PATH="$PWD/node_modules/.bin:$HOME/.ait-unity-sdk/nodejs/v24.13.0/darwin-arm64/bin:$PATH"
timeout 600 pnpm exec ait deploy --profile default -m "[Test] <app> v0.x <what changed>" 2>&1 \
  | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' | grep -E "intoss|완료|오류|Code" | tail -5
```
Success output [SP 2026-10-05 01:26]:
```
◇  screw-toktok 배포가 완료되었어요
│  intoss-private://screw-toktok?_deploymentId=01a109aa-…&host=appsInTossHost
```
- Make a QR: `npx --yes qrcode -w 600 -o test-qr.png "intoss-private://<appName>?_deploymentId=<id>&host=appsInTossHost"` (Python `qrcode` also works). Scan it with the phone camera or the Toss app. Opening the link on an iPhone launches Toss straight into the test build. [SP, TW]
- In the console the build appears under 앱 출시 → version `YYYYMMDD-N` (e.g. `20261005-1`) → 테스트(QR), with SDK 3.5.0 and status **검토 필요**. [SP via Codex 2026-10-05 01:35]
- Every redeploy issues a new deploymentId and link, so send a new QR each time. [SP v0.2–v0.4]
- Sandbox (local dev, no QR): the Toss sandbox app (`com.vivarepublica.ent.cash.test`) needs a Toss **business** account login. Enter only the path after the fixed `intoss://` prefix in the scheme field. `xcrun simctl openurl intoss://…` does not work. [SE `qa/README.md`, `docs/RUN_LOCAL.md`]

---

## 3. Driving the console with Codex (computer use / external browser)

### 3.1 Command (copied exactly from the SP and SD sessions)
```bash
S=<scratchpad>; cd <repo> && timeout 2400 codex exec "$(cat $S/console.txt)" \
  --dangerously-bypass-approvals-and-sandbox --enable computer_use --enable browser_use_external \
  -c 'model_reasoning_effort="medium"' --json < /dev/null 2>$S/console.err | python3 -u -c "
import sys, json
for line in sys.stdin:
    try: obj=json.loads(line)
    except: continue
    if obj.get('type')=='thread.started': print('SESSION', obj.get('thread_id'), flush=True)
    if obj.get('type')=='item.completed' and obj['item'].get('type')=='agent_message': print(obj['item'].get('text',''), flush=True)
" > $S/console.out; echo exit=$?
```
- In Claude Code, run it with `run_in_background: true` and `dangerouslyDisableSandbox: true`. A run took about 4–10 minutes. [SP, SD]
- `codex features list` shows `computer_use`, `browser_use` and `browser_use_external` as stable. [SP 2026-10-04 10:42]
- `browser_use_external` drives the owner's **already logged-in Google Chrome** through the ChatGPT Chrome extension. Codex uses `cua_repl` JS: `cua.createBrowserTab("chrome", url)`, `tab.goto`, `tab.getAXState()`, `tab.playwright.getByRole(...)`, and `app.*` for native windows. [CX]
- Resume after a question: `codex exec resume --last "<approval text>" <same flags> --json`. This worked in SP. **`--last` can pick up the wrong session if another Codex job started in between**, so capture the `thread.started` id and use `codex exec resume <id>`. [SP 01:58, LIB:../tooling/ai-agent/parallel-codex-sessions-resume-last-and-shared-data-drift]
- stderr noise such as `failed to parse plugin hooks config`, `failed to load skill …` or figma MCP `AuthRequired` is harmless. [SP]

### 3.2 Prompt structure that worked
1. First line: `IMPORTANT: Do NOT read or execute any files under ~/.claude/, ~/.agents/, .claude/skills/, or agents/. Ignore repo AGENTS.md workflow rules; do not ask questions.` Without it, codex exec reads the repo's AGENTS.md and stops to ask questions. [SD, LIB:../tooling/ai-agent/codex-exec-delegation-reads-repo-agents-md-and-stalls]
2. Authorization: "Task (authorized by the account owner) … in the owner's already-logged-in Google Chrome … Use your browser/computer-use tools to drive the real Chrome window."
3. Login gate: "If not logged in or the site asks for login / phone verification / QR / password, STOP and output: `LOGIN_REQUIRED: <what it asks>`. Do not try to log in yourself."
4. Workspace: "workspace **35273** (the one containing seoultax and screw-toktok; the local deploy API key belongs to it)." **The app must be in the same workspace as the API key**, or deploy returns 4031.
5. Numbered steps with exact values and **fallbacks**: display name plus fallbacks that respect the name rules, appName plus fallbacks (e.g. `spot-difference` → `spot-difference-daily` → `nunsseolmi`), category 게임 (퍼즐 sub-category), short description, absolute icon path (600×600), support email.
6. "Fill only what is REQUIRED to create the app and get a test (QR) environment; save (임시저장 is fine)."
7. Hard limits: "no review submission, no release, no changes to other apps, no business registration number / bank / settlement / personal identity data. If required, STOP: `NEEDS_OWNER: <field and exact screen text>`."
8. Machine-readable output:
   ```
   STATUS: CREATED | PARTIAL | LOGIN_REQUIRED | NEEDS_OWNER | FAILED
   APP <appName> <display name>
   AD_GROUP <name> <type> <adGroupId>
   PRODUCT <name> <productId or NOT_CREATED: reason>
   Remaining required fields / blockers
   ```
9. Optional read-only audit run: "READ-ONLY task (enter nothing, save nothing, submit nothing) … list EXACTLY each field still required before 검토 요청/출시, grouped by screen". [SP console5]

Full prompts are in the SP transcript (`console.txt`, `console2.txt`, `console3.txt`, `console5.txt`) and `spot-difference/…/scratchpad/console_sd.txt`.

### 3.3 Console URLs (workspace 35273) [CX]
- App list / register: `/workspace/35273/mini-app`
- App home / build (bundles and versions): `/workspace/35273/mini-app/<appName>/home`, `/app-build`
- App info edit (release metadata): `/mini-app/<appName>/app-info`, `/meta/edit?step=1`, `/meta/edit?deploymentId=<id>&step=0`
- Ad groups: `/mini-app/<appName>/placement-group/list?tab=adUnitGroup`, create: `/placement-group/create`
- IAP: `/mini-app/<appName>/in-app-purchase/list`
- Business and settlement info: `/workspace/35273/partner-info` (내 정보)
- Notices: `/mini-app/<appName>/notice/<id>`

### 3.4 Registration form rules (checked against the form validation, 2026-10-05)
- **Display name: at most 10 characters excluding spaces, and no hyphen.** "나사톡톡: 나사 풀기 퍼즐" and "나사톡톡 - 나사 풀기 퍼즐" were both rejected; "나사톡톡" passed. [SP, LIB:console-game-registration-rules-and-ads-without-business]
- **appName must be unique across all workspaces.** `spot-difference` was "already in use", which is also why deploying under that name gave 4031. Hyphens are fine in the appName (`screw-toktok`). [SD 2026-10-05 05:16]
- To create the app you need only the name, appName, type (게임) and description. Everything else can wait until release. [SP]
- **Support email (고객문의 이메일) is a required field and is shown publicly.** Ask the owner which address to use; SP and SD used the owner's email. Saving shows "임시저장 했어요". [SP 01:35–02:04]
- **Icon: exactly 600×600 px.** Error text: "600px * 600px 사이즈의 이미지만 등록할 수 있어요." 1024 and 512 are rejected. Resize with `Image.open('icon-1024.png').resize((600,600), Image.LANCZOS)`. There is a separate dark-mode logo slot, also 600×600. [SP, CX]
- Release images: thumbnail **1932×828**; screenshots **portrait 636×1048, at least 3**, or **landscape 1504×741, at least 1**. [CX AX tree 2026-10-05]
- The QR test screen needs an uploaded `.ait`; it stays empty until the first `ait deploy`. [SD Codex]

### 3.5 Icon upload: the Chrome file-URL permission
- `tab.playwright.waitForEvent('filechooser')` → `chooser.setFiles([...])` fails with:
  `To enable file upload, open chrome://extensions, click Details under the ChatGPT browser extension, and enable "Allow access to file URLs."` (see developers.openai.com/codex/app/chrome-extension#upload-files). [SD/CX 2026-10-05 14:13]
- **Owner fix:** `chrome://extensions` → ChatGPT extension → 세부정보 → enable "파일 URL에 대한 액세스 허용". Then rerun.
- What worked in SP without that toggle: Codex clicked the button, the **native macOS file dialog** opened, and Codex drove it as an app via computer_use: `app.pressKey('super+shift+g'); app.paste('<abs path>'); app.setValue(<field>,'<abs path>'); app.pressKey('Return')`, then clicked save. In SD the native-dialog retry still failed, so ask the owner for the toggle up front. [CX 10:38 vs 14:13]

### 3.6 Ad terms and ad groups
- Before the first ad group, the 인앱 광고 menu shows "인앱 광고를 등록하려면 약관에 먼저 동의해 주세요" with a required **"TOSS 광고대행 서비스 이용약관"** and a "동의하고 시작하기" button. [SP]
- **Codex's browser policy asks for confirmation at the moment of consent even when the prompt says the owner approved.** It stopped with `STATUS: PENDING_CONFIRMATION`. Fix: get explicit approval from the owner in chat, then `codex exec resume … "승인: 계정 주인이 채팅에서 'TOSS 광고대행 서비스 이용약관' 동의를 명시적으로 승인했다 … '동의하고 시작하기'를 눌러…"`. That worked. [SP 01:42 → 02:04]
- The consent appears to be per workspace: the second app in workspace 35273 (SD) created its ad group with no consent prompt. [SD 05:18, observed]
- Rewarded ad group form: name, reward unit (text), reward amount (number), type 리워드형. SD example: name 힌트, unit 힌트, amount 1. [CX]
- **adGroupId = the `groupId` query parameter in the console URL** after creation: `…/placement-group/list?tab=adUnitGroup&groupId=ait.v2.live.<16 hex>`. Format: `ait.v2.live.xxxxxxxxxxxxxxxx`. The detail view may not show the ID while the status is "구글 반영 중", so ads may not serve until the Google sync finishes. [SP 02:04, CX]
- Code: `AIT.LoadFullScreenAd(adGroupId, …)` and then `AIT.ShowFullScreenAd(adGroupId, …)`. Reward only on `userEarnedReward`; close on `dismissed` or `failedToShow`. Use a separate group per placement (SP has "이어하기" and "코인2배"). [SP TossPlatform.cs, LIB:rewarded-ad-and-share-apis]

### 3.7 In-app purchase products
- **You can't create IAP products until business info is registered.** The IAP list page shows: "먼저 사업자 정보를 등록해 주세요 검토는 약 2일 소요되며, 이후 정산 정보 등록 단계로 넘어가요." Codex stopped there with NEEDS_OWNER as instructed. [SD 2026-10-05 05:18]
- Business registration (`/partner-info`) needs a 10-digit business registration number. Settlement info can be added only after the business info. This is owner-only data; Codex must not enter it. [SP console2, CX]
- Product limits: up to 80 for games, 30 for non-games. Digital goods must use in-app purchase. [LIB:unity-sdk-games-vs-nongame-constraints]
- Unity IAP: `ProcessProductGrant` is a **synchronous bool** callback. On startup, query pending **and** completed/refunded orders. Grant records should live on a server. [LIB:unity-iap-sync-approval-needs-completed-order-recovery]
- Ship monetization **flagged off with empty IDs** (`PlatformConfig.json` flags plus `rewardedAdGroupId` / `chapterPackProductId` / SKU slots), then fill the IDs once the console issues them and rebuild. [CP, SD]

### 3.8 Console notices seen (2026-10-05)
- SDK: "SDK 3.x 미만 버전을 사용 중인 미니앱은 2026년 10월 5일부터 콘솔에서 신규 등록이 제한돼요." / "Unity SDK : 별도의 설정 변경 없이, git 패키지를 3.x 버전으로 업데이트하면 전환이 완료돼요." / "SDK 3.x 출시 후에는 SDK 2.x로 롤백할 수 없어요." (notice 53009) [SP]
- Existing apps keep showing "활성, 전환 지표를 설정해 주세요". If no metric is registered, the app is never evaluated for the 추천 tier under the exposure policy that starts 2026-10-22. [SP, TW, LIB:exposure-policy-tiers-require-metric-registration]

---

## 4. Errors and fixes

| Symptom | Cause | Fix | Source |
|---|---|---|---|
| `앱이 없거나 앱 정보에 접근할 수 있는 권한이 없어요 (Code: 4031)` → `Canceled` | No app with that appName in **the API key's workspace**: not registered yet, the appName belongs to someone else, or the key has no rights to that app (e.g. `whereismytax`) | Register the app in the same workspace (Codex), set appName in AITConfig/granite config, rebuild, redeploy. A valid key does not mean a valid app | SP, SD, SE `.claude/CLAUDE.md`, LIB:ait-deploy-4031… |
| `이미 해당 앱 번들이 업로드되어 있어요 (Code: 4097)` | Redeploying the identical .ait | Reuse the previous QR, or rebuild for a new bundle | SD 2026-10-05 |
| `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY` | `pnpm exec` reruns `pnpm install` with no TTY | `CI=true`, or run `./node_modules/.bin/ait` directly | SP, SD |
| Deploy asks for the key on every run | Interactive key isn't saved | `ait token add --api-key <key> <profile>` | TW |
| HTTP 403 with a new key | Workspace or app scope (community report) | Check the workspace and key scope | LIB |
| Codex `fileChooser.setFiles failed … Allow access to file URLs` | ChatGPT extension lacks file-URL access | Owner enables it in `chrome://extensions`; or Codex drives the native dialog (⌘⇧G, paste path) | SD, CX |
| Codex `STATUS: PENDING_CONFIRMATION` on the ad terms | Browser tool needs consent at the moment of clicking | Get explicit approval in chat, then `codex exec resume` with the approval quoted | SP |
| Name rejected | Over 10 characters excluding spaces, or contains a hyphen | Shorter name; the subtitle goes in a separate field | SP |
| Icon rejected "600px * 600px …" | Wrong size | Resize to exactly 600×600 | SP |
| IAP "먼저 사업자 정보를 등록해 주세요" | No business info | Owner registers the business (about 2 days of review), then settlement info | SD |
| Ads don't show right after creation | Ad group still "구글 반영 중" | Wait; test later | SP |
| `LOGIN_REQUIRED` | Chrome not logged in / phone verification | Owner logs in; Codex must not try (didn't happen in SP or SD) | SP prompt design |
| Driving Chrome from Claude directly fails | `osascript` "보조 접근이 허용되지 않습니다 (-25211)"; Chrome "Apple Events의 자바스크립트 허용" is off; gstack headless browser has no login | Use Codex `browser_use_external` (the owner's logged-in Chrome) | TW 2026-09-22 |
| Sandbox 404 / "스키마를 여는데 실패" | appName ≠ console name ≠ scheme; or app not registered | Make all three identical | SE `docs/RUN_LOCAL.md` |

---

## 5. Monetization rules

- **Ads without a registered business:** the latest console notice (52685) says "워크스페이스의 누적 예상수익이 5천원 미만인 경우, 사업자 및 정산정보 등록을 유예할 수 있어요." Once the workspace's accrued estimate reaches 5,000 KRW, business and settlement info must be registered and approved **within 5 business days**, or the mini-app stops being shown. You can get ad IDs before then. This corrects the older note "인앱광고는 사업자등록 필수". [SP, LIB:console-game-registration-rules-and-ads-without-business]
- Prerequisite for ads: accept the TOSS 광고대행 서비스 이용약관. This is the account owner's decision, so get explicit consent first. [SP]
- **IAP needs business info first**: about 2 days of review, then settlement info. [SD]
- Settlement deductions from older docs: about 30% of ad revenue as operating costs plus a 15% Apps-in-Toss fee; settlement info review takes 2–3 business days. [LIB:rewarded-ad-and-share-apis]
- Share APIs (`getTossShareLink`, `share`) don't need a business. They count only "shared", not whether a friend actually came in. [LIB:rewarded-ad-and-share-apis]
- Push notifications: functional ones only. Promotional push ended 2026-10-01. [LIB:unity-sdk-3-5-limits…, SP research]

---

## 6. Test deploy vs release review

- **Test deploy** = `ait deploy`. It goes live in the QR/test environment right away, with no review. Status 검토 필요 means uploaded but not submitted. [SP, TW]
- **Release** = a console UI action by the owner: version list → choose the bundle → 검토 요청하기 → approval → press 출시. Only one version is live at a time, and a new release replaces the old one. [TW 2026-09-21]
  - seoultax history: builds `20260917-11` and `-12` were **rejected for "first entry over 20 seconds"**. Enabling minify (`build: { esbuild: { minify: true } }`), cutting first-load API calls from 521 to 1 and shortening the splash got `-13` approved. Submitted 9/17, approved 9/21: **about 4 days**. [TW, SE granite.config.ts comment]
- **Release-only required fields** (empty fields don't block test deploys) [SP console2/console5 2026-10-05]:
  - App info: English app name, subtitle, detailed description, support email, release notes, sub-category, app logo (600×600, plus a dark-mode logo), search keywords, thumbnail 1932×828, screenshots (see 3.4).
  - **Game rating (게임 등급)**, two routes:
    - GRAC certificate PDF.
    - Store self-rating (IARC). This needs the **URL of a game actually released on a store**; a finished questionnaire is not enough.
    - Fields: 앱마켓 게임등록자명, 대표자명, 주소, 전화번호; 자체등급분류 등록자명 (Google Play developer name); 자체등급분류사업자명 (the market, e.g. 구글); 등급분류일자; 등급분류번호; 이용등급 (전체/12/15/청소년 이용불가/평가용); 내용정보 (multi-select); **대표자 인감 또는 사인 이미지**; 게임 주요화면 1 and 2 as pairs (store build vs Apps-in-Toss build, unedited originals).
  - Final checkboxes (all required): 앱인토스에서 오픈할 수 있는 서비스 / 환전·현금화·자금세탁 우려 없음 / 인허가·등록·신고 완료 / 부정행위·위법 없음 / 위반 시 파트너사 책임.
  - "검토 요청하기" stays disabled until all of these are filled.
- Game launch checklist: https://developers-apps-in-toss.toss.im/checklist/app-game (launch, sound, Safe Area, data persistence, ads and payments). [SP console5]
- Rating guides: https://developers-apps-in-toss.toss.im/guide/operation/console-workspace#id-5-3, https://toss.im/apps-in-toss/blog/self-rated_game_distribution, https://toss.im/apps-in-toss/blog/game_rating_classification. [SP console5]
- Critical path for a game release: with the store route, a new personal Google Play account must run a closed test (12 testers for 14 days) before production. Start that early. [LIB:game-release-needs-rating-proof-store-iarc-route-means-play-closed-test-first]

---

## 7. Who does what (to put in the skill)

| Step | Claude | Codex (Chrome) | Owner |
|---|---|---|---|
| Build `.ait`, `ait deploy`, QR | ✅ | | |
| Register app, upload icon, set email, ad group | | ✅ | Approves terms consent and email choice; enables the file-URL toggle if uploads fail |
| Read the adGroupId (URL `groupId`), put it in the config, rebuild, redeploy | ✅ | reports ID | |
| Business number, settlement / bank info, 인감/사인, game rating certificate, store release | | ❌ never | ✅ |
| 검토 요청 / 출시 | | ❌ hard limit | ✅ |
| Issue the API key | | possible but not done | Done once; saved per profile |

Watch for one thing in this setup: a Claude Code Stop hook keeps asking for "커밋하고 푸시" while Codex is still running in the background. Commit only after the Codex result has been applied. [SD]
