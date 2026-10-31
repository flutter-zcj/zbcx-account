from datetime import date
from typing import Any

from sqlalchemy import String, and_, case, delete, func, literal, or_, select, union_all, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from common.vo import PageModel
from module_account.entity.do.account_do import (
    AcctAccount,
    AcctBill,
    AcctBudget,
    AcctCategory,
    AcctLedger,
    AcctLedgerMember,
    AcctRecurring,
)
from module_account.entity.vo.account_vo import (
    AccountModel,
    BillModel,
    BillPageQueryModel,
    CategoryModel,
    LedgerModel,
    RecurringModel,
)
from utils.page_util import PageUtil


class AccountCategoryDao:
    """
    记账分类数据库操作层
    """

    @classmethod
    async def get_category_list(cls, db: AsyncSession, user_id: int, category_type: str | None = None) -> list[AcctCategory]:
        """
        查询指定用户的分类列表

        :param db: orm对象
        :param user_id: 用户ID
        :param category_type: 分类类型，为空时查询全部
        :return: 分类列表
        """
        query = (
            select(AcctCategory)
            .where(
                AcctCategory.user_id == user_id,
                AcctCategory.del_flag == '0',
                AcctCategory.category_type == category_type if category_type else True,
            )
            .order_by(AcctCategory.category_type.asc(), AcctCategory.sort_num.asc(), AcctCategory.category_id.asc())
        )

        return list((await db.execute(query)).scalars().all())

    @classmethod
    async def get_category_by_id(cls, db: AsyncSession, category_id: int) -> AcctCategory | None:
        """
        根据分类ID查询分类

        :param db: orm对象
        :param category_id: 分类ID
        :return: 分类对象
        """
        return (
            await db.execute(
                select(AcctCategory).where(AcctCategory.category_id == category_id, AcctCategory.del_flag == '0')
            )
        ).scalars().first()

    @classmethod
    async def add_category_dao(cls, db: AsyncSession, category: CategoryModel) -> AcctCategory:
        """
        新增分类

        :param db: orm对象
        :param category: 分类对象
        :return: 新增后的分类对象
        """
        db_category = AcctCategory(**category.model_dump(exclude={'create_time', 'update_time'}, exclude_none=True))
        db.add(db_category)
        await db.flush()

        return db_category

    @classmethod
    async def edit_category_dao(cls, db: AsyncSession, category: dict) -> None:
        """
        修改分类

        :param db: orm对象
        :param category: 待更新的分类字典
        :return:
        """
        await db.execute(
            update(AcctCategory).where(AcctCategory.category_id == category.get('category_id')).values(**category)
        )

    @classmethod
    async def delete_category_dao(cls, db: AsyncSession, category_ids: list[int]) -> None:
        """
        逻辑删除分类

        :param db: orm对象
        :param category_ids: 分类ID列表
        :return:
        """
        if category_ids:
            await db.execute(
                update(AcctCategory).where(AcctCategory.category_id.in_(category_ids)).values(del_flag='2')
            )

    @classmethod
    async def count_category_name(cls, db: AsyncSession, user_id: int, category_type: str, category_name: str) -> int:
        """
        统计同名分类数量，用于唯一性校验

        :param db: orm对象
        :param user_id: 用户ID
        :param category_type: 分类类型
        :param category_name: 分类名称
        :return: 数量
        """
        return (
            await db.execute(
                select(func.count())
                .select_from(AcctCategory)
                .where(
                    AcctCategory.user_id == user_id,
                    AcctCategory.category_type == category_type,
                    AcctCategory.category_name == category_name,
                    AcctCategory.del_flag == '0',
                )
            )
        ).scalar_one()

    @classmethod
    async def count_bill_by_category(cls, db: AsyncSession, category_ids: list[int]) -> int:
        """
        统计分类下挂载的账单数量，用于删除前提示

        :param db: orm对象
        :param category_ids: 分类ID列表
        :return: 账单数量
        """
        if not category_ids:
            return 0

        return (
            await db.execute(
                select(func.count())
                .select_from(AcctBill)
                .where(AcctBill.category_id.in_(category_ids), AcctBill.del_flag == '0')
            )
        ).scalar_one()


