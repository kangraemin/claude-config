"""서비스 계정(~/.claude/ai-paper-analytics-sa.json) 세션. 프로젝트 ai-paper-analytics."""
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
SA = '/Users/ram/.claude/ai-paper-analytics-sa.json'
GA_ACCOUNT = 'accounts/136249894'  # GA 계정 'Kangraemin'(remin1994 관리자, SA는 뷰어)
def sess(*scopes):
    return AuthorizedSession(service_account.Credentials.from_service_account_file(SA, scopes=list(scopes)))
