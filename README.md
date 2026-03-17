# 🔮 타로카드 리딩 앱

Streamlit으로 구현된 78장 라이더-웨이트-스미스 타로 리딩 웹앱입니다.

## 기능

- **78장 풀 덱**: 메이저 아르카나 22장 + 마이너 아르카나 56장 (완드/컵/소드/펜타클 각 14장)
- **카테고리 선택**: 오늘의운세 / 연애운 / 직업운 / 학업및시험운 / 건강운 / 애정운 / 인간관계
- **3장 무중복 뽑기**: 매 뽑기마다 중복 없이 3장 선택
- **정방향/역방향**: 랜덤 결정 (역방향 포함/제외 토글 옵션)
- **카드별 해석**: 선택 카테고리 + 방향에 맞춘 한국어 해석
- **이미지 표시**: 레포에 포함된 `assets/rws/` 로컬 이미지 사용 (없으면 Wikimedia Commons에서 자동 다운로드)
- **GPT 상세풀이**: "상세풀이 생성" 버튼을 누르면 OpenAI GPT가 매우 상세한 한국어 타로 리딩을 생성
- **세션 유지**: `st.session_state`로 새로고침해도 결과 유지

## 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성 (권장)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 앱 실행

```bash
streamlit run app.py
```

브라우저에서 http://localhost:8501 로 접속합니다.

### 3. 카드 이미지

카드 이미지(78장)는 **레포에 포함**되어 있어(`assets/rws/`), 별도 다운로드 없이도
Streamlit Cloud 배포 환경에서 누구나 이미지를 볼 수 있습니다.

로컬에서 이미지를 갱신하거나 누락된 이미지를 다시 받으려면:

```bash
python scripts/download_rws_images.py
```

옵션:
```
--output PATH    이미지 저장 경로 (기본: assets/rws)
--delay SECONDS  요청 간격(초) (기본: 1.0)
```

## GPT 상세풀이 기능

카드를 뽑은 뒤 사이드바의 **"🤖 GPT 상세풀이"** 섹션에서 질문을 입력(선택)하고
**"상세풀이 생성 ✨"** 버튼을 클릭하면, OpenAI GPT가 다음 정보를 바탕으로
매우 상세한 한국어 타로 리딩을 생성합니다:

- 선택된 카테고리
- 뽑힌 카드 3장의 이름, 위치(과거/현재/미래), 방향(정/역)
- `data/meanings_ko.json`의 기본 의미 및 카테고리 힌트

출력 구조:
1. 종합 요약
2. 과거 카드 상세 해석
3. 현재 카드 상세 해석
4. 미래 카드 상세 해석
5. 카드 조합 해석
6. 실행 조언 (5가지 이상)
7. 주의점 및 리스크

> ⚠️ **이 기능은 OpenAI API를 호출하므로 API 사용 비용이 발생합니다.**
> 동일한 카드·질문·카테고리 조합의 결과는 캐시되어 중복 호출을 방지합니다.

### OpenAI API 키 설정

**로컬 실행**:

```bash
export OPENAI_API_KEY=sk-...          # Mac/Linux
set OPENAI_API_KEY=sk-...             # Windows CMD
$env:OPENAI_API_KEY="sk-..."          # Windows PowerShell
```

또는 레포 루트에 `.env` 파일을 생성한 뒤:
```
OPENAI_API_KEY=sk-...
```
`python-dotenv`가 설치된 경우 자동으로 로드됩니다.

**Streamlit Cloud**:

앱 대시보드 → **Settings → Secrets** 에서 다음을 추가합니다:

```toml
OPENAI_API_KEY = "sk-..."
```

> `.streamlit/secrets.toml` 파일은 `.gitignore`에 포함되어 있어 레포에 커밋되지 않습니다.
> 절대 API 키를 소스 코드나 레포에 직접 기입하지 마세요.

## 프로젝트 구조

```
taro/
├── app.py                        # Streamlit 메인 앱
├── tarot_gpt.py                  # GPT 상세풀이 생성 모듈
├── requirements.txt              # Python 의존성
├── README.md                     # 이 파일
├── .gitignore
├── data/
│   ├── cards.json                # 78장 카드 메타데이터
│   └── meanings_ko.json          # 한국어 해석 데이터 (컴팩트 스키마)
├── assets/
│   └── rws/                      # 카드 이미지 78장 (레포에 포함)
├── scripts/
│   └── download_rws_images.py   # Wikimedia Commons 이미지 다운로더
└── tests/
    ├── test_deck.py              # pytest 테스트 (덱 데이터 / 이미지 로딩)
    └── test_gpt.py               # pytest 테스트 (GPT 모듈)
```

## 데이터 구조

### `data/cards.json`

