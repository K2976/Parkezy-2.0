import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, RulesDep, ServicesDep
from app.api.presenters import review_out
from app.schemas.reviews import ReviewOut, ReviewUpdate

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.patch("/{review_id}", response_model=ReviewOut)
async def update_review(
    review_id: uuid.UUID, body: ReviewUpdate, user: CurrentUser, services: ServicesDep, rules: RulesDep
) -> ReviewOut:
    review = await services.reviews().update(
        user,
        review_id,
        rating=body.rating,
        comment=body.comment or None,
        clear_comment="comment" in body.model_fields_set and not body.comment,
        rules=rules,
    )
    return review_out(review, user)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: uuid.UUID, user: CurrentUser, services: ServicesDep) -> None:
    await services.reviews().delete(user, review_id)
