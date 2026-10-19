---
name: chrome-direct
description: Run repeated web actions in the owner's real Mac Chrome without an LLM, using AppleScript + JS scenario scripts (Gmail search/send/codes/spam, Google Forms read/fill, Apps-in-Toss console builds/ad groups/review request, result-page checks). Use this BEFORE handing a Chrome task to Codex; the script falls back to Codex (codex_console.sh) on its own when it fails.
---

# chrome-direct

Scripts in `scenarios/` drive the real Chrome (`chromectl.py`, AppleScript `execute javascript`) in a **new tab** of the profile you pick (default `Profile 1` = remin1994 Google + Toss Business). They close that tab when done.

```
cd ~/.config/claude-accounts/personal/skills/chrome-direct/scenarios
python3 <scenario>.py ... [--profile "Profile 1"] [--no-fallback] [--codex-out f] [--keep-tab]
```
Output: one JSON object, then a last line `RESULT: <STATUS> ...`. Exit codes: 0 ok, 1 failed (after the Codex fallback), 2 blocked (login needed, already submitted, lock held, button disabled). **There is no fallback on exit 2.** Pass the reason to the user or the board card.

## Scenarios

| Script | What it does | Kind | Verified |
|---|---|---|---|
| `google_account.py [--expect remin1994@gmail.com]` | Which Google account is signed in on this profile | Read | yes |
| `gmail_search.py "<query>" [--limit N] [--open N] [--proof x.pdf]` | List search results / open one thread (`in:sent`, `in:spam` also work) | Read | yes |
| `gmail_mailcheck.py [--days 5] [--out x.md] [--open-bodies]` | Contest-mail sweep (3 queries, ad/key classification, codes masked) | Read | yes |
| `gmail_code.py [--from x] [--link pattern]` | Verification code (`CODE n`) or link (`LINK url`) from recent mail | Read | yes |
| `gform_read.py <url> [--skeleton a.json]` | Every page, question, and required flag of a Google Form; checks for closed form or existing response | Read | yes |
| `gform_fill.py <url> answers.json [--submit --contest-id id]` | Fill a form. Dry-run by default. File questions go to Codex | Submit | no |
| `gmail_send.py --to --subject --body-file [--attach f]... [--submit --contest-id id]` | Send mail (SMTP if `GMAIL_APP_PASSWORD` is set, otherwise the web compose window). Checks Sent first to avoid duplicates | Submit | dry-run only |
| `ait_builds.py [--apps] [app] [--reject-reason ver]` | Apps-in-Toss app list, version table, review status, rejection reason | Read | yes |
| `ait_adgroups.py <app> [--name n]` | Ad groups and `AD_GROUP <app> <name> <type> <adGroupId>` | Read | yes |
| `ait_adgroup_create.py <app> --name --type 리워드/전면형/배너 [--unit --amount] [--submit]` | Create an ad group. If the name already exists it only prints the ID. Stops at the terms screen | Submit | EXISTS path only |
| `ait_review_request.py <app> --version v [--notes ..] [--submit]` | Request review. Dry-run reports whether the button is enabled. Never presses release, cancel, or rollback | Submit | dry-run only |
| `toss_business_login.sh send` → `code <6자리>` (`resend`) | Toss Business / Apps-in-Toss console login when `ait_*` returns LOGIN_REQUIRED. `send`: Codex fills phone login (SKT 알뜰폰, name, birth+phone from 제천 `build_application.py` INFO, RRN back first digit 1) and requests the SMS. Ask the owner only for the 6 digits. `code`: types them by JS (**2-minute limit, Codex is too slow**) and picks the remin1994 account. `TOSS_LOGIN_OUT` = marker dir | Login | yes (10/19) |
| `naver_login.py [--qr --notify] [--otp N]` | Naver login check (myInfo redirect). Logged out → `--qr --notify` sends the QR (800px) + the number to pick in the Naver app straight to the owner's Telegram, waits until scanned (3 rounds × 3 min) and sends '로그인 확인됨'. Run it in the background and start the next step as soon as it prints `RESULT: OK` — don't make the owner wait or ask; `--otp` uses the app's one-time number. Turns on '로그인 상태 유지'. No passwords | Login | yes (QR, 10/19) |
| `page_check.py <url> --kw a --kw b [--name]` | Keyword lines and links on any page; own name (also masked forms) shown as `[이름]` | Read | yes |
| `announce_check.py [--days N] [--only id]` | Opens result pages for contests in `_radar/announce.json` whose announce date has passed. Hints only | Read | yes |

