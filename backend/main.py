from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
from backend.core.config import get_settings
from backend.api.v1 import router as api_v1_router
from backend.db.database import DatabaseConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="VAMOS - Distribution Analysis Tool for comparing input data distributions to reference data",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "VAMOS Distribution Analysis Tool",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = DatabaseConnection()
        db_status = "connected" if db.test_connection() else "disconnected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "environment": settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else "production",
            "timestamp": datetime.now().isoformat(),
            "version": settings.VERSION
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API running on {settings.API_HOST}:{settings.API_PORT}")
    
    # Test database connection on startup
    try:
        db = DatabaseConnection()
        if db.test_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️ Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database connection error: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down VAMOS application")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )