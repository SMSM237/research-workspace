# 대시보드 설치

`starter-vault`에는 플러그인 실행 파일 세 개와 공통 스타일이 이미 포함되어 있습니다. Vault 전체 폴더를 복사하여 Obsidian으로 열고 커뮤니티 플러그인에서 Figure First Reader를 활성화하세요. 처음부터 Tasks, Calendar, Dataview를 별도 설치할 필요는 없습니다. 카드의 할 일·달력·회의·프로젝트 기능은 이 플러그인이 제공합니다.

PC는 자동으로 화면에 맞는 연구 홈을 열고, 모바일은 세로 카드 홈을 엽니다. 제목과 주요 내용은 크기·굵기·색을 함께 사용합니다. 시스템에서 사용 가능한 글꼴을 사용하며 특정 상용 글꼴을 배포하지 않습니다.

## PDF와 분석

원본 PDF를 Vault의 `PDF/`에 넣으면 Windows·Mac·Android에서 열 수 있고 논문 카드·보관함·3D 그래프에도 표시됩니다. PDF를 넣는 것만으로 분석이 시작되지는 않습니다. 원하는 파일 옆의 **분석**을 누르면 그 파일의 경로와 SHA-256이 담긴 요청이 저장됩니다. Git 동기화와 Windows PC 접수 후 Chat 분석, Work 검증, Git 게시 상태를 논문 분석 화면에서 확인합니다. PDF가 크면 Android의 Git 동기화가 오래 걸릴 수 있으므로 첫 사용 시 한 편으로 시험하세요. `Inbox/`의 구형 자동 접수 파일은 새 보관함에 자동으로 합쳐지지 않습니다.

3D 그래프는 분석 리포트·원본 PDF·공통 주제 연결을 표시합니다. 점을 누르면 원본 또는 리포트가 열립니다. 휠로 확대·축소, 드래그로 이동, Shift+드래그로 회전할 수 있습니다. 색상은 공통 주제별 분류이며 인용 관계나 검증된 기전을 뜻하지 않습니다.

## 업데이트

개인 Vault를 백업한 뒤 `.obsidian/plugins/figure-first-reader`의 `main.js`, `styles.css`, `manifest.json`만 교체하세요. 개인 노트나 플러그인의 data.json을 덮어쓰지 않습니다. 동기화 후 다른 기기에서 Obsidian을 다시 열거나 플러그인을 다시 활성화합니다.

## 동기화 설정

1. 본인 GitHub 계정에 **비공개** Vault 저장소를 만듭니다.
2. starter-vault 내용만 해당 저장소의 루트에 올립니다. `.obsidian`을 누락하지 마세요. 저장소 전체를 소프트웨어 공개 저장소와 연결하지 않습니다.
3. Windows/Mac에서 Obsidian Git을 공식 커뮤니티 목록으로 설치하고 해당 저장소를 연결합니다. Git 계정 인증은 자신의 운영체제 자격 증명 도구에서 합니다.
4. Android는 GitSync에서 같은 개인 저장소를 빈 로컬 폴더로 clone한 뒤, Obsidian과 위젯이 **그 동일한 폴더**를 사용하게 합니다. 동기화 프로그램 두 개가 같은 폴더를 동시에 갱신하지 않도록 하나를 선택하세요.
5. 한 기기에서 새 테스트 할 일 하나를 추가 → 동기화 → 다른 기기에서 확인 → 체크 → 다시 동기화하여 돌아오는지 확인합니다. 충돌 파일이 있으면 새 작업을 시작하기 전에 정리합니다.

공식 안내: [Obsidian Git](https://github.com/Vinzent03/obsidian-git), [GitSync](https://github.com/ViscousPot/GitSync). 앱별 인증과 권한은 패키지 다운로드로 자동 설정되지 않습니다.

## 소스 빌드

Node.js와 npm을 설치한 뒤 `dashboard/plugin`에서 실행합니다.

```sh
npm install
npm run build
npm run typecheck
npm test
```

0.7.3: 체크박스 내부 체크 표시의 크기와 중앙 위치 수정. 0.7.2: 프로젝트 제목–주차 간격 축소, 날짜별 구절 10일 순환과 자정/앱 복귀 갱신.