class AccountAccountDao:
    """
    记账资产账户数据库操作层
    """

    @classmethod
    async def get_account_list(cls, db: AsyncSession, user_id: int) -> list[AcctAccount]:
        """
        查询指定用户的账户列表

        :param db: orm对象
        :param user_id: 用户ID
        :return: 账户列表
        """
        query = (
            select(AcctAccount)
            .where(AcctAccount.user_id == user_id, AcctAccount.del_flag == '0')
            .order_by(AcctAccount.sort_num.asc(), AcctAccount.account_id.asc())
        )

        return list((await db.execute(query)).scalars().all())

    @classmethod
    async def get_account_by_id(cls, db: AsyncSession, account_id: int) -> AcctAccount | None:
        """
        根据账户ID查询账户

        :param db: orm对象
        :param account_id: 账户ID
        :return: 账户对象
        """
        return (
            await db.execute(
                select(AcctAccount).where(AcctAccount.account_id == account_id, AcctAccount.del_flag == '0')
            )
        ).scalars().first()

    @classmethod
    async def add_account_dao(cls, db: AsyncSession, account: AccountModel) -> AcctAccount:
        """
        新增账户

        :param db: orm对象
        :param account: 账户对象
        :return: 新增后的账户对象
        """
        payload = account.model_dump(
            exclude={'create_time', 'update_time', 'balance', 'expense', 'income', 'account_id'},
            exclude_none=True,
        )
        db_account = AcctAccount(**payload)
        db.add(db_account)
        await db.flush()

        return db_account

    @classmethod
    async def edit_account_dao(cls, db: AsyncSession, account: dict) -> None:
        """
        修改账户

        :param db: orm对象
        :param account: 待更新的账户字典
        :return:
        """
        await db.execute(
            update(AcctAccount).where(AcctAccount.account_id == account.get('account_id')).values(**account)
        )

    @classmethod
    async def delete_account_dao(cls, db: AsyncSession, account_ids: list[int]) -> None:
        """
        逻辑删除账户

        :param db: orm对象
        :param account_ids: 账户ID列表
        :return:
        """
        if account_ids:
            await db.execute(
                update(AcctAccount).where(AcctAccount.account_id.in_(account_ids)).values(del_flag='2')
            )

    @classmethod
    async def count_account_name(cls, db: AsyncSession, user_id: int, account_name: str, exclude_id: int | None = None) -> int:
        """
        统计同名账户数量，用于唯一性校验

        :param db: orm对象
        :param user_id: 用户ID
        :param account_name: 账户名称
        :param exclude_id: 需要排除的账户ID（编辑场景）
        :return: 数量
        """
        return (
            await db.execute(
                select(func.count())
                .select_from(AcctAccount)
                .where(
                    AcctAccount.user_id == user_id,
                    AcctAccount.account_name == account_name,
                    AcctAccount.del_flag == '0',
                    AcctAccount.account_id != exclude_id if exclude_id else True,
                )
            )
        ).scalar_one()

    @classmethod
    async def sum_delta_by_account(cls, db: AsyncSession, user_id: int) -> dict[int, dict[str, float]]:
        """
        聚合每个账户的余额变动额、累计支出与累计收入

        余额 = 期初余额 + delta；delta 由收入、支出、转账进出三部分组成

        :param db: orm对象
        :param user_id: 用户ID
        :return: {account_id: {'delta': x, 'expense': y, 'income': z}}
        """
        # 收入 / 支出
        income_expense = (
            select(
                AcctBill.account_id.label('acc_id'),
                func.sum(case((AcctBill.bill_type == '1', AcctBill.amount), else_=-AcctBill.amount)).label('delta'),
                func.sum(case((AcctBill.bill_type == '0', AcctBill.amount), else_=literal(0))).label('expense'),
                func.sum(case((AcctBill.bill_type == '1', AcctBill.amount), else_=literal(0))).label('income'),
            )
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.bill_type.in_(['0', '1']),
                AcctBill.account_id.isnot(None),
            )
            .group_by(AcctBill.account_id)
        )
        # 转账转出
        transfer_out = (
            select(
                AcctBill.account_id.label('acc_id'),
                func.sum(-AcctBill.amount).label('delta'),
                func.sum(literal(0)).label('expense'),
                func.sum(literal(0)).label('income'),
            )
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.bill_type == '2',
                AcctBill.account_id.isnot(None),
            )
            .group_by(AcctBill.account_id)
        )
        # 转账转入
        transfer_in = (
            select(
                AcctBill.to_account_id.label('acc_id'),
                func.sum(AcctBill.amount).label('delta'),
                func.sum(literal(0)).label('expense'),
                func.sum(literal(0)).label('income'),
            )
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.bill_type == '2',
                AcctBill.to_account_id.isnot(None),
            )
            .group_by(AcctBill.to_account_id)
        )

        union_query = union_all(income_expense, transfer_out, transfer_in).subquery()
        query = select(
            union_query.c.acc_id,
            func.sum(union_query.c.delta).label('delta'),
            func.sum(union_query.c.expense).label('expense'),
            func.sum(union_query.c.income).label('income'),
        ).group_by(union_query.c.acc_id)

        rows = (await db.execute(query)).mappings().all()

        return {
            int(row['acc_id']): {
                'delta': float(row['delta'] or 0),
                'expense': float(row['expense'] or 0),
                'income': float(row['income'] or 0),
            }
            for row in rows
        }

    @classmethod
    async def count_bill_by_account(cls, db: AsyncSession, account_ids: list[int]) -> int:
        """
        统计账户下挂载的账单数量

        :param db: orm对象
        :param account_ids: 账户ID列表
        :return: 账单数量
        """
        if not account_ids:
            return 0

        return (
            await db.execute(
                select(func.count())
                .select_from(AcctBill)
                .where(
                    AcctBill.del_flag == '0',
                    or_(AcctBill.account_id.in_(account_ids), AcctBill.to_account_id.in_(account_ids)),
                )
            )
        ).scalar_one()


