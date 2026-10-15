from app.api.crud import resource_router
from app.governance.rollout_gates import ENTRY_CRITERIA, PHASES, REASSESSMENT

router = resource_router("rollout")


@router.get("/meta/criteria")
def criteria():
    return {"phases": PHASES, "entry_criteria": ENTRY_CRITERIA, "reassessment": REASSESSMENT}