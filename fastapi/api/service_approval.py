# -*- coding: utf-8 -*-
"""
다단계 결재 시스템 API

기능:
- 결재 상신 (기안)
- 결재 승인/반려
- 결재 현황 조회
- 결재 완료 시 자동 발행

결재 단계:
- 2단계: 기안자 → 1차 결재자 → 2차 결재자(최종)
- 3단계: 기안자 → 1차 결재자 → 2차 결재자 → 3차 결재자(최종)

:copyright: (c) 2025 by wizice.
:license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .auth_middleware import get_current_user, require_role
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/approval",
    tags=["approval"]
)

# DB 설정
db_config = {
    'database': settings.DB_NAME,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'host': settings.DB_HOST,
    'port': settings.DB_PORT
}


# ==================== Pydantic 모델 ====================

class ApproverInfo(BaseModel):
    """결재자 정보"""
    approver_id: str
    approver_name: str
    approver_dept: Optional[str] = ""
    approver_position: Optional[str] = ""


class SubmitApprovalRequest(BaseModel):
    """결재 상신 요청"""
    rule_seq: int = Field(..., description="규정 ID")
    rule_name: str = Field(..., description="규정명")
    rule_pubno: Optional[str] = Field("", description="공포번호")
    total_steps: int = Field(2, ge=2, le=3, description="결재 단계 (2 또는 3)")
    approvers: List[ApproverInfo] = Field(..., description="결재자 목록 (순서대로)")
    comment: Optional[str] = Field("", description="기안 의견")


class ApproveRequest(BaseModel):
    """결재 승인 요청"""
    comment: Optional[str] = Field("", description="결재 의견")


class RejectRequest(BaseModel):
    """결재 반려 요청"""
    comment: str = Field(..., min_length=1, description="반려 사유 (필수)")


# ==================== 헬퍼 함수 ====================

def get_db_manager():
    """DB 매니저 인스턴스 반환"""
    return DatabaseConnectionManager(**db_config)


def log_approval_history(
    workflow_id: int,
    action: str,
    actor_id: str,
    actor_name: str,
    actor_dept: str = "",
    step_id: int = None,
    from_status: str = None,
    to_status: str = None,
    comment: str = "",
    ip_address: str = None,
    user_agent: str = ""
):
    """결재 이력 기록"""
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO wz_approval_history
                        (workflow_id, step_id, action, actor_id, actor_name, actor_dept,
                         from_status, to_status, comment, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    workflow_id, step_id, action, actor_id, actor_name, actor_dept,
                    from_status, to_status, comment, ip_address, user_agent
                ))
                conn.commit()
    except Exception as e:
        logger.error(f"[Approval] 이력 기록 실패: {e}")


def send_notification(
    recipient_id: str,
    recipient_name: str,
    notification_type: str,
    title: str,
    message: str,
    workflow_id: int = None,
    rule_seq: int = None,
    rule_name: str = None,
    sender_id: str = None,
    sender_name: str = None
):
    """
    알림 발송

    알림 유형:
    - APPROVAL_REQUEST: 결재 요청
    - APPROVED: 결재 승인
    - REJECTED: 결재 반려
    - PUBLISHED: 규정 발행
    """
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO wz_notifications
                        (recipient_id, recipient_name, type, title, message,
                         workflow_id, rule_seq, rule_name, sender_id, sender_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING notification_id
                """, (
                    recipient_id, recipient_name, notification_type, title, message,
                    workflow_id, rule_seq, rule_name, sender_id, sender_name
                ))
                notification_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[Notification] 알림 발송: {notification_type} → {recipient_name} (id={notification_id})")
                return notification_id
    except Exception as e:
        logger.error(f"[Notification] 알림 발송 실패: {e}")
        return None


