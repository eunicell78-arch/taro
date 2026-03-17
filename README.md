# 🔮 타로카드 리딩 앱

Streamlit으로 구현된 78장 라이더-웨이트-스미스 타로 리딩 웹앱입니다.

## 기능

- **78장 풀 덱**: 메이저 아르카나 22장 + 마이너 아르카나 56장 (완드/컵/소드/펜타클 각 14장)
- **카테고리 선택**: 오늘의운세 / 연애운 / 직업운 / 학업및시험운 / 건강운 / 애정운 / 인간관계
- **3장 무중복 뽑기**: 매 뽑기마다 중복 없이 3장 선택
- **정방향/역방향**: 랜덤 결정 (역방향 포함/제외 토글 옵션)
- **카드별 해석**: 선택 카테고리 + 방향에 맞춘 한국어 해석
- **3장 종합 요약**: 카드 조합을 바탕으로 카테고리별 종합 해석
- **이미지 표시**: `assets/rws/`의 로컬 이미지 사용 (없으면 플레이스홀더 표시)
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

### 3. 카드 이미지 다운로드 (선택)

이미지 없이도 텍스트 해석은 정상 동작합니다. 카드 이미지를 표시하려면:

```bash
python scripts/download_rws_images.py
```

옵션:
```
--output PATH    이미지 저장 경로 (기본: assets/rws)
--delay SECONDS  요청 간격(초) (기본: 1.0)
```

다운로드가 완료되면 `assets/rws/` 폴더에 78장의 이미지가 저장됩니다.

## 프로젝트 구조

```
taro/
├── app.py                        # Streamlit 메인 앱
├── requirements.txt              # Python 의존성
├── README.md                     # 이 파일
├── .gitignore                    # 다운로드된 이미지 등 제외
├── data/
│   ├── cards.json                # 78장 카드 메타데이터
│   └── meanings_ko.json          # 한국어 해석 데이터 (컴팩트 스키마)
├── assets/
│   └── rws/                      # 다운로드된 카드 이미지 (.gitignore에 포함)
├── scripts/
│   └── download_rws_images.py   # Wikimedia Commons 이미지 다운로더
└── tests/
    └── test_deck.py              # pytest 테스트
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
pytest tests/test_deck.py -v
```

테스트 항목:
- 78장 고유 카드 존재 확인
- 메이저/마이너 아르카나 수량 확인
- 4개 수트 각 14장 확인
- 3장 뽑기 중복 없음 확인
- 방향 로직 검증
- 해석 데이터 완전성 확인
- 이미지 다운로드 스크립트 매핑 확인

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

1. GitHub에 코드를 푸시합니다 (이미지 제외: `.gitignore` 설정됨)
2. [share.streamlit.io](https://share.streamlit.io) 에서 새 앱 생성
3. `app.py`를 메인 파일로 지정
4. 배포 후 이미지 없이도 텍스트 해석은 정상 동작합니다

> 클라우드 배포 환경에서 이미지를 표시하려면 별도의 이미지 호스팅이 필요합니다.
