from fastapi import APIRouter
from app.api.v1.admin.routes import router as admin_router
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.bookings.routes import router as bookings_router
from app.api.v1.public.routes import router as public_router
from app.api.v1.student.routes import router as student_router
from app.api.v1.super_admin.routes import router as super_admin_router
from app.api.v1.supervisor.routes import router as supervisor_router
from app.api.v1.visitor.routes import router as visitor_router
from app.api.v1.webhooks.routes import router as webhook_router
from app.api.v1.reports.routes import router as reports_router  
from app.api.v1.plans.routes import router as plans_router


api_router = APIRouter()
api_router.include_router(public_router, prefix="/public", tags=["public"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(bookings_router, prefix="/bookings", tags=["bookings"])
api_router.include_router(super_admin_router, prefix="/super-admin", tags=["super-admin"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(supervisor_router, prefix="/supervisor", tags=["supervisor"])
api_router.include_router(student_router, prefix="/student", tags=["student"])
api_router.include_router(visitor_router, prefix="/visitor", tags=["visitor"])
api_router.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])  
api_router.include_router(plans_router, prefix="/plans", tags=["plans"])