def notify_drafter_rejected(workflow_id: int, rejector_name: str, reject_reason: str):
    """기안자에게 반려 알림 발송"""
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 워크플로우에서 기안자 정보 조회
                cur.execute("""
                    SELECT drafter_id, drafter_name, rule_seq, rule_name
                    FROM wz_approval_workflow
                    WHERE workflow_id = %s
                """, (workflow_id,))
                row = cur.fetchone()
                if row:
                    drafter_id, drafter_name, rule_seq, rule_name = row
                    send_notification(
                        recipient_id=drafter_id,
                        recipient_name=drafter_name,
                        notification_type='REJECTED',
                        title=f'[반려] {rule_name}',
                        message=f'{rejector_name}님이 결재를 반려하였습니다.\n반려 사유: {reject_reason}',
                        workflow_id=workflow_id,
                        rule_seq=rule_seq,
                        rule_name=rule_name,
                        sender_name=rejector_name
                    )
    except Exception as e:
        logger.error(f"[Notification] 반려 알림 발송 실패: {e}")


def notify_next_approver(workflow_id: int, drafter_name: str):
    """다음 결재자에게 결재 요청 알림 발송"""
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 다음 결재자 정보 조회
                cur.execute("""
                    SELECT
                        s.approver_id, s.approver_name, s.step_name,
                        w.rule_seq, w.rule_name
                    FROM wz_approval_workflow w
                    JOIN wz_approval_step s ON w.workflow_id = s.workflow_id
                    WHERE w.workflow_id = %s
                      AND s.step_order = w.current_step + 1
                      AND s.status = 'PENDING'
                """, (workflow_id,))
                row = cur.fetchone()
                if row:
                    approver_id, approver_name, step_name, rule_seq, rule_name = row
                    send_notification(
                        recipient_id=approver_id,
                        recipient_name=approver_name,
                        notification_type='APPROVAL_REQUEST',
                        title=f'[결재요청] {rule_name}',
                        message=f'{drafter_name}님이 {step_name}를 요청하였습니다.',
                        workflow_id=workflow_id,
                        rule_seq=rule_seq,
                        rule_name=rule_name,
                        sender_name=drafter_name
                    )
    except Exception as e:
        logger.error(f"[Notification] 결재 요청 알림 발송 실패: {e}")


def notify_drafter_approved(workflow_id: int, approver_name: str, is_final: bool):
    """기안자에게 승인 알림 발송"""
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT drafter_id, drafter_name, rule_seq, rule_name
                    FROM wz_approval_workflow
                    WHERE workflow_id = %s
                """, (workflow_id,))
                row = cur.fetchone()
                if row:
                    drafter_id, drafter_name, rule_seq, rule_name = row
                    if is_final:
                        title = f'[발행완료] {rule_name}'
                        message = f'최종 결재가 완료되어 규정이 발행되었습니다.'
                        notification_type = 'PUBLISHED'
                    else:
                        title = f'[결재승인] {rule_name}'
                        message = f'{approver_name}님이 결재를 승인하였습니다.'
                        notification_type = 'APPROVED'

                    send_notification(
                        recipient_id=drafter_id,
                        recipient_name=drafter_name,
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        workflow_id=workflow_id,
                        rule_seq=rule_seq,
                        rule_name=rule_name,
                        sender_name=approver_name
                    )
    except Exception as e:
        logger.error(f"[Notification] 승인 알림 발송 실패: {e}")


def publish_rule(rule_seq: int, workflow_id: int):
    """
    결재 완료된 규정 발행 처리

    TODO: 실제 발행 로직 구현
    - 규정 상태 변경
    - PDF 생성
    - 알림 발송 등
    """
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 워크플로우 발행 상태로 변경
                cur.execute("""
                    UPDATE wz_approval_workflow
                    SET status = 'PUBLISHED',
                        published_at = NOW(),
                        updated_at = NOW()
                    WHERE workflow_id = %s
                """, (workflow_id,))

                # TODO: WZ_RULE 테이블의 발행 상태 업데이트
                # cur.execute("""
                #     UPDATE wz_rule
                #     SET wz_status = 'PUBLISHED', ...
                #     WHERE wzruleseq = %s
                # """, (rule_seq,))

                conn.commit()
                logger.info(f"[Approval] 규정 발행 완료: rule_seq={rule_seq}, workflow_id={workflow_id}")
                return True
    except Exception as e:
        logger.error(f"[Approval] 규정 발행 실패: {e}")
        return False


