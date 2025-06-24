from fastapi import APIRouter
from .routers import analyze, feedback, metrics, configurations, reference, input, training

# Create the main v1 router
router = APIRouter()

# Include all routers with proper prefixes (remove duplicate metrics router)
router.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
router.include_router(configurations.router, prefix="/settings", tags=["settings"])
router.include_router(reference.router, prefix="/reference", tags=["reference"])
router.include_router(input.router, prefix="/input", tags=["input"])
router.include_router(training.router, prefix="/training", tags=["training"])

__all__ = ['router']