class AccountBillDao:
    """
    记账账单数据库操作层
    """

    @classmethod
    async def get_bill_list(
        cls,
        db: AsyncSession,
        user_id: int,
        query_object: BillPageQueryModel,
        is_page: bool = False,
        ledger_id: int | None = None,
    ) -> PageModel | list[dict[str, Any]]:
        """
        分页查询账单列表

        :param db: orm对象
        :param user_id: 用户ID
        :param query_object: 查询参数
        :param is_page: 是否分页
        :return: 账单列表
        """
        from_account = aliased(AcctAccount)
        to_account = aliased(AcctAccount)
        keyword = (query_object.keyword or '').strip()

        query = (
            select(
                AcctBill.bill_id,
                AcctBill.category_id,
                AcctBill.bill_type,
                AcctBill.amount,
                AcctBill.bill_date,
                AcctBill.pay_method,
                AcctBill.account_id,
                AcctBill.to_account_id,
                AcctBill.tag,
                AcctBill.images,
                AcctBill.remark,
                AcctBill.create_time,
                AcctCategory.category_name,
                AcctCategory.icon.label('category_icon'),
                AcctCategory.color.label('category_color'),
                from_account.account_name.label('account_name'),
                to_account.account_name.label('to_account_name'),
            )
            .outerjoin(AcctCategory, AcctCategory.category_id == AcctBill.category_id)
            .outerjoin(from_account, from_account.account_id == AcctBill.account_id)
            .outerjoin(to_account, to_account.account_id == AcctBill.to_account_id)
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.ledger_id == ledger_id if ledger_id else True,
                AcctBill.bill_type == query_object.bill_type if query_object.bill_type else True,
                AcctBill.category_id == query_object.category_id if query_object.category_id else True,
                AcctBill.bill_date >= date.fromisoformat(query_object.begin_date) if query_object.begin_date else True,
                AcctBill.bill_date <= date.fromisoformat(query_object.end_date) if query_object.end_date else True,
                AcctBill.tag.like(f'%{query_object.tag}%') if query_object.tag else True,
                or_(
                    AcctBill.account_id == query_object.account_id,
                    AcctBill.to_account_id == query_object.account_id,
                )
                if query_object.account_id
                else True,
                or_(
                    AcctBill.remark.like(f'%{keyword}%'),
                    AcctBill.tag.like(f'%{keyword}%'),
                    AcctCategory.category_name.like(f'%{keyword}%'),
                    AcctBill.amount.cast(String).like(f'%{keyword}%'),
                )
                if keyword
                else True,
            )
            .order_by(AcctBill.bill_date.desc(), AcctBill.bill_id.desc())
        )

        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_bill_by_id(cls, db: AsyncSession, bill_id: int) -> AcctBill | None:
        """
        根据账单ID查询账单

        :param db: orm对象
        :param bill_id: 账单ID
        :return: 账单对象
        """
        return (
            await db.execute(select(AcctBill).where(AcctBill.bill_id == bill_id, AcctBill.del_flag == '0'))
        ).scalars().first()

    @classmethod
    async def add_bill_dao(cls, db: AsyncSession, bill: BillModel) -> AcctBill:
        """
        新增账单

        :param db: orm对象
        :param bill: 账单对象
        :return: 新增后的账单对象
        """
        payload = bill.model_dump(
            exclude={
                'create_time',
                'update_time',
                'category_name',
                'category_icon',
                'category_color',
                'account_name',
                'to_account_name',
                'bill_id',
            },
            exclude_none=True,
        )
        db_bill = AcctBill(**payload)
        db.add(db_bill)
        await db.flush()

        return db_bill

    @classmethod
    async def edit_bill_dao(cls, db: AsyncSession, bill: dict) -> None:
        """
        修改账单

        :param db: orm对象
        :param bill: 待更新的账单字典
        :return:
        """
        await db.execute(update(AcctBill).where(AcctBill.bill_id == bill.get('bill_id')).values(**bill))

    @classmethod
    async def delete_bill_dao(cls, db: AsyncSession, bill_ids: list[int]) -> None:
        """
        逻辑删除账单

        :param db: orm对象
        :param bill_ids: 账单ID列表
        :return:
        """
        if bill_ids:
            await db.execute(update(AcctBill).where(AcctBill.bill_id.in_(bill_ids)).values(del_flag='2'))

    @classmethod
    async def sum_by_type(
        cls,
        db: AsyncSession,
        user_id: int,
        begin_date: str | None = None,
        end_date: str | None = None,
        ledger_id: int | None = None,
    ) -> dict[str, Any]:
        """
        统计指定时间范围内的收入、支出合计与笔数（转账不计入）

        :param db: orm对象
        :param user_id: 用户ID
        :param begin_date: 开始日期
        :param end_date: 结束日期
        :return: 汇总字典
        """
        query = (
            select(
                AcctBill.bill_type,
                func.coalesce(func.sum(AcctBill.amount), 0).label('amount'),
                func.count().label('bill_count'),
            )
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.ledger_id == ledger_id if ledger_id else True,
                AcctBill.bill_type.in_(['0', '1']),
                AcctBill.bill_date >= date.fromisoformat(begin_date) if begin_date else True,
                AcctBill.bill_date <= date.fromisoformat(end_date) if end_date else True,
            )
            .group_by(AcctBill.bill_type)
        )
        rows = (await db.execute(query)).mappings().all()
        result = {'0': {'amount': 0.0, 'bill_count': 0}, '1': {'amount': 0.0, 'bill_count': 0}}
        for row in rows:
            result[row['bill_type']] = {'amount': float(row['amount']), 'bill_count': int(row['bill_count'])}

        return result

    @classmethod
    async def stat_by_category(
        cls,
        db: AsyncSession,
        user_id: int,
        bill_type: str,
        begin_date: str | None = None,
        end_date: str | None = None,
        ledger_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        按分类统计金额

        :param db: orm对象
        :param user_id: 用户ID
        :param bill_type: 账单类型
        :param begin_date: 开始日期
        :param end_date: 结束日期
        :return: 分类统计列表
        """
        query = (
            select(
                AcctBill.category_id,
                AcctCategory.category_name,
                AcctCategory.color.label('category_color'),
                AcctCategory.icon.label('category_icon'),
                func.coalesce(func.sum(AcctBill.amount), 0).label('amount'),
                func.count().label('bill_count'),
            )
            .outerjoin(AcctCategory, AcctCategory.category_id == AcctBill.category_id)
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.ledger_id == ledger_id if ledger_id else True,
                AcctBill.bill_type == bill_type,
                AcctBill.bill_date >= date.fromisoformat(begin_date) if begin_date else True,
                AcctBill.bill_date <= date.fromisoformat(end_date) if end_date else True,
            )
            .group_by(AcctBill.category_id, AcctCategory.category_name, AcctCategory.color, AcctCategory.icon)
            .order_by(func.sum(AcctBill.amount).desc())
        )

        return [dict(row) for row in (await db.execute(query)).mappings().all()]

    @classmethod
    async def stat_top_bills(
        cls,
        db: AsyncSession,
        user_id: int,
        bill_type: str = '0',
        begin_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        单笔金额排行榜

        :param db: orm对象
        :param user_id: 用户ID
        :param bill_type: 账单类型
        :param begin_date: 开始日期
        :param end_date: 结束日期
        :param limit: 返回条数
        :return: 排行列表
        """
        query = (
            select(
                AcctBill.bill_id,
                AcctBill.amount,
                AcctBill.remark,
                AcctBill.tag,
                AcctCategory.category_name,
                AcctCategory.icon.label('category_icon'),
                AcctCategory.color.label('category_color'),
            )
            .outerjoin(AcctCategory, AcctCategory.category_id == AcctBill.category_id)
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.bill_type == bill_type,
                AcctBill.bill_date >= date.fromisoformat(begin_date) if begin_date else True,
                AcctBill.bill_date <= date.fromisoformat(end_date) if end_date else True,
            )
            .order_by(AcctBill.amount.desc())
            .limit(limit)
        )

        return [dict(row) for row in (await db.execute(query)).mappings().all()]

    @classmethod
    async def stat_by_month(cls, db: AsyncSession, user_id: int, months: int = 6) -> list[dict[str, Any]]:
        """
        按月统计收支趋势

        :param db: orm对象
        :param user_id: 用户ID
        :param months: 统计月份数量
        :return: 月度统计列表
        """
        month_expr = func.to_char(AcctBill.bill_date, 'YYYY-MM')
        query = (
            select(
                month_expr.label('month'),
                func.coalesce(
                    func.sum(case((AcctBill.bill_type == '1', AcctBill.amount), else_=0)), 0
                ).label('income'),
                func.coalesce(
                    func.sum(case((AcctBill.bill_type == '0', AcctBill.amount), else_=0)), 0
                ).label('expense'),
            )
            .where(AcctBill.user_id == user_id, AcctBill.del_flag == '0')
            .group_by(month_expr)
            .order_by(month_expr.desc())
            .limit(months)
        )
        rows = (await db.execute(query)).mappings().all()

        return [
            {'month': row['month'], 'income': float(row['income']), 'expense': float(row['expense'])}
            for row in reversed(rows)
        ]

    @classmethod
    async def sum_expense_by_category(
        cls, db: AsyncSession, user_id: int, begin_date: str, end_date: str
    ) -> dict[int, float]:
        """
        按分类聚合指定区间内的支出金额，用于预算执行进度

        :param db: orm对象
        :param user_id: 用户ID
        :param begin_date: 开始日期
        :param end_date: 结束日期
        :return: {category_id: 支出合计}
        """
        query = (
            select(AcctBill.category_id, func.coalesce(func.sum(AcctBill.amount), 0).label('amount'))
            .where(
                AcctBill.user_id == user_id,
                AcctBill.del_flag == '0',
                AcctBill.bill_type == '0',
                AcctBill.bill_date >= date.fromisoformat(begin_date),
                AcctBill.bill_date <= date.fromisoformat(end_date),
            )
            .group_by(AcctBill.category_id)
        )
        rows = (await db.execute(query)).mappings().all()

        return {int(row['category_id']): float(row['amount']) for row in rows if row['category_id']}


