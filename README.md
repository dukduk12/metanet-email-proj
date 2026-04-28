# 📧 업무 메일 PDF 분석 및 추천 시스템

Airflow를 활용한 자동 데이터 파이프라인과 Gemini AI를 기반으로 업무 이메일과 첨부된 PDF 문서를 요약하고, Chroma DB를 통해 과거 유사 업무 메일을 추천해주는 종합 시스템입니다.

## 🚀 주요 기능
- **이메일 자동 파이프라인 (Airflow)**: 매일 지정된 키워드(`[업무 협조]` 등)의 메일을 스크래핑하여 PDF를 파싱하고 AI로 요약한 뒤, 벡터(Vector) 데이터로 변환해 Chroma DB에 자동 적재합니다.
- **AI 분석 및 TF-IDF 차트 (Streamlit)**: 수신된 메일을 웹 UI에서 확인하고 개별 분석할 수 있으며, TF-IDF를 이용한 핵심 키워드 막대그래프를 생성합니다.
- **유사 메일 추천**: 현재 분석 중인 메일과 가장 유사도(Cosine Similarity)가 높은 과거 메일 3개를 추천해 줍니다.
- **DB 전용 뷰어**: 백그라운드(Airflow)에서 수집된 방대한 메일 DB를 웹 화면에서 손쉽게 조회하고 임베딩 벡터 수치까지 확인할 수 있습니다.

---

## 🛠 기술 스택
- **언어 및 패키지 관리**: Python 3.12, `uv`
- **웹 대시보드 (UI)**: Streamlit
- **데이터 파이프라인**: Apache Airflow, Docker Compose
- **데이터베이스**: Chroma DB (Vector DB), PostgreSQL (Airflow 메타데이터)
- **AI & ML**: Google Gemini API (`gemini-1.5-flash` 요약, `text-embedding-004` 임베딩), scikit-learn (TF-IDF)

---

## ⚙️ 사전 준비사항 (Prerequisites)

1. **Docker 및 Docker Compose**가 설치되어 있어야 합니다.
2. 빠르고 쾌적한 패키지 관리를 위해 **`uv`** 가 설치되어 있어야 합니다.
3. 프로젝트 루트(최상위) 디렉토리에 **`.env`** 파일을 생성하고 다음 정보를 기입해야 합니다.
   ```ini
   # .env 예시
   GEMINI_API_KEY=당신의_제미나이_API_키
   IMAP_SERVER=imap.gmail.com
   EMAIL_ACCOUNT=당신의_이메일@gmail.com
   EMAIL_PASSWORD=앱_비밀번호
   ```

---

## 🏃‍♂️ 실행 방법 (How to Run)

### 1. 백그라운드 인프라 실행 (Airflow + Chroma DB)
데이터베이스와 스케줄러 환경을 도커로 띄웁니다.
```bash
docker compose up -d
```
> 도커가 모두 실행되면 [http://localhost:8080](http://localhost:8080) 에 접속하여 Airflow UI를 확인할 수 있습니다. (기본 계정: `admin` / `admin`)
> Airflow 내에서 `email_embedding_daily_job` DAG를 켜두거나 수동으로 Trigger(▶️)하여 오늘의 메일을 DB에 적재할 수 있습니다.

### 2. 패키지 설치
`uv`를 사용하여 프로젝트에 필요한 파이썬 라이브러리를 동기화합니다.
```bash
uv sync
```

### 3. 메인 분석 앱 실행 (Streamlit UI)
메일 목록을 불러오고 개별 분석 및 유사 메일 추천을 받을 수 있는 메인 대시보드입니다.
```bash
uv run streamlit run src/app.py
```
> 실행 후 브라우저에서 `http://localhost:8501` 로 접속됩니다.

### 4. Chroma DB 뷰어 실행 (선택 사항)
Airflow가 수집하여 넣은 과거 메일 데이터와 임베딩 수치를 확인하고 싶을 때 실행하는 독립 뷰어입니다.
```bash
uv run streamlit run scripts/db_viewer.py
```
> 실행 후 브라우저에서 `http://localhost:8502` 로 접속됩니다.

---

## 📁 디렉토리 구조
```text
.
├── dags/
│   └── email_embedding_pipeline.py  # Airflow 배치 파이프라인
├── src/
│   ├── app.py                       # 메인 Streamlit 앱
│   ├── config.py                    # 환경 변수 및 설정 관리
│   ├── db_client.py                 # Chroma DB 연결 클라이언트
│   ├── email_client.py              # IMAP 메일 수집 클라이언트
│   ├── pdf_parser.py                # PDF 텍스트 추출
│   ├── summarizer.py                # Gemini API 요약 로직
│   └── word_cloud_gen.py            # TF-IDF 기반 차트 생성
├── scripts/
│   └── db_viewer.py                 # Chroma DB 조회 전용 대시보드
├── docker-compose.yml               # 인프라(Airflow, Postgres, Chroma) 구성
├── pyproject.toml                   # uv 패키지 의존성 파일
└── README.md
```
