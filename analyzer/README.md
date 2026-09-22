# 논문 분석 구성

Python은 PDF 접수·원문 식별·대기열·Markdown 검증·Markdown/HTML 리포트 생성을 맡습니다. 분석 내용과 개념 이미지는 로그인한 ChatGPT Chat에서 얻습니다. 고정 프롬프트는 `src/figure_reports/resources/chat-analysis-prompt.md`입니다.

## Windows 설치

Python 3.11 이상과 Git을 설치하고, starter-vault를 개인 위치에 복사해 Obsidian으로 엽니다. 분석 프로그램은 Vault 밖에 둡니다.

```powershell
python analyzer/install.py --vault "D:/Research Vault" --expected-remote "https://github.com/YOUR_ACCOUNT/YOUR_PRIVATE_VAULT.git"
```

기본 설치 위치는 사용자 홈 아래 `Documents/Codex/Paper Analyzer`입니다. 설치 프로그램은 개인 설정, 별도 Python 환경과 의존성을 준비하며 분석이나 업로드를 시작하지 않습니다. 기존 폴더가 있으면 보존하고 중단합니다. Obsidian의 PC 요청 수신기는 이 기본 위치를 읽습니다.

설치 폴더에서 `Start-Watcher.ps1`을 실행하면 창 없이 파일 접수 감지가 시작됩니다. 상태는 `.venv/Scripts/python.exe launch.py status`, 종료 요청은 같은 명령의 `stop`입니다. PC가 잠들거나 꺼져 있으면 접수·분석이 진행되지 않습니다. 시작 프로그램 자동 등록은 포함하지 않습니다.

일반 PDF는 Vault의 `PDF/`에 넣으면 Obsidian 논문 목록과 그래프에 표시됩니다. **분석은 각 파일 옆의 `분석` 버튼을 누른 경우에만 요청됩니다.** 기존 `Inbox/` 자동 접수 경로는 호환용이며 새 PDF 분석을 자동으로 시작하는 기본 경로가 아닙니다.

## Chat으로 분석

1. Vault의 `PDF/`에 PDF를 넣고 해당 파일의 `분석` 버튼을 누릅니다. 요청에는 상대 경로와 SHA-256이 기록되어 다른 PDF로 범위가 확장되지 않습니다. PC 접수는 순차적으로 처리합니다.
2. `chat-dispatch.py claim`으로 작업을 하나 접수하고 `prepare-chat-job.py --job <ID>`를 실행합니다. 출력된 chat-packet에는 PDF, 고정 프롬프트, source-blocks, request가 들어갑니다.
3. ChatGPT Chat의 사용 가능한 Latest Pro 모델에서 해당 자료를 분석하고 고정 프롬프트대로 Markdown과 이미지를 받습니다. Work GPT-6 Sol High에서 결과를 원문과 대조한 뒤 게시합니다. 모델의 실제 사용 여부는 각 실행 기록으로 확인해야 합니다. ChatGPT 구독/로그인 및 사용량 제한이 적용됩니다.
4. 설치 폴더의 `app`을 PYTHONPATH에 지정하고 다음 도구의 `--help`로 결과 검사/게시 명령을 확인합니다. `check`는 구조와 근거 식별자 검사이며, 사람 또는 승인된 Codex 검토의 과학적 검토를 대체하지 않습니다.

```powershell
$env:PYTHONPATH = "$PWD/app"
.venv/Scripts/python.exe -m figure_reports.markdown_exchange --help
```

`publish`는 로컬 Vault 결과를 만들고 같은 원본의 `PDF/` 경로를 `Dashboard/pdf-links.json`에 연결합니다. Git push와 원격 receipt 검증은 별도 단계입니다. 자세한 수동 연결 절차와 모델 단계는 `CHAT_AUTOMATION.md`에 있습니다. 원문·생성 이미지의 사용 및 공유 권한은 사용자 책임 범위에서 확인하세요.

## 모바일 버튼과 PC 연결

`mobile-control.json`은 Git 밖의 개인 설정입니다. `thread`에 자신의 Codex 작업 UUID, `codex`에 `queue` 명령을 지원하는 실행 파일 절대 경로, `workspace`와 `runbook`에 실제 설치 경로를 넣고 진단 후 `enabled`를 켭니다. 비밀키나 계정 암호를 넣지 않습니다. 요청 JSON은 명령 프롬프트로 실행하지 않습니다.

Obsidian을 실행 중인 Windows PC가 Git 요청을 받아 Codex queue에 전달하는 코드는 포함되어 있습니다. **모든 Codex 버전에서 queue 지원과 유휴 작업 자동 재개가 보장되지는 않습니다.** 설치 환경에서 diagnostic 요청의 왕복을 먼저 검증하세요. 미지원이면 PC Chat에서 수동으로 분석을 시작할 수 있습니다. 매분 모델을 호출하는 클라우드 예약작업은 설치하지 않습니다.

## 개발 검증

```powershell
python -m pip install -e "analyzer[test]"
python -m playwright install chromium
python -m pytest analyzer/tests -q
```

이 패키지에는 PDF 엔진 바이너리, 사용자 PDF, 실행 상태, 계정 파일, 브라우저 프로필을 포함하지 않습니다.
