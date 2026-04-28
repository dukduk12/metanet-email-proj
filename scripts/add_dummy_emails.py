import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.db_client import ChromaClient
from loguru import logger

DUMMY_EMAILS = [
    {
        "email_id": "dummy_email_002",
        "title": "[업무 협조] 2026년 상반기 IT 인프라 고도화 제안",
        "summary": "노후 서버 교체 및 클라우드 마이그레이션을 포함한 IT 인프라 고도화 계획을 제안합니다. AWS 기반으로 전환 시 연간 운영비 30% 절감 효과가 예상되며, 3개년 로드맵과 예산안을 첨부하였습니다.",
        "date": "2026-04-15",
        "sender": "김인프라 <infra@techcorp.com>",
    },
    {
        "email_id": "dummy_email_003",
        "title": "[업무 협조] 신규 협력사 계약 검토 요청",
        "summary": "물류 부문 신규 협력사 (주)스피드물류와의 계약서 검토를 요청드립니다. 계약 기간은 2026년 6월부터 1년이며, 단가 협상 결과 기존 대비 12% 절감되었습니다. 법무팀 검토 후 날인 요청드립니다.",
        "date": "2026-04-18",
        "sender": "이계약 <contract@logistics.co.kr>",
    },
    {
        "email_id": "dummy_email_004",
        "title": "[업무 협조] 전사 보안 취약점 점검 결과 공유",
        "summary": "4월 정기 보안 점검 결과를 공유합니다. 총 23개 시스템 중 5개에서 취약점이 발견되었으며, 그 중 2개는 긴급 패치가 필요한 High 등급입니다. 각 담당팀은 5월 2일까지 조치 완료 후 결과를 보안팀에 보고해 주시기 바랍니다.",
        "date": "2026-04-21",
        "sender": "박보안 <security@company.com>",
    },
    {
        "email_id": "dummy_email_005",
        "title": "[업무 협조] 2026 하반기 마케팅 캠페인 기획안 검토",
        "summary": "하반기 신제품 출시에 맞춘 통합 마케팅 캠페인 기획안을 첨부합니다. SNS·유튜브·옥외광고를 연계한 3단계 전략으로 구성되며, 총 예산은 2억 5천만원입니다. 각 본부장님의 의견을 5월 9일까지 취합할 예정입니다.",
        "date": "2026-04-23",
        "sender": "최마케팅 <marketing@brand.co.kr>",
    },
    {
        "email_id": "dummy_email_006",
        "title": "[업무 협조] 사무실 이전 관련 업무 협조 요청",
        "summary": "본사 사무실 이전(현 위치 → 강남구 테헤란로 신사옥) 일정을 안내드립니다. 이전일은 6월 14일(토)이며, 각 팀별 짐 정리 및 IT 장비 태그 부착을 6월 7일까지 완료해 주시기 바랍니다. 이전 후 월요일(6/16)부터 신사옥 정상 근무 예정입니다.",
        "date": "2026-04-25",
        "sender": "정총무 <admin@company.com>",
    },
]


def add_dummy_emails():
    client = ChromaClient()

    if client.collection is None:
        logger.error("ChromaDB에 연결할 수 없습니다. Docker가 실행 중인지 확인하세요.")
        return

    existing_ids = set(client.collection.get()["ids"])
    added = 0

    for email in DUMMY_EMAILS:
        if email["email_id"] in existing_ids:
            logger.info(f"이미 존재하는 항목 건너뜀: {email['email_id']}")
            continue

        logger.info(f"추가 중: {email['title']}")
        success = client.add_email(
            email_id=email["email_id"],
            title=email["title"],
            summary=email["summary"],
            date=email["date"],
            sender=email["sender"],
        )
        if success:
            added += 1
            logger.info(f"완료: {email['email_id']}")
        else:
            logger.error(f"실패: {email['email_id']}")

    logger.info(f"총 {added}개 더미 데이터 추가 완료. 현재 DB 총 {client.collection.count()}개.")


if __name__ == "__main__":
    add_dummy_emails()
