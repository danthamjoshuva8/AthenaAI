from fastapi import APIRouter

router = APIRouter()


@router.get("/allocate-test")
def allocate_test():

    return {
        "message":
        "Daily Allocation Engine Ready"
    }