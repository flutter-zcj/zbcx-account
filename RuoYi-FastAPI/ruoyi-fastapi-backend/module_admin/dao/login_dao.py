from sqlalchemy import Row, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.do.user_do import SysUser


async def login_by_account(db: AsyncSession, user_name: str) -> Row[tuple[SysUser, SysDept]] | None:
    """
    根据登录账号查询用户信息

    账号既可以是用户名，也可以是用户邮箱；输入内容包含 @ 时同时按邮箱匹配，
    保证邮箱登录与用户名登录共用同一套锁定与错误计数逻辑

    :param db: orm对象
    :param user_name: 用户名或用户邮箱
    :return: 用户对象
    """
    account = (user_name or '').strip()
    conditions = [SysUser.user_name == account]
    if '@' in account:
        conditions.append(SysUser.email == account)
    user = (
        await db.execute(
            select(SysUser, SysDept)
            .where(or_(*conditions), SysUser.del_flag == '0')
            .join(
                SysDept,
                and_(SysUser.dept_id == SysDept.dept_id, SysDept.status == '0', SysDept.del_flag == '0'),
                isouter=True,
            )
            .distinct()
        )
    ).first()

    return user


async def get_user_by_email(db: AsyncSession, email: str) -> SysUser | None:
    """
    根据邮箱查询未删除的用户信息

    注册前用于判断邮箱是否已被占用，避免同一邮箱重复注册

    :param db: orm对象
    :param email: 用户邮箱
    :return: 用户对象
    """
    account = (email or '').strip().lower()
    if not account:
        return None

    return (await db.execute(select(SysUser).where(SysUser.email == account, SysUser.del_flag == '0'))).scalars().first()