class AccountBudgetDao:
    """
    记账预算数据库操作层
    """

    @classmethod
    async def get_budget_list(cls, db: AsyncSession, user_id: int, budget_month: str) -> list[AcctBudget]:
        """
        查询指定月份的预算列表

        :param db: orm对象
        :param user_id: 用户ID
        :param budget_month: 预算月份
        :return: 预算列表
        """
        query = select(AcctBudget).where(AcctBudget.user_id == user_id, AcctBudget.budget_month == budget_month)

        return list((await db.execute(query)).scalars().all())

    @classmethod
    async def get_budget_by_id(cls, db: AsyncSession, budget_id: int) -> AcctBudget | None:
        """
        根据预算ID查询预算

        :param db: orm对象
        :param budget_id: 预算ID
        :return: 预算对象
        """
        return (await db.execute(select(AcctBudget).where(AcctBudget.budget_id == budget_id))).scalars().first()

    @classmethod
    async def get_budget_by_category(
        cls, db: AsyncSession, user_id: int, budget_month: str, category_id: int | None
    ) -> AcctBudget | None:
        """
        查询指定月份、指定分类的预算

        :param db: orm对象
        :param user_id: 用户ID
        :param budget_month: 预算月份
        :param category_id: 分类ID，为空表示总预算
        :return: 预算对象
        """
        query = select(AcctBudget).where(
            AcctBudget.user_id == user_id,
            AcctBudget.budget_month == budget_month,
            AcctBudget.category_id == category_id if category_id else AcctBudget.category_id.is_(None),
        )

        return (await db.execute(query)).scalars().first()

    @classmethod
    async def add_budget_dao(cls, db: AsyncSession, payload: dict) -> AcctBudget:
        """
        新增预算

        :param db: orm对象
        :param payload: 预算字典
        :return: 新增后的预算对象
        """
        db_budget = AcctBudget(**payload)
        db.add(db_budget)
        await db.flush()

        return db_budget

    @classmethod
    async def edit_budget_dao(cls, db: AsyncSession, payload: dict) -> None:
        """
        修改预算

        :param db: orm对象
        :param payload: 待更新的预算字典
        :return:
        """
        await db.execute(update(AcctBudget).where(AcctBudget.budget_id == payload.get('budget_id')).values(**payload))

    @classmethod
    async def delete_budget_dao(cls, db: AsyncSession, budget_id: int) -> None:
        """
        删除预算

        :param db: orm对象
        :param budget_id: 预算ID
        :return:
        """
        await db.execute(delete(AcctBudget).where(AcctBudget.budget_id == budget_id))


