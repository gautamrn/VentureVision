from fastapi import APIRouter, Depends, HTTPException

from app.feedback.store import FeedbackStore, getFeedbackStore
from app.middleware.rateLimiter import rateLimit
from app.routers.analyze import verifyAdminKey
from app.schemas.feedback import FeedbackCreated, FeedbackList, FeedbackRecord, FeedbackRequest, FeedbackReview, FeedbackView
from app.schemas.models import SealedMemo
from app.shares.sealing import verifySeal

router = APIRouter()

FEEDBACK_PER_HOUR = 60


@router.post(
    "/feedback",
    response_model=FeedbackCreated,
    status_code=201,
    dependencies=[Depends(rateLimit("feedback", FEEDBACK_PER_HOUR))],
)
async def submitFeedback(request: FeedbackRequest, store: FeedbackStore = Depends(getFeedbackStore)):
    verified = False
    if request.seal is not None:
        sealed = SealedMemo(pitch=request.pitch, mode=request.mode, memo=request.memo, seal=request.seal)
        if not verifySeal(sealed):
            raise HTTPException(status_code=403, detail="This memo was modified after the server produced it.")
        verified = True
    record = store.add(
        pitch=request.pitch,
        mode=request.mode,
        annotation=request.memo.pitch_annotations[request.annotation_index],
        userVerdict=request.user_verdict,
        origin="demo" if request.demo_sample_id else "live",
        verified=verified,
    )
    return FeedbackCreated(feedback_id=record.feedback_id, verified=record.verified)


@router.get("/admin/feedback", response_model=FeedbackList, dependencies=[Depends(verifyAdminKey)])
async def listFeedback(view: FeedbackView = "disagreements", store: FeedbackStore = Depends(getFeedbackStore)):
    return store.listRecords(view)


@router.post(
    "/admin/feedback/{feedbackId}/review", response_model=FeedbackRecord, dependencies=[Depends(verifyAdminKey)]
)
async def reviewFeedback(feedbackId: int, review: FeedbackReview, store: FeedbackStore = Depends(getFeedbackStore)):
    record = store.review(feedbackId, review)
    if record is None:
        raise HTTPException(status_code=404, detail="Feedback not found, or already exported to candidates.")
    return record
