"""
Debug API endpoints (temporary, for troubleshooting)

IMPORTANT: Remove this file in production!
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.company import Company

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/companies")
async def list_all_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List all companies in the database (for debugging).

    Shows: ID, name, domain, user count
    """
    result = await db.execute(select(Company))
    companies = result.scalars().all()

    company_data = []
    for company in companies:
        # Count users in this company
        user_result = await db.execute(
            select(User).where(User.company_id == company.id)
        )
        users = user_result.scalars().all()

        company_data.append({
            "id": str(company.id),
            "name": company.name,
            "domain": company.domain,
            "user_count": len(users),
            "users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role,
                    "is_active": u.is_active
                }
                for u in users
            ]
        })

    return company_data


@router.get("/my-company")
async def get_my_company_details(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed information about current user's company.
    """
    if not current_user.company_id:
        return {"error": "User has no company"}

    # Get company
    company_result = await db.execute(
        select(Company).where(Company.id == current_user.company_id)
    )
    company = company_result.scalar_one_or_none()

    if not company:
        return {"error": "Company not found"}

    # Get all users in this company
    user_result = await db.execute(
        select(User).where(User.company_id == current_user.company_id)
    )
    users = user_result.scalars().all()

    return {
        "current_user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "company_id": str(current_user.company_id),
            "role": current_user.role
        },
        "company": {
            "id": str(company.id),
            "name": company.name,
            "domain": company.domain
        },
        "all_users_in_company": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "company_id": str(u.company_id) if u.company_id else None
            }
            for u in users
        ]
    }


@router.get("/all-users")
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List ALL users in the database (for debugging).

    Shows company_id for each user.
    """
    result = await db.execute(select(User))
    users = result.scalars().all()

    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "company_id": str(user.company_id) if user.company_id else None,
        }
        for user in users
    ]