## Submit-type rules
- No `--submit` means **dry-run**: fill in, but do not press the final button.
- With `--contest-id`: checks `.done` SUBMITTED, `handled/`, and db `contests` status=submitted, then runs `mkdir _radar/jobs/<id>.submit.lock`. If either check fails, it does not submit (exit 2).
- If the result can't be confirmed after pressing, the script stops with `UNCONFIRMED` (exit 2). **Never press again.** Check with the read scenarios first.
- Personal info comes in only as `{name} {phone} {email} {address} {birth} {birth6} {rrn7} {affiliation}` placeholders (`_common.personal_info()`, extracted by pattern from 제천 `build_application.py`). Never print it. Passwords come only by env name.
- Terms consent, payment, release, and review-request screens stop with `NEEDS_OWNER` unless the call explicitly asks for that step.

## Prerequisites
- Chrome menu: View > Developer > Allow JavaScript from Apple Events (pref `browser.allow_javascript_apple_events`).
- `shot`/`--proof` needs Screen Recording permission for the terminal. Codex fallback needs tmux and `~/.codex/plugins/cache/openai-bundled/chrome`.
- Don't touch other sessions' tabs (e.g. X sign-up in Profile 4). The scripts only open and close their own tabs.

## Pitfalls (already handled, keep in mind when adding scenarios)
- Redeclaring a page-global `const` throws an error. Always run JS with `chromectl.js_json`, which wraps it in an IIFE.
- Google Forms buttons and radios ignore a bare `.click()`. Use `__press` (pointer→mouse→click). For inputs, use `__setv` (native setter + input/change).
- With two Chrome instances running, AppleScript attaches to the one with 0 windows. Open new tabs through the Chrome binary with `--profile-directory` (`new_tab`), not `open -na`.
- Gmail URLs use the `mail.google.com/mail/?authuser=<email>#search/...` form. `/mail/u/<email>/` gives "Temporary Error". Gmail turns spaces in the hash into `+`.
- Cross-origin iframes (file pickers and the like) can't be reached with JS. Use `rclick` (cliclick) or Codex.
- AppleScript JS can't see page globals declared in page scripts (`makeApiUrl`, `fileInfoArr`, inline functions → ReferenceError/undefined). Drive the page through DOM events (`press`, native `change`/`input`), or replay what the function does (e.g. set `form.action` and call `submit()` yourself).
- File upload without a file dialog: push the file as base64 in ~400KB chunks into `window.__b` (it persists across calls in the same tab), then build a `File` → `DataTransfer` → `input.files`, and dispatch `change`. Fetching from a local http server is blocked by Chrome (Private Network Access). After uploading, compare the server copy against the original with `crypto.subtle` SHA-256 (eyedesignwear, 10/18).
- `rclick` clicks the tab that is active in that window. If another session has a different tab active in the same window, the click lands on its page. Set `active tab index` first, or use only DOM events. `window.open` popups (NICE identity check) do open with `rclick`.
- The claude.ai board/list pages don't work with this approach because the profile's login doesn't match (Profile 1 is the company account). Keep using `_radar/board/healthcheck.py`.
- **Google re-login (passkey) is NOT a user step.** When the account chooser shows every account "로그아웃됨", click the account (`[data-identifier="<email>"]`), click the page's `계속`, and a native macOS "로그인 — 패스키를 사용하여… 로그인하겠습니까?" sheet appears. Pressing its blue `계속` signs in **without fingerprint** (passkey from the Passwords app). The sheet is not in the DOM, has no AX children (`entire contents` = 0), and `keystroke return` does nothing → click it with `cliclick c:X,Y`. Coordinates: Chrome window position/size from System Events (`position of window 1` e.g. 0,30 / 1920x967); `shot` PNG is 3840 px wide → shown at 2000 → points = shown_x × 0.96, y = window_top + shown_y × 0.96 (계속 was 1157,631). It times out in ~1 min ("요청 제한 시간 초과") → close that error sheet the same way (`position of window "문제가 발생했습니다"` + offset), press the page's `다시 시도`/`계속`, and click again right away (2026-10-19).
- Never take Google logins to another browser or a Playwright profile. Anthropic API calls are not allowed.

## Adding a scenario
Import `parser/tab/js/poll/emit/run/Blocked` from `_common`. `run(main, args, task)` hands the same goal to Codex when an exception occurs. Write `task` as a full instruction Codex can act on by itself, including read-only/no-click rules.
