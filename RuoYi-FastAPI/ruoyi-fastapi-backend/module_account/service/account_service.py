import calendar
import random
import string
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from exceptions.exception import ServiceException
from module_account.dao.account_dao import (
    AccountAccountDao,
    AccountBillDao,
    AccountBudgetDao,
    AccountCategoryDao,
    AccountLedgerDao,
    AccountRecurringDao,
)
from module_account.entity.vo.account_vo import (
    AccountModel,
    BillModel,
    BillPageQueryModel,
    BudgetModel,
    CategoryModel,
    CategoryStatModel,
    LedgerModel,
    MonthStatModel,
    RankItemModel,
    RecurringModel,
    SummaryModel,
)
from utils.common_util import CamelCaseUtil


class AccountCategoryService:
    """
    记账分类服务层
    """


    # 兼容历史英文图标名与外部写入，统一归一化为 emoji
    ICON_MAP: dict[str, str] = {
        'food': '🍚', 'car': '🚌', 'cart': '🛍️', 'home': '🏠', 'game': '🎮',
        'medical': '💊', 'book': '📚', 'gift': '🎁', 'more': '📦', 'salary': '💰',
        'award': '🏆', 'invest': '📈', 'work': '💼', 'redpacket': '🧧',
        'bike': '🚲', 'donate': '🤝', 'paw': '🐾', 'phone': '📱', 'coffee': '☕',
        'travel': '✈️', 'pet': '🐾', 'sport': '🏃', 'clothes': '👕', 'baby': '👶',
        'wallet': '💳', 'other': '📦',
    }

    @classmethod
    def normalize_icon(cls, icon):
        # 将英文图标名归一化为 emoji
        if not icon:
            return icon
        return cls.ICON_MAP.get(str(icon).strip().lower(), icon)

    DEFAULT_CATEGORIES: tuple[tuple[str, str, str, str], ...] = (
        ('餐饮', '0', '🍚', '#FF7043'),
        ('交通', '0', '🚌', '#42A5F5'),
        ('购物', '0', '🛍️', '#AB47BC'),
        ('居住', '0', '🏠', '#8D6E63'),
        ('娱乐', '0', '🎮', '#FFA726'),
        ('医疗', '0', '💊', '#EF5350'),
        ('学习', '0', '📚', '#26A69A'),
        ('人情', '0', '🎁', '#EC407A'),
        ('通讯', '0', '📱', '#5C6BC0'),
        ('其他支出', '0', '📦', '#90A4AE'),
        ('工资', '1', '💰', '#66BB6A'),
        ('奖金', '1', '🏆', '#FFCA28'),
        ('理财', '1', '📈', '#26C6DA'),
        ('兼职', '1', '💼', '#5C6BC0'),
        ('红包', '1', '🧧', '#EF5350'),
        ('其他收入', '1', '📥', '#78909C'),
    )

    @classmethod
    async def init_default_categories(cls, query_db: AsyncSession, user_id: int) -> None:
        """
        初始化用户默认分类

        :param query_db: orm对象
        :param user_id: 用户ID
        :return:
        """
        for index, (name, category_type, icon, color) in enumerate(cls.DEFAULT_CATEGORIES):
            await AccountCategoryDao.add_category_dao(
                query_db,
                CategoryModel(
                    user_id=user_id,
                    category_name=name,
                    category_type=category_type,
                    icon=icon,
                    color=color,
                    sort_num=index,
                    status='0',
                    create_by='system',
                    update_by='system',
                ),
            )
        await query_db.commit()

    @classmethod
    async def get_category_list_services(
        cls, query_db: AsyncSession, user_id: int, category_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        获取分类列表，首次访问时自动初始化默认分类

        :param query_db: orm对象
        :param user_id: 用户ID
        :param category_type: 分类类型
        :return: 分类列表
        """
        category_list = await AccountCategoryDao.get_category_list(query_db, user_id)
        if not category_list:
            await cls.init_default_categories(query_db, user_id)
        category_list = await AccountCategoryDao.get_category_list(query_db, user_id, category_type)
        result = CamelCaseUtil.transform_result(category_list)
        # 历史数据或外部写入可能是英文图标名，出口统一归一化
        for item in result:
            if isinstance(item, dict) and item.get('icon'):
                item['icon'] = cls.normalize_icon(item['icon'])

        return result

    @classmethod
    async def add_category_services(
        cls, query_db: AsyncSession, user_id: int, page_object: CategoryModel
    ) -> CrudResponseModel:
        """
        新增分类

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 分类对象
        :return: 操作结果
        """
        if page_object.category_type not in {'0', '1'}:
            raise ServiceException(message='分类类型不合法')
        exists_count = await AccountCategoryDao.count_category_name(
            query_db, user_id, page_object.category_type, page_object.category_name
        )
        if exists_count:
            raise ServiceException(message=f'分类{page_object.category_name}已存在')
        page_object.user_id = user_id
        page_object.icon = cls.normalize_icon(page_object.icon)
        try:
            await AccountCategoryDao.add_category_dao(query_db, page_object)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='新增成功')

    @classmethod
    async def edit_category_services(
        cls, query_db: AsyncSession, user_id: int, page_object: CategoryModel
    ) -> CrudResponseModel:
        """
        修改分类

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 分类对象
        :return: 操作结果
        """
        category_info = await AccountCategoryDao.get_category_by_id(query_db, page_object.category_id)
        if not category_info or category_info.user_id != user_id:
            raise ServiceException(message='分类不存在或无权操作')
        edit_data = page_object.model_dump(exclude_unset=True, exclude={'create_time', 'update_time', 'user_id'})
        if edit_data.get('icon'):
            edit_data['icon'] = cls.normalize_icon(edit_data['icon'])
        try:
            await AccountCategoryDao.edit_category_dao(query_db, edit_data)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='修改成功')

    @classmethod
    async def delete_category_services(cls, query_db: AsyncSession, user_id: int, category_ids: list[int]) -> CrudResponseModel:
        """
        删除分类

        :param query_db: orm对象
        :param user_id: 用户ID
        :param category_ids: 分类ID列表
        :return: 操作结果
        """
        for category_id in category_ids:
            category_info = await AccountCategoryDao.get_category_by_id(query_db, category_id)
            if not category_info or category_info.user_id != user_id:
                raise ServiceException(message='分类不存在或无权操作')
        bill_count = await AccountCategoryDao.count_bill_by_category(query_db, category_ids)
        try:
            await AccountCategoryDao.delete_category_dao(query_db, category_ids)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        message = f'删除成功，{bill_count} 笔相关账单已转为未分类' if bill_count else '删除成功'

        return CrudResponseModel(is_success=True, message=message)


class AccountAccountService:
    """
    记账资产账户服务层
    """

    DEFAULT_ACCOUNTS: tuple[tuple[str, str, str, str], ...] = (
        ('现金', '0', '💵', '#66BB6A'),
        ('微信', '7', '💚', '#43A047'),
        ('支付宝', '8', '💙', '#1E88E5'),
        ('银行卡', '1', '💳', '#5C6BC0'),
    )

    @classmethod
    async def init_default_accounts(cls, query_db: AsyncSession, user_id: int) -> None:
        """
        初始化用户默认账户

        :param query_db: orm对象
        :param user_id: 用户ID
        :return:
        """
        for index, (name, account_type, icon, color) in enumerate(cls.DEFAULT_ACCOUNTS):
            await AccountAccountDao.add_account_dao(
                query_db,
                AccountModel(
                    user_id=user_id,
                    account_name=name,
                    account_type=account_type,
                    icon=icon,
                    color=color,
                    init_balance=0,
                    is_include='0',
                    sort_num=index,
                    status='0',
                    create_by='system',
                    update_by='system',
                ),
            )
        await query_db.commit()

    @classmethod
    async def get_account_balance_services(cls, query_db: AsyncSession, user_id: int) -> dict[str, Any]:
        """
        获取账户列表与实时余额

        余额 = 期初余额 + 累计收入 - 累计支出 ± 转账

        :param query_db: orm对象
        :param user_id: 用户ID
        :return: 账户列表与总资产
        """
        account_list = await AccountAccountDao.get_account_list(query_db, user_id)
        if not account_list:
            await cls.init_default_accounts(query_db, user_id)
            account_list = await AccountAccountDao.get_account_list(query_db, user_id)

        delta_map = await AccountAccountDao.sum_delta_by_account(query_db, user_id)
        result = []
        total_asset = 0.0
        total_debt = 0.0
        for account in account_list:
            delta = delta_map.get(account.account_id, {'delta': 0.0, 'expense': 0.0, 'income': 0.0})
            balance = round(float(account.init_balance or 0) + delta['delta'], 2)
            # 借入（5）属于负债，单独统计；借出（6）属于应收资产
            if account.account_type == '5':
                total_debt += balance
            elif account.is_include == '0':
                total_asset += balance
            result.append(
                {
                    'accountId': account.account_id,
                    'accountName': account.account_name,
                    'accountType': account.account_type,
                    'icon': account.icon,
                    'color': account.color,
                    'initBalance': float(account.init_balance or 0),
                    'isInclude': account.is_include,
                    'sortNum': account.sort_num,
                    'status': account.status,
                    'remark': account.remark,
                    'balance': balance,
                    'expense': round(delta['expense'], 2),
                    'income': round(delta['income'], 2),
                }
            )

        return {
            'accounts': result,
            'totalAsset': round(total_asset, 2),
            'totalDebt': round(total_debt, 2),
            'netAsset': round(total_asset - total_debt, 2),
        }

    @classmethod
    async def add_account_services(
        cls, query_db: AsyncSession, user_id: int, page_object: AccountModel
    ) -> CrudResponseModel:
        """
        新增账户

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 账户对象
        :return: 操作结果
        """
        if page_object.account_type not in {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}:
            raise ServiceException(message='账户类型不合法')
        exists_count = await AccountAccountDao.count_account_name(query_db, user_id, page_object.account_name)
        if exists_count:
            raise ServiceException(message=f'账户{page_object.account_name}已存在')
        page_object.user_id = user_id
        try:
            await AccountAccountDao.add_account_dao(query_db, page_object)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='新增成功')

    @classmethod
    async def edit_account_services(
        cls, query_db: AsyncSession, user_id: int, page_object: AccountModel
    ) -> CrudResponseModel:
        """
        修改账户

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 账户对象
        :return: 操作结果
        """
        account_info = await AccountAccountDao.get_account_by_id(query_db, page_object.account_id)
        if not account_info or account_info.user_id != user_id:
            raise ServiceException(message='账户不存在或无权操作')
        edit_data = page_object.model_dump(
            exclude_unset=True,
            exclude={'create_time', 'update_time', 'user_id', 'balance', 'expense', 'income'},
        )
        try:
            await AccountAccountDao.edit_account_dao(query_db, edit_data)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='修改成功')

    @classmethod
    async def delete_account_services(cls, query_db: AsyncSession, user_id: int, account_ids: list[int]) -> CrudResponseModel:
        """
        删除账户

        :param query_db: orm对象
        :param user_id: 用户ID
        :param account_ids: 账户ID列表
        :return: 操作结果
        """
        for account_id in account_ids:
            account_info = await AccountAccountDao.get_account_by_id(query_db, account_id)
            if not account_info or account_info.user_id != user_id:
                raise ServiceException(message='账户不存在或无权操作')
        bill_count = await AccountAccountDao.count_bill_by_account(query_db, account_ids)
        if bill_count:
            raise ServiceException(message=f'该账户下还有 {bill_count} 笔账单，请先调整或删除后再试')
        try:
            await AccountAccountDao.delete_account_dao(query_db, account_ids)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='删除成功')


class AccountBillService:
    """
    记账账单服务层
    """

    @classmethod
    async def get_bill_list_services(
        cls,
        query_db: AsyncSession,
        user_id: int,
        query_object: BillPageQueryModel,
        is_page: bool = True,
        ledger_id: int | None = None,
    ) -> PageModel | list[dict[str, Any]]:
        """
        获取账单列表

        :param query_db: orm对象
        :param user_id: 用户ID
        :param query_object: 查询参数
        :param is_page: 是否分页
        :return: 账单列表
        """
        await AccountRecurringService.ensure_due_bills(query_db, user_id)
        bill_list_result = await AccountBillDao.get_bill_list(query_db, user_id, query_object, is_page, ledger_id)
        if is_page:
            bill_list_result.rows = CamelCaseUtil.transform_result(bill_list_result.rows)
            for row in bill_list_result.rows:
                if isinstance(row, dict) and row.get('categoryIcon'):
                    row['categoryIcon'] = AccountCategoryService.normalize_icon(row['categoryIcon'])

        return bill_list_result

    @classmethod
    async def _check_category_services(cls, query_db: AsyncSession, user_id: int, category_id: int | None) -> None:
        """
        校验分类归属

        :param query_db: orm对象
        :param user_id: 用户ID
        :param category_id: 分类ID
        :return:
        """
        if not category_id:
            return
        category_info = await AccountCategoryDao.get_category_by_id(query_db, category_id)
        if not category_info or category_info.user_id != user_id:
            raise ServiceException(message='分类不存在或无权操作')

    @classmethod
    async def _check_account_services(
        cls, query_db: AsyncSession, user_id: int, account_id: int | None, field_name: str = '账户'
    ) -> None:
        """
        校验账户归属

        :param query_db: orm对象
        :param user_id: 用户ID
        :param account_id: 账户ID
        :param field_name: 字段名称，用于错误提示
        :return:
        """
        if not account_id:
            return
        account_info = await AccountAccountDao.get_account_by_id(query_db, account_id)
        if not account_info or account_info.user_id != user_id:
            raise ServiceException(message=f'{field_name}不存在或无权操作')

    @classmethod
    def _validate_bill(cls, page_object: BillModel) -> None:
        """
        校验账单基础字段

        :param page_object: 账单对象
        :return:
        """
        if page_object.bill_type not in {'0', '1', '2'}:
            raise ServiceException(message='账单类型不合法')
        if page_object.amount is None or float(page_object.amount) <= 0:
            raise ServiceException(message='金额必须大于0')
        if page_object.bill_type == '2':
            if not page_object.account_id or not page_object.to_account_id:
                raise ServiceException(message='请选择转出与转入账户')
            if page_object.account_id == page_object.to_account_id:
                raise ServiceException(message='转出与转入账户不能相同')

    @classmethod
    async def add_bill_services(
        cls, query_db: AsyncSession, user_id: int, page_object: BillModel, ledger_id: int | None = None
    ) -> CrudResponseModel:
        """
        新增账单

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 账单对象
        :return: 操作结果
        """
        cls._validate_bill(page_object)
        await cls._check_category_services(query_db, user_id, page_object.category_id)
        await cls._check_account_services(query_db, user_id, page_object.account_id)
        await cls._check_account_services(query_db, user_id, page_object.to_account_id, '转入账户')
        page_object.user_id = user_id
        if ledger_id and not page_object.ledger_id:
            page_object.ledger_id = ledger_id
        if not page_object.bill_date:
            page_object.bill_date = date.today()
        try:
            await AccountBillDao.add_bill_dao(query_db, page_object)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='转账成功' if page_object.bill_type == '2' else '记账成功')

    @classmethod
    async def get_bill_detail_services(cls, query_db: AsyncSession, user_id: int, bill_id: int) -> dict[str, Any]:
        """
        获取单条账单详情，供前端编辑回显

        :param query_db: orm对象
        :param user_id: 用户ID
        :param bill_id: 账单ID
        :return: 账单详情
        """
        bill_info = await AccountBillDao.get_bill_by_id(query_db, bill_id)
        if not bill_info or bill_info.user_id != user_id:
            raise ServiceException(message='账单不存在或无权操作')
        detail = {
            'billId': bill_info.bill_id,
            'billType': bill_info.bill_type,
            'amount': float(bill_info.amount or 0),
            'billDate': bill_info.bill_date.isoformat() if bill_info.bill_date else None,
            'categoryId': bill_info.category_id,
            'accountId': bill_info.account_id,
            'toAccountId': bill_info.to_account_id,
            'tag': bill_info.tag,
            'images': bill_info.images,
            'remark': bill_info.remark,
            'payMethod': bill_info.pay_method,
        }
        if bill_info.category_id:
            category_info = await AccountCategoryDao.get_category_by_id(query_db, bill_info.category_id)
            if category_info:
                detail['categoryName'] = category_info.category_name
                detail['categoryIcon'] = category_info.icon
                detail['categoryColor'] = category_info.color
        for key, field in (('accountName', bill_info.account_id), ('toAccountName', bill_info.to_account_id)):
            if field:
                account_info = await AccountAccountDao.get_account_by_id(query_db, field)
                if account_info:
                    detail[key] = account_info.account_name

        return detail

    @classmethod
    async def edit_bill_services(cls, query_db: AsyncSession, user_id: int, page_object: BillModel) -> CrudResponseModel:
        """
        修改账单

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 账单对象
        :return: 操作结果
        """
        bill_info = await AccountBillDao.get_bill_by_id(query_db, page_object.bill_id)
        if not bill_info or bill_info.user_id != user_id:
            raise ServiceException(message='账单不存在或无权操作')
        if page_object.amount is not None and float(page_object.amount) <= 0:
            raise ServiceException(message='金额必须大于0')
        await cls._check_category_services(query_db, user_id, page_object.category_id)
        await cls._check_account_services(query_db, user_id, page_object.account_id)
        await cls._check_account_services(query_db, user_id, page_object.to_account_id, '转入账户')
        if (page_object.bill_type or bill_info.bill_type) == '2' and page_object.account_id and page_object.to_account_id:
            if page_object.account_id == page_object.to_account_id:
                raise ServiceException(message='转出与转入账户不能相同')
        edit_data = page_object.model_dump(
            exclude_unset=True,
            exclude={
                'create_time',
                'update_time',
                'user_id',
                'category_name',
                'category_icon',
                'category_color',
                'account_name',
                'to_account_name',
                'bill_id',
            },
        )
        try:
            await AccountBillDao.edit_bill_dao(query_db, {'bill_id': page_object.bill_id, **edit_data})
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='修改成功')

    @classmethod
    async def delete_bill_services(cls, query_db: AsyncSession, user_id: int, bill_ids: list[int]) -> CrudResponseModel:
        """
        删除账单

        :param query_db: orm对象
        :param user_id: 用户ID
        :param bill_ids: 账单ID列表
        :return: 操作结果
        """
        for bill_id in bill_ids:
            bill_info = await AccountBillDao.get_bill_by_id(query_db, bill_id)
            if not bill_info or bill_info.user_id != user_id:
                raise ServiceException(message='账单不存在或无权操作')
        try:
            await AccountBillDao.delete_bill_dao(query_db, bill_ids)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='删除成功')

    @classmethod
    async def summary_services(
        cls,
        query_db: AsyncSession,
        user_id: int,
        begin_date: str | None = None,
        end_date: str | None = None,
        ledger_id: int | None = None,
    ) -> SummaryModel:
        """
        收支汇总统计（转账不计入）

        :param query_db: orm对象
        :param user_id: 用户ID
        :param begin_date: 开始日期
        :param end_date: 结束日期
        :return: 汇总结果
        """
        await AccountRecurringService.ensure_due_bills(query_db, user_id)
        summary = await AccountBillDao.sum_by_type(query_db, user_id, begin_date, end_date, ledger_id)
        total_income = round(summary['1']['amount'], 2)
        total_expense = round(summary['0']['amount'], 2)

        return SummaryModel(
            total_income=total_income,
            total_expense=total_expense,
            balance=round(total_income - total_expense, 2),
            bill_count=summary['1']['bill_count'] + summary['0']['bill_count'],
        )

    @classmethod
    async def category_stat_services(
        cls,
        query_db: AsyncSession,
        user_id: int,
        bill_type: str = '0',
        begin_date: str | None = None,
        end_date: str | None = None,
        ledger_id: int | None = None,
    ) -> list[CategoryStatModel]:
        """
        分类占比统计

        :param query_db: orm对象
        :param user_id: 用户ID
        :param bill_type: 账单类型
        :param begin_date: 开始日期
        :param end_date: 结束日期
        :return: 分类统计列表
        """
        rows = await AccountBillDao.stat_by_category(query_db, user_id, bill_type, begin_date, end_date, ledger_id)
        total = sum(float(row['amount']) for row in rows)

        return [
            CategoryStatModel(
                category_id=row['category_id'],
                category_name=row['category_name'] or '未分类',
                category_color=row['category_color'],
                category_icon=row['category_icon'],
                bill_type=bill_type,
                amount=round(float(row['amount']), 2),
                bill_count=int(row['bill_count']),
                percent=round(float(row['amount']) / total * 100, 2) if total else 0.0,
            )
            for row in rows
        ]

    @classmethod
    async def rank_services(
        cls,
        query_db: AsyncSession,
        user_id: int,
        bill_type: str = '0',
        begin_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> dict[str, list[RankItemModel]]:
        """
        排行榜：按分类与按单笔

        :param query_db: orm对象
        :param user_id: 用户ID
        :param bill_type: 账单类型
        :param begin_date: 开始日期
        :param end_date: 结束日期
        :param limit: 返回条数
        :return: 分类排行与单笔排行
        """
        category_rows = await AccountBillDao.stat_by_category(query_db, user_id, bill_type, begin_date, end_date)
        category_total = sum(float(row['amount']) for row in category_rows)
        category_rank = [
            RankItemModel(
                key=str(row['category_id'] or ''),
                name=row['category_name'] or '未分类',
                amount=round(float(row['amount']), 2),
                bill_count=int(row['bill_count']),
                percent=round(float(row['amount']) / category_total * 100, 2) if category_total else 0.0,
                color=row['category_color'],
                icon=row['category_icon'],
            )
            for row in category_rows[:limit]
        ]

        bill_rows = await AccountBillDao.stat_top_bills(query_db, user_id, bill_type, begin_date, end_date, limit)
        bill_total = sum(float(row['amount']) for row in bill_rows)
        bill_rank = [
            RankItemModel(
                key=str(row['bill_id']),
                name=row['category_name'] or '未分类',
                amount=round(float(row['amount']), 2),
                bill_count=1,
                percent=round(float(row['amount']) / bill_total * 100, 2) if bill_total else 0.0,
                color=row['category_color'],
                icon=row['category_icon'],
            )
            for row in bill_rows
        ]

        return {'byCategory': category_rank, 'byBill': bill_rank}

    @classmethod
    async def trend_services(cls, query_db: AsyncSession, user_id: int, months: int = 6) -> list[MonthStatModel]:
        """
        月度收支趋势统计

        :param query_db: orm对象
        :param user_id: 用户ID
        :param months: 统计月份数
        :return: 月度统计列表
        """
        rows = await AccountBillDao.stat_by_month(query_db, user_id, months)
        row_map = {row['month']: row for row in rows}

        # 补齐最近 months 个自然月，缺失月份按 0 处理，保证趋势图连续
        today = date.today()
        year, month = today.year, today.month
        month_keys = []
        for _ in range(months):
            month_keys.append(f'{year:04d}-{month:02d}')
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        month_keys.reverse()

        return [
            MonthStatModel(
                month=key,
                income=round(float(row_map[key]['income']), 2) if key in row_map else 0.0,
                expense=round(float(row_map[key]['expense']), 2) if key in row_map else 0.0,
            )
            for key in month_keys
        ]


class AccountBudgetService:
    """
    记账预算服务层
    """

    @classmethod
    def _month_range(cls, budget_month: str) -> tuple[str, str]:
        """
        计算月份的首尾日期

        :param budget_month: 预算月份（YYYY-MM）
        :return: (首日, 末日)
        """
        try:
            year, month = (int(part) for part in budget_month.split('-'))
        except (ValueError, AttributeError):
            raise ServiceException(message='预算月份格式应为 YYYY-MM')
        last_day = calendar.monthrange(year, month)[1]

        return f'{budget_month}-01', f'{budget_month}-{last_day:02d}'

    @classmethod
    async def get_budget_services(cls, query_db: AsyncSession, user_id: int, budget_month: str) -> dict[str, Any]:
        """
        查询指定月份的预算与执行进度

        :param query_db: orm对象
        :param user_id: 用户ID
        :param budget_month: 预算月份
        :return: 总预算与分类预算
        """
        begin_date, end_date = cls._month_range(budget_month)
        budget_list = await AccountBudgetDao.get_budget_list(query_db, user_id, budget_month)
        category_usage = await AccountBillDao.sum_expense_by_category(query_db, user_id, begin_date, end_date)
        total_used = round(sum(category_usage.values()), 2)

        category_ids = [b.category_id for b in budget_list if b.category_id]
        category_map: dict[int, Any] = {}
        if category_ids:
            for category in await AccountCategoryDao.get_category_list(query_db, user_id):
                category_map[category.category_id] = category

        total_budget = next((b for b in budget_list if b.category_id is None), None)
        category_budgets = []
        for budget in budget_list:
            if budget.category_id is None:
                continue
            category = category_map.get(budget.category_id)
            category_budgets.append(
                {
                    'budgetId': budget.budget_id,
                    'budgetMonth': budget.budget_month,
                    'categoryId': budget.category_id,
                    'categoryName': category.category_name if category else '已删除分类',
                    'categoryColor': category.color if category else '#90A4AE',
                    'amount': float(budget.amount or 0),
                    'used': round(category_usage.get(budget.category_id, 0.0), 2),
                }
            )

        return {
            'budgetMonth': budget_month,
            'totalAmount': float(total_budget.amount) if total_budget else 0.0,
            'totalUsed': total_used,
            'categoryBudgets': category_budgets,
            'categoryUsage': {str(key): round(value, 2) for key, value in category_usage.items()},
        }

    @classmethod
    async def save_budget_services(cls, query_db: AsyncSession, user_id: int, page_object: BudgetModel) -> CrudResponseModel:
        """
        保存预算（存在则更新，不存在则新增）

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 预算对象
        :return: 操作结果
        """
        if not page_object.budget_month:
            raise ServiceException(message='预算月份不能为空')
        cls._month_range(page_object.budget_month)
        amount = float(page_object.amount or 0)
        if amount < 0:
            raise ServiceException(message='预算金额不能为负数')
        if page_object.category_id:
            await AccountBillService._check_category_services(query_db, user_id, page_object.category_id)

        exists = await AccountBudgetDao.get_budget_by_category(
            query_db, user_id, page_object.budget_month, page_object.category_id
        )
        try:
            if amount == 0 and exists:
                await AccountBudgetDao.delete_budget_dao(query_db, exists.budget_id)
            elif exists:
                await AccountBudgetDao.edit_budget_dao(
                    query_db, {'budget_id': exists.budget_id, 'amount': amount, 'update_by': page_object.update_by or ''}
                )
            elif amount > 0:
                await AccountBudgetDao.add_budget_dao(
                    query_db,
                    {
                        'user_id': user_id,
                        'budget_month': page_object.budget_month,
                        'category_id': page_object.category_id,
                        'amount': amount,
                        'create_by': page_object.create_by or '',
                        'update_by': page_object.update_by or '',
                    },
                )
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='保存成功')


class AccountRecurringService:
    """
    记账周期规则服务层

    采用懒执行：用户打开账单列表或汇总时补记到期账单，避免依赖外部调度器
    """

    RULE_LABELS = {'0': '每天', '1': '每周', '2': '每月', '3': '每年'}
    MAX_CATCH_UP = 60

    @classmethod
    def _advance(cls, rule: RecurringModel, current: date) -> date:
        """
        按规则推算下一次生成日期

        :param rule: 规则
        :param current: 当前日期
        :return: 下一次日期
        """
        interval = int(rule.interval_num or 1)
        rule_type = rule.rule_type or '2'
        if rule_type == '0':
            return current + timedelta(days=interval)
        if rule_type == '1':
            return current + timedelta(weeks=interval)
        if rule_type == '3':
            year = current.year + interval
            day = min(int(rule.day_of_month or current.day), calendar.monthrange(year, current.month)[1])
            return date(year, current.month, day)
        # 每月：按月推进，日期取 min(目标日, 当月最后一天)，避免 31 号在 2 月越界
        month_index = current.month - 1 + interval
        year = current.year + month_index // 12
        month = month_index % 12 + 1
        day = min(int(rule.day_of_month or current.day), calendar.monthrange(year, month)[1])
        return date(year, month, day)

    @classmethod
    async def ensure_due_bills(cls, query_db: AsyncSession, user_id: int) -> int:
        """
        补记所有到期的周期账单（幂等）

        :param query_db: orm对象
        :param user_id: 用户ID
        :return: 本次生成的账单数量
        """
        today = date.today()
        try:
            rules = await AccountRecurringDao.get_due_recurring(query_db, user_id, today)
        except Exception:
            return 0
        if not rules:
            return 0

        created = 0
        default_ledger = await AccountLedgerService.ensure_default_ledger(query_db, user_id)
        default_ledger_id = default_ledger.ledger_id if default_ledger else None
        for db_rule in rules:
            rule = RecurringModel.model_validate(db_rule)
            next_date = db_rule.next_run_date
            guard = 0
            while next_date and next_date <= today and guard < cls.MAX_CATCH_UP:
                guard += 1
                if db_rule.end_date and next_date > db_rule.end_date:
                    break
                exists = await AccountRecurringDao.count_bill_by_recurring(query_db, db_rule.recurring_id, next_date)
                if not exists:
                    await AccountBillDao.add_bill_dao(
                        query_db,
                        BillModel(
                            user_id=user_id,
                            category_id=db_rule.category_id,
                            bill_type=db_rule.bill_type,
                            amount=float(db_rule.amount or 0),
                            bill_date=next_date,
                            pay_method=db_rule.pay_method,
                            account_id=db_rule.account_id,
                            to_account_id=db_rule.to_account_id,
                            tag=db_rule.tag,
                            remark=db_rule.remark or db_rule.title,
                            recurring_id=db_rule.recurring_id,
                            ledger_id=default_ledger_id,
                            create_by='recurring',
                            update_by='recurring',
                        ),
                    )
                    created += 1
                last_date = next_date
                next_date = cls._advance(rule, next_date)
                await AccountRecurringDao.edit_recurring_dao(
                    query_db,
                    {
                        'recurring_id': db_rule.recurring_id,
                        'next_run_date': next_date,
                        'last_run_date': last_date,
                        'run_count': int(db_rule.run_count or 0) + 1,
                    },
                )
            if db_rule.end_date and next_date and next_date > db_rule.end_date:
                await AccountRecurringDao.edit_recurring_dao(
                    query_db, {'recurring_id': db_rule.recurring_id, 'status': '1'}
                )
        try:
            await query_db.commit()
        except Exception:
            await query_db.rollback()

        return created

    @classmethod
    async def get_list_services(cls, query_db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
        """
        获取周期规则列表

        :param query_db: orm对象
        :param user_id: 用户ID
        :return: 规则列表
        """
        await cls.ensure_due_bills(query_db, user_id)
        rows = await AccountRecurringDao.get_recurring_list(query_db, user_id)
        result = []
        for row in rows:
            item = CamelCaseUtil.transform_result(row)
            rule_type = str(row.get('rule_type') or '2')
            interval = int(row.get('interval_num') or 1)
            unit = {'0': '天', '1': '周', '2': '月', '3': '年'}.get(rule_type, '月')
            item['ruleLabel'] = f'每 {interval} {unit}' if interval > 1 else f'每{unit}'
            if item.get('categoryIcon'):
                item['categoryIcon'] = AccountCategoryService.normalize_icon(item['categoryIcon'])
            item['nextRunDate'] = row['next_run_date'].isoformat() if row.get('next_run_date') else None
            item['lastRunDate'] = row['last_run_date'].isoformat() if row.get('last_run_date') else None
            item['startDate'] = row['start_date'].isoformat() if row.get('start_date') else None
            item['endDate'] = row['end_date'].isoformat() if row.get('end_date') else None
            result.append(item)

        return result

    @classmethod
    async def add_services(cls, query_db: AsyncSession, user_id: int, page_object: RecurringModel) -> CrudResponseModel:
        """
        新增周期规则

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 规则对象
        :return: 操作结果
        """
        if page_object.bill_type not in {'0', '1', '2'}:
            raise ServiceException(message='账单类型不合法')
        if page_object.amount is None or float(page_object.amount) <= 0:
            raise ServiceException(message='金额必须大于0')
        if page_object.rule_type not in {'0', '1', '2', '3'}:
            raise ServiceException(message='周期类型不合法')
        await AccountBillService._check_category_services(query_db, user_id, page_object.category_id)
        await AccountBillService._check_account_services(query_db, user_id, page_object.account_id)
        if page_object.bill_type == '2':
            await AccountBillService._check_account_services(query_db, user_id, page_object.to_account_id, '转入账户')
            if page_object.account_id == page_object.to_account_id:
                raise ServiceException(message='转出与转入账户不能相同')
        page_object.user_id = user_id
        if not page_object.start_date:
            page_object.start_date = date.today()
        if not page_object.next_run_date:
            page_object.next_run_date = page_object.start_date
        page_object.status = page_object.status or '0'
        page_object.run_count = 0
        try:
            await AccountRecurringDao.add_recurring_dao(query_db, page_object)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='周期记账已创建')

    @classmethod
    async def edit_services(cls, query_db: AsyncSession, user_id: int, page_object: RecurringModel) -> CrudResponseModel:
        """
        修改周期规则

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 规则对象
        :return: 操作结果
        """
        rule_info = await AccountRecurringDao.get_recurring_by_id(query_db, page_object.recurring_id)
        if not rule_info or rule_info.user_id != user_id:
            raise ServiceException(message='周期规则不存在或无权操作')
        if page_object.amount is not None and float(page_object.amount) <= 0:
            raise ServiceException(message='金额必须大于0')
        await AccountBillService._check_category_services(query_db, user_id, page_object.category_id)
        await AccountBillService._check_account_services(query_db, user_id, page_object.account_id)
        edit_data = page_object.model_dump(
            exclude_unset=True,
            exclude={
                'create_time',
                'update_time',
                'user_id',
                'category_name',
                'category_icon',
                'category_color',
                'account_name',
                'recurring_id',
                'run_count',
                'last_run_date',
            },
        )
        if page_object.rule_type or page_object.start_date:
            edit_data['next_run_date'] = page_object.start_date or rule_info.next_run_date
        try:
            await AccountRecurringDao.edit_recurring_dao(
                query_db, {'recurring_id': page_object.recurring_id, **edit_data}
            )
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='修改成功')

    @classmethod
    async def delete_services(cls, query_db: AsyncSession, user_id: int, recurring_ids: list[int]) -> CrudResponseModel:
        """
        删除周期规则（已生成的账单保留）

        :param query_db: orm对象
        :param user_id: 用户ID
        :param recurring_ids: 规则ID列表
        :return: 操作结果
        """
        for recurring_id in recurring_ids:
            rule_info = await AccountRecurringDao.get_recurring_by_id(query_db, recurring_id)
            if not rule_info or rule_info.user_id != user_id:
                raise ServiceException(message='周期规则不存在或无权操作')
        try:
            await AccountRecurringDao.delete_recurring_dao(query_db, recurring_ids)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='已删除，历史账单保留')

    @classmethod
    async def toggle_services(cls, query_db: AsyncSession, user_id: int, recurring_id: int) -> CrudResponseModel:
        """
        启用 / 暂停周期规则

        :param query_db: orm对象
        :param user_id: 用户ID
        :param recurring_id: 规则ID
        :return: 操作结果
        """
        rule_info = await AccountRecurringDao.get_recurring_by_id(query_db, recurring_id)
        if not rule_info or rule_info.user_id != user_id:
            raise ServiceException(message='周期规则不存在或无权操作')
        new_status = '1' if rule_info.status == '0' else '0'
        try:
            await AccountRecurringDao.edit_recurring_dao(
                query_db, {'recurring_id': recurring_id, 'status': new_status}
            )
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='已暂停' if new_status == '1' else '已启用')


class AccountLedgerService:
    """
    记账账本服务层
    """

    CODE_CHARS = string.ascii_uppercase + string.digits

    @classmethod
    def _generate_code(cls) -> str:
        """
        生成 6 位邀请码

        :return: 邀请码
        """
        return ''.join(random.choices(cls.CODE_CHARS, k=6))

    @classmethod
    async def ensure_default_ledger(cls, query_db: AsyncSession, user_id: int) -> Any:
        """
        确保用户存在默认账本，并把历史账单归入

        :param query_db: orm对象
        :param user_id: 用户ID
        :return: 默认账本对象
        """
        ledger = await AccountLedgerDao.get_default_ledger(query_db, user_id)
        if ledger:
            return ledger
        try:
            code = cls._generate_code()
            while await AccountLedgerDao.get_ledger_by_code(query_db, code):
                code = cls._generate_code()
            ledger = await AccountLedgerDao.add_ledger_dao(
                query_db,
                LedgerModel(
                    owner_id=user_id,
                    ledger_name='我的账本',
                    invite_code=code,
                    is_default='1',
                    status='0',
                    create_by='system',
                    update_by='system',
                ),
            )
            await AccountLedgerDao.add_member_dao(query_db, ledger.ledger_id, user_id, '0')
            await AccountLedgerDao.bind_bills_to_ledger(query_db, user_id, ledger.ledger_id)
            await query_db.commit()
        except Exception:
            await query_db.rollback()
            ledger = await AccountLedgerDao.get_default_ledger(query_db, user_id)

        return ledger

    @classmethod
    async def resolve_ledger_id(cls, query_db: AsyncSession, user_id: int, requested_id: int | None) -> int:
        """
        解析当前账本：请求指定且是成员则用指定的，否则用默认账本

        :param query_db: orm对象
        :param user_id: 用户ID
        :param requested_id: 请求头中的账本ID
        :return: 账本ID
        """
        default_ledger = await cls.ensure_default_ledger(query_db, user_id)
        fallback = default_ledger.ledger_id if default_ledger else 0
        if not requested_id:
            return fallback
        member = await AccountLedgerDao.get_member(query_db, requested_id, user_id)
        if member:
            return requested_id

        return fallback

    @classmethod
    async def get_list_services(cls, query_db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
        """
        获取当前用户可用的账本列表

        :param query_db: orm对象
        :param user_id: 用户ID
        :return: 账本列表
        """
        await cls.ensure_default_ledger(query_db, user_id)
        rows = await AccountLedgerDao.get_user_ledgers(query_db, user_id)
        result = []
        for row in rows:
            item = CamelCaseUtil.transform_result(row)
            item['isOwner'] = str(row.get('role')) == '0'
            if row.get('create_time'):
                item['createTime'] = row['create_time'].strftime('%Y-%m-%d')
            result.append(item)

        return result

    @classmethod
    async def create_services(cls, query_db: AsyncSession, user_id: int, page_object: LedgerModel) -> CrudResponseModel:
        """
        创建共享账本

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 账本对象
        :return: 操作结果
        """
        if not page_object.ledger_name or not page_object.ledger_name.strip():
            raise ServiceException(message='账本名称不能为空')
        code = cls._generate_code()
        while await AccountLedgerDao.get_ledger_by_code(query_db, code):
            code = cls._generate_code()
        page_object.owner_id = user_id
        page_object.invite_code = code
        page_object.is_default = '0'
        page_object.status = '0'
        page_object.create_by = page_object.create_by or ''
        page_object.update_by = page_object.update_by or ''
        try:
            ledger = await AccountLedgerDao.add_ledger_dao(query_db, page_object)
            await AccountLedgerDao.add_member_dao(query_db, ledger.ledger_id, user_id, '0')
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='账本已创建')

    @classmethod
    async def join_services(cls, query_db: AsyncSession, user_id: int, invite_code: str) -> CrudResponseModel:
        """
        通过邀请码加入账本

        :param query_db: orm对象
        :param user_id: 用户ID
        :param invite_code: 邀请码
        :return: 操作结果
        """
        code = (invite_code or '').strip().upper()
        if not code:
            raise ServiceException(message='请输入邀请码')
        ledger = await AccountLedgerDao.get_ledger_by_code(query_db, code)
        if not ledger:
            raise ServiceException(message='邀请码无效')
        exists = await AccountLedgerDao.get_member(query_db, ledger.ledger_id, user_id)
        if exists:
            raise ServiceException(message='你已经在账本中了')
        try:
            await AccountLedgerDao.add_member_dao(query_db, ledger.ledger_id, user_id, '1')
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message=f'已加入「{ledger.ledger_name}」')

    @classmethod
    async def members_services(cls, query_db: AsyncSession, user_id: int, ledger_id: int) -> dict[str, Any]:
        """
        获取账本成员

        :param query_db: orm对象
        :param user_id: 用户ID
        :param ledger_id: 账本ID
        :return: 账本信息与成员列表
        """
        member = await AccountLedgerDao.get_member(query_db, ledger_id, user_id)
        if not member:
            raise ServiceException(message='无权查看该账本')
        ledger = await AccountLedgerDao.get_ledger_by_id(query_db, ledger_id)
        rows = await AccountLedgerDao.get_members(query_db, ledger_id)

        return {
            'ledgerId': ledger_id,
            'ledgerName': ledger.ledger_name if ledger else '',
            'inviteCode': ledger.invite_code if ledger else '',
            'isOwner': member.role == '0',
            'members': [
                {
                    'userId': row['user_id'],
                    'userName': row.get('nick_name') or row.get('user_name') or f'用户{row["user_id"]}',
                    'role': row.get('role'),
                    'joinTime': row['create_time'].strftime('%Y-%m-%d') if row.get('create_time') else '',
                }
                for row in rows
            ],
        }

    @classmethod
    async def leave_services(cls, query_db: AsyncSession, user_id: int, ledger_id: int) -> CrudResponseModel:
        """
        退出共享账本（默认账本不可退出）

        :param query_db: orm对象
        :param user_id: 用户ID
        :param ledger_id: 账本ID
        :return: 操作结果
        """
        ledger = await AccountLedgerDao.get_ledger_by_id(query_db, ledger_id)
        if not ledger:
            raise ServiceException(message='账本不存在')
        if ledger.owner_id == user_id:
            raise ServiceException(message='拥有者不能退出自己的账本')
        try:
            await AccountLedgerDao.remove_member_dao(query_db, ledger_id, user_id)
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='已退出账本')

    @classmethod
    async def rename_services(cls, query_db: AsyncSession, user_id: int, page_object: LedgerModel) -> CrudResponseModel:
        """
        重命名账本（仅拥有者）

        :param query_db: orm对象
        :param user_id: 用户ID
        :param page_object: 账本对象
        :return: 操作结果
        """
        ledger = await AccountLedgerDao.get_ledger_by_id(query_db, page_object.ledger_id)
        if not ledger or ledger.owner_id != user_id:
            raise ServiceException(message='账本不存在或无权操作')
        try:
            await AccountLedgerDao.update_ledger_dao(
                query_db, {'ledger_id': page_object.ledger_id, 'ledger_name': page_object.ledger_name}
            )
            await query_db.commit()
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(is_success=True, message='已重命名')
