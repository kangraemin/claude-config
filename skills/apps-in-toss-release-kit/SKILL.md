---
name: apps-in-toss-release-kit
description: Builds everything an Apps-in-Toss (앱인토스, 토스 미니앱) game needs for the release (출시) application, ready to paste or upload — store text (앱 이름, 영어 이름, 부제, 상세 설명, 키워드, 출시 노트), thumbnail 1932×828, portrait screenshots 636×1048, and the game-rating (게임 등급, GRAC 등급분류) submission pack: a recorded gameplay video and a 게임물 설명서. Use this whenever the user says things like "출시 자료 만들어", "스토어 이미지/스크린샷 만들어", "썸네일 만들어", "등급 신청 자료", "게임 영상 찍어", "검토 요청 전에 뭐 필요해", or asks to prepare any Apps-in-Toss game for release — even for a different game project than the one in the current directory, and even if they only mention one of the pieces.
---

# Apps-in-Toss release kit

Goal: the owner only has to paste and upload. Everything Claude can produce from the repo is produced, checked by
eye, committed, and sent; only legally-owner items are left (support email, rating application itself, seal/sign,
checkboxes, 검토 요청). The owner dislikes long to-do lists — end with a 3-line "what you do" summary.

Test deploys, console registration and the release procedure itself live in the `apps-in-toss-deploy` skill. Console
field specs, rating routes and both document templates: `references/templates.md` (read it before writing text).

## Output layout (in the game repo)
```
docs/store/
  LISTING.md                 # paste-ready console text
  thumbnail_1932x828.png
  screenshot_1..N.png        # 636×1048, N ≥ 3 (aim for 5)
  rating/GAME_DESCRIPTION.md # 게임물 설명서
  rating/gameplay.mp4        # ~30 min summary for a GRAC direct application (see below)
```

## Steps

### 1. Learn the game from the repo (don't ask the owner)
Read README/PRODUCT/PLAN docs, the display name in `granite.config.ts` or the Unity AIT config, and the **actual
monetization flags** (ads/IAP enabled?). Text and the rating form must describe the build that will be submitted:
an ad or random reward that is shipped but not declared is a real problem for the owner.

### 2. Get real captures
Prefer existing ones (gate/QA screenshot folders, smoke-test outputs) from the latest build. Otherwise capture with
Playwright at 390×844, device_scale_factor 2. Pick screens that show: home/start, mid-play, a success moment,
result/progression, collection/meta. Avoid screens that spoil answers or show debug UI. Look at a contact sheet
before choosing.

### 3. Store images
Write a `store_spec.json` (format in the script docstring) and run
`python3 ~/.claude/skills/apps-in-toss-release-kit/scripts/store_images.py store_spec.json`.
Colors: take the brand primary from the config and the app's own background. Captions: 2 short lines per shot in
해요체, each describing what that screen really shows. Then **Read the thumbnail and a sheet of the screenshots** —
check nothing overlaps or is clipped at the edge, text is inside the frame, and captions match their screens.
Copy the spec into the repo next to the images so they can be regenerated.

### 4. Gameplay video for the rating
The reviewer needs to see the real game played start to finish, not a trailer. For a GRAC direct (일반) application
the expected material is a **~30-minute summary video** covering the game broadly, including the strongest content in
each of the 5 criteria (ads, rewards, anything near violence) — a 1-minute clip is too short. Build it by
concatenating many automated sessions with different content (days/levels/modes), not one run repeated.
- If the repo has a play automation (smoke test, e2e), add a video option to it rather than writing a new player:
  Playwright `record_video_dir` + `record_video_size` **equal to the CSS viewport** (a larger size with dpr 2 makes
  frames flip between full and quarter size whenever `page.screenshot` runs). Slow taps to 1.5–2 s so a human can
  follow, hold the final screen ~2.5 s, and print the elapsed time at the moment to cut.
- **Sound is required** — the reviewer judges sound too, and Playwright's video is silent. Inject
  `scripts/webaudio_tap.js` with `page.add_init_script(path=...)` before `goto`, and at the end call
  `page.evaluate("window.__tapStop()")` → base64 webm + `startedAt` ms; mux with `finish_video.py --audio a.webm
  --audio-offset <startedAt/1000>`. Check the result has sound (`ffmpeg -af volumedetect`, mean above about -50 dB).
- Otherwise `scripts/record_web.py <build> <out> --script play.py` with a small play script.
- Native/no web build: ask the owner for a phone screen recording — the one acceptable question.
- Finish with `scripts/finish_video.py raw.webm docs/store/rating/gameplay.mp4 --end <s>`; use `--sheet-only` on the
  raw file first to find where the loader/reload frames start, then Read the output sheet and confirm the first frame
  is the app loading/home and the last is the result. Re-cut if not.

### 5. Text
Fill `LISTING.md` and `rating/GAME_DESCRIPTION.md` from the templates. Counts and claims ("100장이 넘는 그림",
"하루 힌트 2개") must be verified in code/data; round down rather than overstate. Name ≤10 chars without spaces, no
hyphen. Suggest 전체이용가 only if there is truly no violence/sexual/gambling content, chat, or random paid items.

### 6. Deliver
Commit the files individually (no `git add .`) and push, per the repo's commit rules. Send the thumbnail and
`LISTING.md` with SendUserFile (videos > 5 MB may fail to upload — say where the file is if so). Report in Korean,
short: what was made, then "사장님 할 일" (support email, GRAC 신청 with the two rating files, seal/sign + checkboxes,
검토 요청), and that Claude will redeploy the latest build before 검토 요청.

## Several games at once
When asked to do this for other games too, find them (e.g. `~/programming/**/granite.config.ts`,
`Assets/AppsInToss`, the apps listed in apps-in-toss-deploy §1) and run one background agent per repo with this
skill, in parallel, each committing in its own repo. Don't edit a repo where another session is mid-build.