# ==================== API 엔드포인트 ====================

@router.post("/submit")
async def submit_approval(
    request_data: SubmitApprovalRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    결재 상신 (기안)

    새로운 결재 워크플로우를 생성하고 첫 번째 결재자에게 결재 요청을 보냅니다.
    """
    try:
        # 결재자 수 검증
        if len(request_data.approvers) != request_data.total_steps:
            raise HTTPException(
                status_code=400,
                detail=f"결재자 수({len(request_data.approvers)})가 결재 단계({request_data.total_steps})와 일치하지 않습니다."
            )

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. 기존 진행 중인 워크플로우 확인
                cur.execute("""
                    SELECT workflow_id, status
                    FROM wz_approval_workflow
                    WHERE rule_seq = %s AND status IN ('DRAFT', 'PENDING', 'IN_PROGRESS')
                """, (request_data.rule_seq,))
                existing = cur.fetchone()

                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"이미 진행 중인 결재가 있습니다. (상태: {existing[1]})"
                    )

                # 2. 워크플로우 생성
                cur.execute("""
                    INSERT INTO wz_approval_workflow
                        (rule_seq, rule_name, rule_pubno, total_steps, current_step, status,
                         drafter_id, drafter_name, drafter_dept, draft_comment)
                    VALUES (%s, %s, %s, %s, 0, 'PENDING', %s, %s, %s, %s)
                    RETURNING workflow_id
                """, (
                    request_data.rule_seq,
                    request_data.rule_name,
                    request_data.rule_pubno,
                    request_data.total_steps,
                    user.get('id', user.get('username', '')),
                    user.get('name', user.get('username', '')),
                    user.get('department', user.get('dept_name', '')),
                    request_data.comment
                ))
                workflow_id = cur.fetchone()[0]

                # 3. 결재 단계 생성
                step_names = ['1차 결재', '2차 결재', '최종 결재']
                for i, approver in enumerate(request_data.approvers):
                    step_order = i + 1
                    step_name = step_names[i] if request_data.total_steps == 3 else (
                        '1차 결재' if i == 0 else '최종 결재'
                    )

                    cur.execute("""
                        INSERT INTO wz_approval_step
                            (workflow_id, step_order, step_name, approver_id, approver_name,
                             approver_dept, approver_position, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING')
                    """, (
                        workflow_id,
                        step_order,
                        step_name,
                        approver.approver_id,
                        approver.approver_name,
                        approver.approver_dept,
                        approver.approver_position
                    ))

                conn.commit()

                # 4. 이력 기록
                log_approval_history(
                    workflow_id=workflow_id,
                    action='SUBMIT',
                    actor_id=user.get('id', user.get('username', '')),
                    actor_name=user.get('name', user.get('username', '')),
                    actor_dept=user.get('department', ''),
                    from_status='DRAFT',
                    to_status='PENDING',
                    comment=request_data.comment,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get('user-agent', '')
                )

                logger.info(f"[Approval] 결재 상신 완료: workflow_id={workflow_id}, rule_seq={request_data.rule_seq}")

                # 5. 다음 결재자에게 알림 발송
                notify_next_approver(
                    workflow_id=workflow_id,
                    drafter_name=user.get('name', user.get('username', ''))
                )

                return {
                    "success": True,
                    "workflow_id": workflow_id,
                    "message": "결재가 상신되었습니다.",
                    "next_approver": request_data.approvers[0].approver_name
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Approval] 결재 상신 실패: {e}")
        raise HTTPException(status_code=500, detail=f"결재 상신 실패: {str(e)}")


@router.get("/pending")
async def get_pending_approvals(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    내가 결재해야 할 목록 조회

    현재 로그인한 사용자가 결재해야 할 항목들을 반환합니다.
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        w.workflow_id,
                        w.rule_seq,
                        w.rule_name,
                        w.rule_pubno,
                        w.total_steps,
                        w.current_step,
                        w.drafter_name,
                        w.drafter_dept,
                        w.drafted_at,
                        s.step_id,
                        s.step_order,
                        s.step_name
                    FROM wz_approval_workflow w
                    JOIN wz_approval_step s ON w.workflow_id = s.workflow_id
                    WHERE w.status IN ('PENDING', 'IN_PROGRESS')
                      AND s.status = 'PENDING'
                      AND s.step_order = w.current_step + 1
                      AND s.approver_id = %s
                    ORDER BY w.drafted_at DESC
                """, (user_id,))

                rows = cur.fetchall()
                columns = [
                    'workflow_id', 'rule_seq', 'rule_name', 'rule_pubno',
                    'total_steps', 'current_step', 'drafter_name', 'drafter_dept',
                    'drafted_at', 'step_id', 'step_order', 'step_name'
                ]

                pending_list = []
                for row in rows:
                    item = dict(zip(columns, row))
                    item['drafted_at'] = item['drafted_at'].isoformat() if item['drafted_at'] else None
                    pending_list.append(item)

                return {
                    "success": True,
                    "data": pending_list,
                    "count": len(pending_list)
                }

    except Exception as e:
        logger.error(f"[Approval] 대기 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="대기 목록 조회 실패")


@router.get("/my-drafts")
async def get_my_drafts(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    내가 기안한 결재 목록 조회
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        workflow_id,
                        rule_seq,
                        rule_name,
                        rule_pubno,
                        total_steps,
                        current_step,
                        status,
                        drafted_at,
                        completed_at,
                        published_at
                    FROM wz_approval_workflow
                    WHERE drafter_id = %s
                    ORDER BY created_at DESC
                    LIMIT 100
                """, (user_id,))

                rows = cur.fetchall()
                columns = [
                    'workflow_id', 'rule_seq', 'rule_name', 'rule_pubno',
                    'total_steps', 'current_step', 'status',
                    'drafted_at', 'completed_at', 'published_at'
                ]

                drafts = []
                for row in rows:
                    item = dict(zip(columns, row))
                    for date_field in ['drafted_at', 'completed_at', 'published_at']:
                        if item[date_field]:
                            item[date_field] = item[date_field].isoformat()
                    drafts.append(item)

                return {
                    "success": True,
                    "data": drafts,
                    "count": len(drafts)
                }

    except Exception as e:
        logger.error(f"[Approval] 기안 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="기안 목록 조회 실패")


@router.post("/approve/{workflow_id}")
async def approve_workflow(
    workflow_id: int,
    request_data: ApproveRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    결재 승인

    현재 단계를 승인하고 다음 단계로 진행합니다.
    최종 단계인 경우 자동으로 발행 처리됩니다.
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. 워크플로우 및 현재 단계 조회
                cur.execute("""
                    SELECT
                        w.workflow_id,
                        w.rule_seq,
                        w.rule_name,
                        w.total_steps,
                        w.current_step,
                        w.status,
                        s.step_id,
                        s.step_order,
                        s.approver_id
                    FROM wz_approval_workflow w
                    JOIN wz_approval_step s ON w.workflow_id = s.workflow_id
                    WHERE w.workflow_id = %s
                      AND s.step_order = w.current_step + 1
                      AND s.status = 'PENDING'
                """, (workflow_id,))

                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="결재할 항목을 찾을 수 없습니다.")

                (wf_id, rule_seq, rule_name, total_steps, current_step,
                 wf_status, step_id, step_order, approver_id) = row

                # 2. 결재 권한 확인
                if approver_id != user_id:
                    raise HTTPException(status_code=403, detail="결재 권한이 없습니다.")

                # 3. 현재 단계 승인 처리
                cur.execute("""
                    UPDATE wz_approval_step
                    SET status = 'APPROVED',
                        comment = %s,
                        acted_at = NOW()
                    WHERE step_id = %s
                """, (request_data.comment, step_id))

                # 4. 다음 단계로 진행 또는 완료 처리
                is_final = (step_order == total_steps)

                if is_final:
                    # 최종 결재 → 승인 완료 및 자동 발행
                    cur.execute("""
                        UPDATE wz_approval_workflow
                        SET current_step = %s,
                            status = 'APPROVED',
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE workflow_id = %s
                    """, (step_order, workflow_id))
                    conn.commit()

                    # 자동 발행
                    publish_rule(rule_seq, workflow_id)

                    message = "최종 결재가 완료되어 규정이 발행되었습니다."
                else:
                    # 다음 단계로 진행
                    cur.execute("""
                        UPDATE wz_approval_workflow
                        SET current_step = %s,
                            status = 'IN_PROGRESS',
                            updated_at = NOW()
                        WHERE workflow_id = %s
                    """, (step_order, workflow_id))
                    conn.commit()

                    message = f"{step_order}차 결재가 완료되었습니다. 다음 결재자에게 전달됩니다."

                # 5. 이력 기록
                log_approval_history(
                    workflow_id=workflow_id,
                    step_id=step_id,
                    action='APPROVE',
                    actor_id=user_id,
                    actor_name=user.get('name', user.get('username', '')),
                    actor_dept=user.get('department', ''),
                    from_status=wf_status,
                    to_status='APPROVED' if is_final else 'IN_PROGRESS',
                    comment=request_data.comment,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get('user-agent', '')
                )

                logger.info(f"[Approval] 결재 승인: workflow_id={workflow_id}, step={step_order}, final={is_final}")

                # 6. 알림 발송
                approver_name = user.get('name', user.get('username', ''))
                notify_drafter_approved(
                    workflow_id=workflow_id,
                    approver_name=approver_name,
                    is_final=is_final
                )

                # 최종 결재가 아닌 경우 다음 결재자에게 알림
                if not is_final:
                    notify_next_approver(
                        workflow_id=workflow_id,
                        drafter_name=approver_name
                    )

                return {
                    "success": True,
                    "message": message,
                    "is_final": is_final,
                    "workflow_id": workflow_id,
                    "current_step": step_order
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Approval] 결재 승인 실패: {e}")
        raise HTTPException(status_code=500, detail=f"결재 승인 실패: {str(e)}")


@router.post("/reject/{workflow_id}")
async def reject_workflow(
    workflow_id: int,
    request_data: RejectRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    결재 반려

    현재 단계에서 반려하면 워크플로우 전체가 반려됩니다.
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. 워크플로우 및 현재 단계 조회
                cur.execute("""
                    SELECT
                        w.workflow_id,
                        w.rule_seq,
                        w.status,
                        s.step_id,
                        s.step_order,
                        s.approver_id
                    FROM wz_approval_workflow w
                    JOIN wz_approval_step s ON w.workflow_id = s.workflow_id
                    WHERE w.workflow_id = %s
                      AND s.step_order = w.current_step + 1
                      AND s.status = 'PENDING'
                """, (workflow_id,))

                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="반려할 항목을 찾을 수 없습니다.")

                wf_id, rule_seq, wf_status, step_id, step_order, approver_id = row

                # 2. 반려 권한 확인
                if approver_id != user_id:
                    raise HTTPException(status_code=403, detail="결재 권한이 없습니다.")

                # 3. 현재 단계 반려 처리
                cur.execute("""
                    UPDATE wz_approval_step
                    SET status = 'REJECTED',
                        comment = %s,
                        acted_at = NOW()
                    WHERE step_id = %s
                """, (request_data.comment, step_id))

                # 4. 워크플로우 반려 상태로 변경
                cur.execute("""
                    UPDATE wz_approval_workflow
                    SET status = 'REJECTED',
                        completed_at = NOW(),
                        updated_at = NOW()
                    WHERE workflow_id = %s
                """, (workflow_id,))

                conn.commit()

                # 5. 이력 기록
                log_approval_history(
                    workflow_id=workflow_id,
                    step_id=step_id,
                    action='REJECT',
                    actor_id=user_id,
                    actor_name=user.get('name', user.get('username', '')),
                    actor_dept=user.get('department', ''),
                    from_status=wf_status,
                    to_status='REJECTED',
                    comment=request_data.comment,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get('user-agent', '')
                )

                logger.info(f"[Approval] 결재 반려: workflow_id={workflow_id}, step={step_order}")

                # 6. 기안자에게 반려 알림 발송
                notify_drafter_rejected(
                    workflow_id=workflow_id,
                    rejector_name=user.get('name', user.get('username', '')),
                    reject_reason=request_data.comment
                )

                return {
                    "success": True,
                    "message": f"결재가 반려되었습니다. 반려 사유: {request_data.comment}",
                    "workflow_id": workflow_id
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Approval] 결재 반려 실패: {e}")
        raise HTTPException(status_code=500, detail=f"결재 반려 실패: {str(e)}")


@router.get("/status/{workflow_id}")
async def get_approval_status(
    workflow_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    결재 진행 상태 조회

    특정 워크플로우의 상세 진행 상태를 반환합니다.
    """
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 워크플로우 조회
                cur.execute("""
                    SELECT
                        workflow_id, rule_seq, rule_name, rule_pubno,
                        total_steps, current_step, status,
                        drafter_id, drafter_name, drafter_dept, draft_comment,
                        drafted_at, completed_at, published_at
                    FROM wz_approval_workflow
                    WHERE workflow_id = %s
                """, (workflow_id,))

                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="워크플로우를 찾을 수 없습니다.")

                columns = [
                    'workflow_id', 'rule_seq', 'rule_name', 'rule_pubno',
                    'total_steps', 'current_step', 'status',
                    'drafter_id', 'drafter_name', 'drafter_dept', 'draft_comment',
                    'drafted_at', 'completed_at', 'published_at'
                ]
                workflow = dict(zip(columns, row))

                for date_field in ['drafted_at', 'completed_at', 'published_at']:
                    if workflow[date_field]:
                        workflow[date_field] = workflow[date_field].isoformat()

                # 결재 단계 조회
                cur.execute("""
                    SELECT
                        step_id, step_order, step_name,
                        approver_id, approver_name, approver_dept, approver_position,
                        status, comment, acted_at
                    FROM wz_approval_step
                    WHERE workflow_id = %s
                    ORDER BY step_order
                """, (workflow_id,))

                step_columns = [
                    'step_id', 'step_order', 'step_name',
                    'approver_id', 'approver_name', 'approver_dept', 'approver_position',
                    'status', 'comment', 'acted_at'
                ]
                steps = []
                for step_row in cur.fetchall():
                    step = dict(zip(step_columns, step_row))
                    if step['acted_at']:
                        step['acted_at'] = step['acted_at'].isoformat()
                    steps.append(step)

                workflow['steps'] = steps

                return {
                    "success": True,
                    "data": workflow
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Approval] 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="상태 조회 실패")


@router.get("/history/{rule_seq}")
async def get_approval_history(
    rule_seq: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    규정별 결재 이력 조회

    특정 규정의 모든 결재 이력을 반환합니다.
    """
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        h.history_id,
                        h.workflow_id,
                        h.action,
                        h.actor_id,
                        h.actor_name,
                        h.actor_dept,
                        h.from_status,
                        h.to_status,
                        h.comment,
                        h.created_at,
                        w.rule_name
                    FROM wz_approval_history h
                    JOIN wz_approval_workflow w ON h.workflow_id = w.workflow_id
                    WHERE w.rule_seq = %s
                    ORDER BY h.created_at DESC
                    LIMIT 100
                """, (rule_seq,))

                columns = [
                    'history_id', 'workflow_id', 'action',
                    'actor_id', 'actor_name', 'actor_dept',
                    'from_status', 'to_status', 'comment',
                    'created_at', 'rule_name'
                ]

                history = []
                for row in cur.fetchall():
                    item = dict(zip(columns, row))
                    if item['created_at']:
                        item['created_at'] = item['created_at'].isoformat()
                    history.append(item)

                return {
                    "success": True,
                    "data": history,
                    "count": len(history)
                }

    except Exception as e:
        logger.error(f"[Approval] 이력 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="이력 조회 실패")


@router.get("/users/search")
async def search_approvers(
    q: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    결재자 검색

    결재자로 지정할 사용자를 검색합니다.
    """
    try:
        if len(q) < 2:
            return {"success": True, "data": [], "count": 0}

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # users 테이블에서 검색
                cur.execute("""
                    SELECT
                        username as id,
                        name,
                        department,
                        position
                    FROM users
                    WHERE name LIKE %s OR username LIKE %s
                    ORDER BY name
                    LIMIT 20
                """, (f'%{q}%', f'%{q}%'))

                columns = ['id', 'name', 'department', 'position']
                users = []
                for row in cur.fetchall():
                    users.append(dict(zip(columns, row)))

                return {
                    "success": True,
                    "data": users,
                    "count": len(users)
                }

    except Exception as e:
        logger.error(f"[Approval] 사용자 검색 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 검색 실패")


# ==================== 알림 API 엔드포인트 ====================

@router.get("/notifications")
async def get_notifications(
    limit: int = 20,
    unread_only: bool = False,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    내 알림 목록 조회

    현재 로그인한 사용자의 알림 목록을 반환합니다.
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        notification_id,
                        type,
                        title,
                        message,
                        workflow_id,
                        rule_seq,
                        rule_name,
                        sender_name,
                        is_read,
                        read_at,
                        created_at
                    FROM wz_notifications
                    WHERE recipient_id = %s
                """
                params = [user_id]

                if unread_only:
                    query += " AND is_read = FALSE"

                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, params)

                columns = [
                    'notification_id', 'type', 'title', 'message',
                    'workflow_id', 'rule_seq', 'rule_name', 'sender_name',
                    'is_read', 'read_at', 'created_at'
                ]

                notifications = []
                for row in cur.fetchall():
                    item = dict(zip(columns, row))
                    for date_field in ['read_at', 'created_at']:
                        if item[date_field]:
                            item[date_field] = item[date_field].isoformat()
                    notifications.append(item)

                # 읽지 않은 알림 수
                cur.execute("""
                    SELECT COUNT(*)
                    FROM wz_notifications
                    WHERE recipient_id = %s AND is_read = FALSE
                """, (user_id,))
                unread_count = cur.fetchone()[0]

                return {
                    "success": True,
                    "data": notifications,
                    "count": len(notifications),
                    "unread_count": unread_count
                }

    except Exception as e:
        logger.error(f"[Notification] 알림 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="알림 조회 실패")


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    알림 읽음 처리
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE wz_notifications
                    SET is_read = TRUE, read_at = NOW()
                    WHERE notification_id = %s AND recipient_id = %s
                    RETURNING notification_id
                """, (notification_id, user_id))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

                conn.commit()

                return {
                    "success": True,
                    "message": "알림을 읽음 처리했습니다."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Notification] 읽음 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="읽음 처리 실패")


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    모든 알림 읽음 처리
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE wz_notifications
                    SET is_read = TRUE, read_at = NOW()
                    WHERE recipient_id = %s AND is_read = FALSE
                """, (user_id,))

                updated_count = cur.rowcount
                conn.commit()

                return {
                    "success": True,
                    "message": f"{updated_count}개의 알림을 읽음 처리했습니다.",
                    "updated_count": updated_count
                }

    except Exception as e:
        logger.error(f"[Notification] 전체 읽음 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="전체 읽음 처리 실패")


@router.get("/notifications/count")
async def get_unread_notification_count(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    읽지 않은 알림 수 조회
    """
    try:
        user_id = user.get('id', user.get('username', ''))

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM wz_notifications
                    WHERE recipient_id = %s AND is_read = FALSE
                """, (user_id,))

                unread_count = cur.fetchone()[0]

                return {
                    "success": True,
                    "unread_count": unread_count
                }

    except Exception as e:
        logger.error(f"[Notification] 알림 수 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="알림 수 조회 실패")
