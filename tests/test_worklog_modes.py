#!/usr/bin/env python3
"""
워크로그 저장 모드 (--set-mode) 테스트
Run: python3 tests/test_worklog_modes.py
"""

import sys, os, json, subprocess, tempfile, unittest

SCRIPT = os.path.expanduser("~/.claude/scripts/notion-migrate-worklogs.sh")


# ── apply_mode 로직 (스크립트와 동일) ────────────────────────────────────────

def apply_mode(cfg: dict, mode: str) -> dict:
    env = cfg.setdefault('env', {})
    if mode == 'notion-only':
        env['WORKLOG_DEST']      = 'notion-only'
        env['WORKLOG_GIT_TRACK'] = 'false'
    elif mode == 'git':
        env['WORKLOG_DEST']      = 'git'
        env['WORKLOG_GIT_TRACK'] = 'true'
    elif mode == 'git-ignore':
        env['WORKLOG_DEST']      = 'git'
        env['WORKLOG_GIT_TRACK'] = 'false'
    elif mode == 'both':
        env['WORKLOG_DEST']      = 'notion'
        env['WORKLOG_GIT_TRACK'] = 'true'
    return cfg

VALID_MODES = ['notion-only', 'git', 'git-ignore', 'both']


# ── 유닛 테스트: apply_mode ───────────────────────────────────────────────────

class TestApplyMode(unittest.TestCase):

    def _cfg(self):
        return {'env': {'WORKLOG_DEST': 'git', 'WORKLOG_GIT_TRACK': 'true', 'OTHER': 'keep'}}

    def test_notion_only(self):
        cfg = apply_mode(self._cfg(), 'notion-only')
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'notion-only')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'false')

    def test_git(self):
        cfg = apply_mode(self._cfg(), 'git')
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'git')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'true')

    def test_git_ignore(self):
        cfg = apply_mode(self._cfg(), 'git-ignore')
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'git')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'false')

    def test_both(self):
        cfg = apply_mode(self._cfg(), 'both')
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'notion')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'true')

    def test_other_keys_preserved(self):
        """다른 env 키는 변경하지 않음"""
        cfg = apply_mode(self._cfg(), 'git')
        self.assertEqual(cfg['env']['OTHER'], 'keep')

    def test_env_key_created_if_missing(self):
        """env 키 없어도 생성됨"""
        cfg = apply_mode({}, 'git')
        self.assertIn('WORKLOG_DEST', cfg['env'])

    def test_all_modes_produce_valid_dest(self):
        """모든 모드의 WORKLOG_DEST가 알려진 값임"""
        valid_dests = {'git', 'notion', 'notion-only'}
        for mode in VALID_MODES:
            cfg = apply_mode({}, mode)
            self.assertIn(cfg['env']['WORKLOG_DEST'], valid_dests, f"mode={mode}")

    def test_all_modes_produce_valid_git_track(self):
        """모든 모드의 WORKLOG_GIT_TRACK이 true/false"""
        for mode in VALID_MODES:
            cfg = apply_mode({}, mode)
            self.assertIn(cfg['env']['WORKLOG_GIT_TRACK'], {'true', 'false'}, f"mode={mode}")


# ── 통합 테스트: 실제 쉘 스크립트 호출 ──────────────────────────────────────

class TestSetModeScript(unittest.TestCase):
    """
    실제 bash 스크립트를 temp 디렉토리로 호출해 settings.json 업데이트 검증.
    NOTION_TOKEN / NOTION_DB_ID 불필요 (--set-mode 는 마이그레이션 없이 동작).
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # 빈 worklogs 디렉토리 (마이그레이션 대상 없음)
        self.wl_dir = os.path.join(self.tmpdir, '.worklogs')
        os.makedirs(self.wl_dir)
        # 기본 settings.json
        self.settings = os.path.join(self.tmpdir, 'settings.json')
        initial = {'env': {'WORKLOG_DEST': 'git', 'WORKLOG_GIT_TRACK': 'true', 'FOO': 'bar'}}
        with open(self.settings, 'w') as f:
            json.dump(initial, f, indent=2)

    def _run_set_mode(self, mode):
        # HOME을 tmpdir로 override해 settings.json 경로 우회
        # 스크립트는 "$HOME/.claude/settings.json"을 사용하므로
        # tmpdir/.claude/settings.json을 만들어준다
        claude_dir = os.path.join(self.tmpdir, '.claude')
        os.makedirs(claude_dir, exist_ok=True)
        settings_path = os.path.join(claude_dir, 'settings.json')
        initial = {'env': {'WORKLOG_DEST': 'git', 'WORKLOG_GIT_TRACK': 'true', 'FOO': 'bar'}}
        with open(settings_path, 'w') as f:
            json.dump(initial, f, indent=2)

        env = {**os.environ, 'HOME': self.tmpdir}
        # .env 없어도 괜찮도록 (NOTION_TOKEN/DB_ID 불필요 — --set-mode 전용)
        result = subprocess.run(
            ['bash', SCRIPT, '--dry-run', '--set-mode', mode, self.wl_dir],
            capture_output=True, text=True, env=env
        )
        with open(settings_path) as f:
            updated = json.load(f)
        return result, updated

    def test_set_mode_notion_only(self):
        result, cfg = self._run_set_mode('notion-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'notion-only')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'false')

    def test_set_mode_git(self):
        result, cfg = self._run_set_mode('git')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'git')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'true')

    def test_set_mode_git_ignore(self):
        result, cfg = self._run_set_mode('git-ignore')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'git')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'false')

    def test_set_mode_both(self):
        result, cfg = self._run_set_mode('both')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(cfg['env']['WORKLOG_DEST'],      'notion')
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'true')

    def test_set_mode_preserves_other_keys(self):
        result, cfg = self._run_set_mode('git')
        self.assertEqual(cfg['env'].get('FOO'), 'bar', "다른 env 키 보존 실패")

    def test_set_mode_output_contains_label(self):
        result, _ = self._run_set_mode('notion-only')
        self.assertIn('Notion에만 기록', result.stdout)

    def test_set_mode_output_contains_dest(self):
        result, _ = self._run_set_mode('git-ignore')
        self.assertIn('WORKLOG_DEST=git', result.stdout)
        self.assertIn('WORKLOG_GIT_TRACK=false', result.stdout)

    def test_invalid_mode_fails(self):
        env = {**os.environ, 'HOME': self.tmpdir}
        result = subprocess.run(
            ['bash', SCRIPT, '--dry-run', '--set-mode', 'invalid', self.wl_dir],
            capture_output=True, text=True, env=env
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('notion-only', result.stderr)

    def test_settings_json_is_valid_json(self):
        result, cfg = self._run_set_mode('both')
        self.assertIsInstance(cfg, dict)
        self.assertIn('env', cfg)

    def test_dry_run_with_set_mode(self):
        """--dry-run과 --set-mode 함께 쓰면 마이그레이션 없이 모드만 변경"""
        result, cfg = self._run_set_mode('git-ignore')
        self.assertIn('[DRY RUN]', result.stdout)
        self.assertEqual(cfg['env']['WORKLOG_GIT_TRACK'], 'false')


if __name__ == '__main__':
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
