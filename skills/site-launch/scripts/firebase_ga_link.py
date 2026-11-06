"""Firebase 프로젝트에 GA4 연결(Firebase Management API, gcloud 로그인 토큰) + 앱 설정 파일 저장.
  python3 firebase_ga_link.py <firebase프로젝트ID> <저장폴더>
- 쿼터 프로젝트 헤더(x-goog-user-project)가 꼭 필요하다.
- GA 속성 이름은 API로 못 바꾼다(속성이 'projectId'로 생김) → GA 화면에서 이름·통화 수정(2026-11-07 러너스하이 검증).
- 이후 ga_custom_dims.py <속성ID> 로 측정기준 등록. 서비스 계정은 GA 계정 단위 뷰어라 새 속성이 자동으로 보인다."""
import base64, os, subprocess, sys, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from _sa import GA_ACCOUNT
proj, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
T = subprocess.check_output(['gcloud', 'auth', 'print-access-token'], text=True).strip()
H = {'Authorization': 'Bearer ' + T, 'x-goog-user-project': proj}
B = f'https://firebase.googleapis.com/v1beta1/projects/{proj}'
d = requests.get(B + '/analyticsDetails', headers=H).json()
if 'analyticsProperty' not in d:
    op = requests.post(B + ':addGoogleAnalytics', headers=H, json={'analyticsAccountId': GA_ACCOUNT.split('/')[1]}).json()
    for _ in range(30):
        time.sleep(3); r = requests.get('https://firebase.googleapis.com/v1beta1/' + op['name'], headers=H).json()
        if r.get('done'): break
    d = requests.get(B + '/analyticsDetails', headers=H).json()
print('PROPERTY', d['analyticsProperty']['id'])
for kind, key in (('androidApps', 'packageName'), ('iosApps', 'bundleId')):
    for a in requests.get(f'{B}/{kind}', headers=H).json().get('apps', []):
        cfg = requests.get(f"https://firebase.googleapis.com/v1beta1/{a['name']}/config", headers=H).json()
        fn = 'GoogleService-Info.plist' if kind == 'iosApps' else f"google-services.{a[key]}.json"
        open(os.path.join(out, fn), 'wb').write(base64.b64decode(cfg['configFileContents']))
        print(kind, a[key], a['appId'], '->', fn)