78장 카드의 메타데이터:

```json
[
  {
    "id": "major_00",
    "name_ko": "바보",
    "name_en": "The Fool",
    "arcana": "major",
    "suit": null,
    "rank": 0,
    "image_file": "00_fool.jpg"
  },
  ...
]
```

### `data/meanings_ko.json`

컴팩트 스키마 (기본 해석 + 카테고리별 힌트):

```json
{
  "_schema": "compact_v1",
  "_categories": {"today": "오늘의운세", "love": "연애운", ...},
  "cards": {
    "major_00": {
      "upright": "새로운 시작과 무한한 가능성...",
      "reversed": "무모함과 부주의함을 경계...",
      "hints": {
        "today": "오늘은 새로운 도전을 맞이할...",
        "love": "새로운 연애의 시작이나...",
        ...
      }
    }
  }
}
```

런타임에 앱이 `{기본 해석} + {카테고리 힌트}`를 합쳐 최종 해석을 표시합니다.

## 테스트 실행

```bash
pytest tests/ -v
```

테스트 항목:
- 78장 고유 카드 존재 확인
- 메이저/마이너 아르카나 수량 확인
- 4개 수트 각 14장 확인
- 3장 뽑기 중복 없음 확인
- 방향 로직 검증
- 해석 데이터 완전성 확인
- 이미지 다운로드 스크립트 매핑 확인
- GPT 모듈 동작 확인 (OpenAI API 모킹)

## 이미지 라이선스 및 출처

카드 이미지는 **Rider-Waite Tarot** (공개 도메인) 입니다.

- **저자**: Pamela Colman Smith (삽화), Arthur Edward Waite (개념)
- **출판**: 1909년, Rider Company
- **저작권 상태**: 미국 내 공개 도메인 (1928년 이전 출판)
- **출처**: [Wikimedia Commons – Rider-Waite tarot deck](https://commons.wikimedia.org/wiki/Rider-Waite_tarot_deck)

주요 파일 페이지 (Wikimedia Commons):
- [File:RWS Tarot 00 Fool.jpg](https://commons.wikimedia.org/wiki/File:RWS_Tarot_00_Fool.jpg)
- [File:RWS Tarot 01 Magician.jpg](https://commons.wikimedia.org/wiki/File:RWS_Tarot_01_Magician.jpg)
- [File:RWS Tarot 02 High Priestess.jpg](https://commons.wikimedia.org/wiki/File:RWS_Tarot_02_High_Priestess.jpg)
- (나머지 75장도 동일한 명명 규칙으로 Wikimedia Commons에서 확인 가능)

> **참고**: 이미지 자체는 공개 도메인이지만, `scripts/download_rws_images.py`는
> Wikimedia Commons 이용 약관을 준수하여 `User-Agent` 헤더를 포함하며
> 요청 간 지연을 두어 서버에 과부하가 걸리지 않도록 합니다.

## Streamlit Cloud 배포

1. GitHub에 코드를 푸시합니다 (이미지 78장이 `assets/rws/` 에 포함됨)
2. [share.streamlit.io](https://share.streamlit.io) 에서 새 앱 생성
3. `app.py`를 메인 파일로 지정
4. **앱 접근 비밀번호 설정 (필수)**: 앱 Settings → Secrets 에 아래를 추가합니다:

   ```toml
   APP_PASSWORD = "원하는_비밀번호"
   ```

   설정하지 않으면 앱이 실행되지 않습니다. 이 비밀번호를 공유받은 사용자만 앱을 사용할 수 있습니다.

5. (선택) GPT 상세풀이를 사용하려면 같은 Secrets 파일에 `OPENAI_API_KEY`도 추가합니다:

   ```toml
   APP_PASSWORD = "원하는_비밀번호"
   OPENAI_API_KEY = "sk-..."
   ```

6. 배포 후 누구나 링크로 접속하면 사이드바에서 비밀번호를 입력해야 앱을 사용할 수 있습니다

> **로컬 실행 시 비밀번호 설정**:
>
> ```bash
> export APP_PASSWORD="원하는_비밀번호"   # Mac/Linux
> $env:APP_PASSWORD="원하는_비밀번호"     # Windows PowerShell
> streamlit run app.py
> ```
>
> 또는 `.streamlit/secrets.toml` 파일에 추가합니다 (`.gitignore`에 포함됨):
>
> ```toml
> APP_PASSWORD = "원하는_비밀번호"
> ```

> 이미지는 레포에 커밋되어 있으므로 Streamlit Cloud에서 별도 다운로드 없이
> 즉시 표시됩니다. 혹시 일부 이미지가 누락된 경우 Wikimedia Commons에서
> 자동으로 다운로드하는 폴백 동작이 활성화됩니다.