class AccountRecurringDao:
    """
    记账周期规则数据库操作层
    """

    @classmethod
    async def get_recurring_list(cls, db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
        """
        查询用户的周期规则列表，附带分类与账户名称

        :param db: orm对象
        :param user_id: 用户ID
        :return: 规则列表
        """
        from_account = aliased(AcctAccount)
        query = (
            select(
                AcctRecurring.recurring_id,
                AcctRecurring.title,
                AcctRecurring.bill_type,
                AcctRecurring.amount,
                AcctRecurring.category_id,
                AcctRecurring.account_id,
                AcctRecurring.to_account_id,
                AcctRecurring.tag,
                AcctRecurring.remark,
                AcctRecurring.rule_type,
                AcctRecurring.interval_num,
                AcctRecurring.day_of_month,
                AcctRecurring.day_of_week,
                AcctRecurring.start_date,
                AcctRecurring.end_date,
                AcctRecurring.next_run_date,
                AcctRecurring.last_run_date,
                AcctRecurring.run_count,
                AcctRecurring.status,
                AcctCategory.category_name,
                AcctCategory.icon.label('category_icon'),
                AcctCategory.color.label('category_color'),
                from_account.account_name,
            )
            .outerjoin(AcctCategory, AcctCategory.category_id == AcctRecurring.category_id)
            .outerjoin(from_account, from_account.account_id == AcctRecurring.account_id)
            .where(AcctRecurring.user_id == user_id, AcctRecurring.del_flag == '0')
            .order_by(AcctRecurring.status.asc(), AcctRecurring.next_run_date.asc())
        )

        return [dict(row) for row in (await db.execute(query)).mappings().all()]

    @classmethod
    async def get_recurring_by_id(cls, db: AsyncSession, recurring_id: int) -> AcctRecurring | None:
        """
        根据ID查询周期规则

        :param db: orm对象
        :param recurring_id: 规则ID
        :return: 规则对象
        """
        return (
            await db.execute(
                select(AcctRecurring).where(
                    AcctRecurring.recurring_id == recurring_id, AcctRecurring.del_flag == '0'
                )
            )
        ).scalars().first()

    @classmethod
    async def get_due_recurring(cls, db: AsyncSession, user_id: int, today: date) -> list[AcctRecurring]:
        """
        查询到期未生成的启用规则

        :param db: orm对象
        :param user_id: 用户ID
        :param today: 当天日期
        :return: 规则列表
        """
        query = (
            select(AcctRecurring)
            .where(
                AcctRecurring.user_id == user_id,
                AcctRecurring.del_flag == '0',
                AcctRecurring.status == '0',
                AcctRecurring.next_run_date <= today,
            )
            .order_by(AcctRecurring.next_run_date.asc())
        )

        return list((await db.execute(query)).scalars().all())

    @classmethod
    async def add_recurring_dao(cls, db: AsyncSession, recurring: RecurringModel) -> AcctRecurring:
        """
        新增周期规则

        :param db: orm对象
        :param recurring: 规则对象
        :return: 新增后的规则
        """
        payload = recurring.model_dump(
            exclude={
                'create_time',
                'update_time',
                'category_name',
                'category_icon',
                'category_color',
                'account_name',
                'recurring_id',
            },
            exclude_none=True,
        )
        db_recurring = AcctRecurring(**payload)
        db.add(db_recurring)
        await db.flush()

        return db_recurring

    @classmethod
    async def edit_recurring_dao(cls, db: AsyncSession, payload: dict) -> None:
        """
        修改周期规则

        :param db: orm对象
        :param payload: 待更新的规则字典
        :return:
        """
        await db.execute(
            update(AcctRecurring)
            .where(AcctRecurring.recurring_id == payload.get('recurring_id'))
            .values(**payload)
        )

    @classmethod
    async def delete_recurring_dao(cls, db: AsyncSession, recurring_ids: list[int]) -> None:
        """
        逻辑删除周期规则

        :param db: orm对象
        :param recurring_ids: 规则ID列表
        :return:
        """
        if recurring_ids:
            await db.execute(
                update(AcctRecurring).where(AcctRecurring.recurring_id.in_(recurring_ids)).values(del_flag='2')
            )

    @classmethod
    async def count_bill_by_recurring(cls, db: AsyncSession, recurring_id: int, bill_date: date) -> int:
        """
        统计某规则在某天是否已生成账单，用于幂等校验

        :param db: orm对象
        :param recurring_id: 规则ID
        :param bill_date: 账单日期
        :return: 数量
        """
        return (
            await db.execute(
                select(func.count())
                .select_from(AcctBill)
                .where(
                    AcctBill.recurring_id == recurring_id,
                    AcctBill.bill_date == bill_date,
                    AcctBill.del_flag == '0',
                )
            )
        ).scalar_one()


class AccountLedgerDao:
    """
    记账账本数据库操作层
    """

    @classmethod
    async def get_user_ledgers(cls, db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
        """
        查询用户加入的账本（含角色、成员数、账单数）

        :param db: orm对象
        :param user_id: 用户ID
        :return: 账本列表
        """
        member_count = (
            select(AcctLedgerMember.ledger_id, func.count().label('cnt'))
            .where(AcctLedgerMember.del_flag == '0', AcctLedgerMember.status == '0')
            .group_by(AcctLedgerMember.ledger_id)
            .subquery()
        )
        bill_count = (
            select(AcctBill.ledger_id, func.count().label('cnt'))
            .where(AcctBill.del_flag == '0')
            .group_by(AcctBill.ledger_id)
            .subquery()
        )
        query = (
            select(
                AcctLedger.ledger_id,
                AcctLedger.owner_id,
                AcctLedger.ledger_name,
                AcctLedger.invite_code,
                AcctLedger.is_default,
                AcctLedger.status,
                AcctLedger.create_time,
                AcctLedgerMember.role,
                func.coalesce(member_count.c.cnt, 1).label('member_count'),
                func.coalesce(bill_count.c.cnt, 0).label('bill_count'),
            )
            .join(
                AcctLedgerMember,
                and_(
                    AcctLedgerMember.ledger_id == AcctLedger.ledger_id,
                    AcctLedgerMember.user_id == user_id,
                    AcctLedgerMember.del_flag == '0',
                    AcctLedgerMember.status == '0',
                ),
            )
            .outerjoin(member_count, member_count.c.ledger_id == AcctLedger.ledger_id)
            .outerjoin(bill_count, bill_count.c.ledger_id == AcctLedger.ledger_id)
            .where(AcctLedger.del_flag == '0')
            .order_by(AcctLedger.is_default.desc(), AcctLedger.ledger_id.asc())
        )

        return [dict(row) for row in (await db.execute(query)).mappings().all()]

    @classmethod
    async def get_ledger_by_id(cls, db: AsyncSession, ledger_id: int) -> AcctLedger | None:
        """
        根据ID查询账本

        :param db: orm对象
        :param ledger_id: 账本ID
        :return: 账本对象
        """
        return (
            await db.execute(select(AcctLedger).where(AcctLedger.ledger_id == ledger_id, AcctLedger.del_flag == '0'))
        ).scalars().first()

    @classmethod
    async def get_default_ledger(cls, db: AsyncSession, user_id: int) -> AcctLedger | None:
        """
        查询用户的默认账本

        :param db: orm对象
        :param user_id: 用户ID
        :return: 账本对象
        """
        query = (
            select(AcctLedger)
            .join(AcctLedgerMember, AcctLedgerMember.ledger_id == AcctLedger.ledger_id)
            .where(
                AcctLedger.owner_id == user_id,
                AcctLedger.is_default == '1',
                AcctLedger.del_flag == '0',
                AcctLedgerMember.user_id == user_id,
                AcctLedgerMember.del_flag == '0',
            )
        )

        return (await db.execute(query)).scalars().first()

    @classmethod
    async def get_ledger_by_code(cls, db: AsyncSession, invite_code: str) -> AcctLedger | None:
        """
        根据邀请码查询账本

        :param db: orm对象
        :param invite_code: 邀请码
        :return: 账本对象
        """
        return (
            await db.execute(
                select(AcctLedger).where(
                    AcctLedger.invite_code == invite_code.upper(), AcctLedger.del_flag == '0'
                )
            )
        ).scalars().first()

    @classmethod
    async def add_ledger_dao(cls, db: AsyncSession, ledger: LedgerModel) -> AcctLedger:
        """
        新增账本

        :param db: orm对象
        :param ledger: 账本对象
        :return: 新增后的账本
        """
        payload = ledger.model_dump(
            exclude={'create_time', 'member_count', 'bill_count', 'owner_name', 'role', 'ledger_id'},
            exclude_none=True,
        )
        db_ledger = AcctLedger(**payload)
        db.add(db_ledger)
        await db.flush()

        return db_ledger

    @classmethod
    async def add_member_dao(cls, db: AsyncSession, ledger_id: int, user_id: int, role: str = '1') -> AcctLedgerMember:
        """
        添加账本成员

        :param db: orm对象
        :param ledger_id: 账本ID
        :param user_id: 用户ID
        :param role: 角色
        :return: 成员对象
        """
        member = AcctLedgerMember(ledger_id=ledger_id, user_id=user_id, role=role, status='0')
        db.add(member)
        await db.flush()

        return member

    @classmethod
    async def get_member(cls, db: AsyncSession, ledger_id: int, user_id: int) -> AcctLedgerMember | None:
        """
        查询账本成员关系

        :param db: orm对象
        :param ledger_id: 账本ID
        :param user_id: 用户ID
        :return: 成员对象
        """
        return (
            await db.execute(
                select(AcctLedgerMember).where(
                    AcctLedgerMember.ledger_id == ledger_id,
                    AcctLedgerMember.user_id == user_id,
                    AcctLedgerMember.del_flag == '0',
                    AcctLedgerMember.status == '0',
                )
            )
        ).scalars().first()

    @classmethod
    async def get_members(cls, db: AsyncSession, ledger_id: int) -> list[dict[str, Any]]:
        """
        查询账本成员列表

        :param db: orm对象
        :param ledger_id: 账本ID
        :return: 成员列表
        """
        from module_admin.entity.do.user_do import SysUser

        query = (
            select(
                AcctLedgerMember.user_id,
                AcctLedgerMember.role,
                AcctLedgerMember.create_time,
                SysUser.user_name,
                SysUser.nick_name,
            )
            .outerjoin(SysUser, SysUser.user_id == AcctLedgerMember.user_id)
            .where(
                AcctLedgerMember.ledger_id == ledger_id,
                AcctLedgerMember.del_flag == '0',
                AcctLedgerMember.status == '0',
            )
            .order_by(AcctLedgerMember.role.asc())
        )

        return [dict(row) for row in (await db.execute(query)).mappings().all()]

    @classmethod
    async def bind_bills_to_ledger(cls, db: AsyncSession, user_id: int, ledger_id: int) -> None:
        """
        把用户尚未归属账本的历史账单挂到默认账本

        :param db: orm对象
        :param user_id: 用户ID
        :param ledger_id: 账本ID
        :return:
        """
        await db.execute(
            update(AcctBill)
            .where(AcctBill.user_id == user_id, AcctBill.ledger_id.is_(None))
            .values(ledger_id=ledger_id)
        )

    @classmethod
    async def update_ledger_dao(cls, db: AsyncSession, payload: dict) -> None:
        """
        修改账本

        :param db: orm对象
        :param payload: 待更新字典
        :return:
        """
        await db.execute(
            update(AcctLedger).where(AcctLedger.ledger_id == payload.get('ledger_id')).values(**payload)
        )

    @classmethod
    async def remove_member_dao(cls, db: AsyncSession, ledger_id: int, user_id: int) -> None:
        """
        移除账本成员（退出）

        :param db: orm对象
        :param ledger_id: 账本ID
        :param user_id: 用户ID
        :return:
        """
        await db.execute(
            update(AcctLedgerMember)
            .where(AcctLedgerMember.ledger_id == ledger_id, AcctLedgerMember.user_id == user_id)
            .values(status='1')
        )
