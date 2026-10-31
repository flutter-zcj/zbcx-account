import uuid
from pathlib import Path
from typing import Annotated

from fastapi import File, Header, Path as PathParam, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_session import DBSessionDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from exceptions.exception import ServiceException
from module_account.entity.vo.account_vo import (
    AccountModel,
    BillModel,
    BillPageQueryModel,
    BudgetModel,
    CategoryModel,
    CategoryStatModel,
    LedgerModel,
    MonthStatModel,
    RecurringModel,
    SummaryModel,
)
from module_account.service.ai_service import AccountAiService
from module_account.service.ocr_service import AccountOcrService
from module_account.service.account_service import (
    AccountAccountService,
    AccountBillService,
    AccountBudgetService,
    AccountCategoryService,
    AccountLedgerService,
    AccountRecurringService,
)
from module_admin.entity.vo.user_vo import CurrentUserModel
from utils.log_util import logger
from utils.response_util import ResponseUtil

account_controller = APIRouterPro(
    prefix='/account', order_num=60, tags=['记账管理'], dependencies=[PreAuthDependency()]
)

# 图片上传目录，与 nginx 的 /account/ 静态目录保持一致
UPLOAD_DIR = Path('/www/wwwroot/account/uploads')
ALLOWED_IMAGE_SUFFIX = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _parse_ids(ids: str) -> list[int]:
    """
    解析逗号分隔的ID字符串

    :param ids: 逗号分隔的ID
    :return: ID列表
    """
    return [int(item) for item in ids.split(',') if item.strip().isdigit()]


@account_controller.get(
    '/category/list',
    summary='获取记账分类列表接口',
    description='用于获取当前用户的记账分类列表',
    response_model=DataResponseModel[list[CategoryModel]],
)
async def get_account_category_list(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    category_type: Annotated[str | None, Query(alias='categoryType', description='分类类型（0支出 1收入）')] = None,
) -> Response:
    category_list = await AccountCategoryService.get_category_list_services(
        query_db, current_user.user.user_id, category_type
    )
    logger.info('获取记账分类列表成功')

    return ResponseUtil.success(data=category_list)


@account_controller.post(
    '/category',
    summary='新增记账分类接口',
    description='用于新增当前用户的记账分类',
    response_model=ResponseBaseModel,
)
@Log(title='记账分类', business_type=BusinessType.INSERT)
async def add_account_category(
    request: Request,
    add_category: CategoryModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_category.create_by = current_user.user.user_name
    add_category.update_by = current_user.user.user_name
    result = await AccountCategoryService.add_category_services(query_db, current_user.user.user_id, add_category)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.put(
    '/category',
    summary='修改记账分类接口',
    description='用于修改当前用户的记账分类',
    response_model=ResponseBaseModel,
)
@Log(title='记账分类', business_type=BusinessType.UPDATE)
async def edit_account_category(
    request: Request,
    edit_category: CategoryModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_category.update_by = current_user.user.user_name
    result = await AccountCategoryService.edit_category_services(query_db, current_user.user.user_id, edit_category)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.delete(
    '/category/{category_ids}',
    summary='删除记账分类接口',
    description='用于删除当前用户的记账分类',
    response_model=ResponseBaseModel,
)
@Log(title='记账分类', business_type=BusinessType.DELETE)
async def delete_account_category(
    request: Request,
    category_ids: Annotated[str, PathParam(alias='category_ids', description='逗号分隔的分类ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountCategoryService.delete_category_services(
        query_db, current_user.user.user_id, _parse_ids(category_ids)
    )
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.get(
    '/account/list',
    summary='获取资产账户列表接口',
    description='用于获取当前用户的资产账户列表，含实时余额与总资产',
    response_model=DataResponseModel[dict],
)
async def get_account_account_list(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountAccountService.get_account_balance_services(query_db, current_user.user.user_id)
    logger.info('获取资产账户列表成功')

    return ResponseUtil.success(data=result)


@account_controller.post(
    '/account',
    summary='新增资产账户接口',
    description='用于新增当前用户的资产账户',
    response_model=ResponseBaseModel,
)
@Log(title='记账账户', business_type=BusinessType.INSERT)
async def add_account_account(
    request: Request,
    add_account: AccountModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_account.create_by = current_user.user.user_name
    add_account.update_by = current_user.user.user_name
    result = await AccountAccountService.add_account_services(query_db, current_user.user.user_id, add_account)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.put(
    '/account',
    summary='修改资产账户接口',
    description='用于修改当前用户的资产账户',
    response_model=ResponseBaseModel,
)
@Log(title='记账账户', business_type=BusinessType.UPDATE)
async def edit_account_account(
    request: Request,
    edit_account: AccountModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_account.update_by = current_user.user.user_name
    result = await AccountAccountService.edit_account_services(query_db, current_user.user.user_id, edit_account)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.delete(
    '/account/{account_ids}',
    summary='删除资产账户接口',
    description='用于删除当前用户的资产账户',
    response_model=ResponseBaseModel,
)
@Log(title='记账账户', business_type=BusinessType.DELETE)
async def delete_account_account(
    request: Request,
    account_ids: Annotated[str, PathParam(alias='account_ids', description='逗号分隔的账户ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountAccountService.delete_account_services(
        query_db, current_user.user.user_id, _parse_ids(account_ids)
    )
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.get(
    '/bill/list',
    summary='获取账单分页列表接口',
    description='用于获取当前用户的账单分页列表',
    response_model=PageResponseModel[BillModel],
)
async def get_account_bill_list(
    request: Request,
    bill_page_query: Annotated[BillPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    x_ledger_id: Annotated[int | None, Header(alias='X-Ledger-Id')] = None,
) -> Response:
    ledger_id = await AccountLedgerService.resolve_ledger_id(query_db, current_user.user.user_id, x_ledger_id)
    bill_list = await AccountBillService.get_bill_list_services(
        query_db, current_user.user.user_id, bill_page_query, is_page=True, ledger_id=ledger_id
    )
    logger.info('获取账单列表成功')

    return ResponseUtil.success(model_content=bill_list)


@account_controller.get(
    '/bill/{bill_id}',
    summary='获取账单详情接口',
    description='用于获取当前用户单条账单详情，供编辑回显',
    response_model=DataResponseModel[dict],
)
async def get_account_bill_detail(
    request: Request,
    bill_id: Annotated[int, PathParam(alias='bill_id', description='账单ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    detail = await AccountBillService.get_bill_detail_services(query_db, current_user.user.user_id, bill_id)
    logger.info('获取账单详情成功')

    return ResponseUtil.success(data=detail)


@account_controller.post(
    '/bill',
    summary='新增账单接口',
    description='用于新增当前用户的账单，支持支出、收入与转账',
    response_model=ResponseBaseModel,
)
@Log(title='记账账单', business_type=BusinessType.INSERT)
async def add_account_bill(
    request: Request,
    add_bill: BillModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    x_ledger_id: Annotated[int | None, Header(alias='X-Ledger-Id')] = None,
) -> Response:
    ledger_id = await AccountLedgerService.resolve_ledger_id(query_db, current_user.user.user_id, x_ledger_id)
    add_bill.create_by = current_user.user.user_name
    add_bill.update_by = current_user.user.user_name
    result = await AccountBillService.add_bill_services(
        query_db, current_user.user.user_id, add_bill, ledger_id=ledger_id
    )
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.put(
    '/bill',
    summary='修改账单接口',
    description='用于修改当前用户的账单',
    response_model=ResponseBaseModel,
)
@Log(title='记账账单', business_type=BusinessType.UPDATE)
async def edit_account_bill(
    request: Request,
    edit_bill: BillModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_bill.update_by = current_user.user.user_name
    result = await AccountBillService.edit_bill_services(query_db, current_user.user.user_id, edit_bill)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.delete(
    '/bill/{bill_ids}',
    summary='删除账单接口',
    description='用于删除当前用户的账单',
    response_model=ResponseBaseModel,
)
@Log(title='记账账单', business_type=BusinessType.DELETE)
async def delete_account_bill(
    request: Request,
    bill_ids: Annotated[str, PathParam(alias='bill_ids', description='逗号分隔的账单ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountBillService.delete_bill_services(query_db, current_user.user.user_id, _parse_ids(bill_ids))
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.get(
    '/stat/summary',
    summary='收支汇总统计接口',
    description='用于统计当前用户在指定日期范围内的收入、支出与结余（不含转账）',
    response_model=DataResponseModel[SummaryModel],
)
async def get_account_stat_summary(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    begin_date: Annotated[str | None, Query(alias='beginDate', description='开始日期（YYYY-MM-DD）')] = None,
    end_date: Annotated[str | None, Query(alias='endDate', description='结束日期（YYYY-MM-DD）')] = None,
    x_ledger_id: Annotated[int | None, Header(alias='X-Ledger-Id')] = None,
) -> Response:
    ledger_id = await AccountLedgerService.resolve_ledger_id(query_db, current_user.user.user_id, x_ledger_id)
    summary = await AccountBillService.summary_services(
        query_db, current_user.user.user_id, begin_date, end_date, ledger_id=ledger_id
    )
    logger.info('收支汇总统计成功')

    return ResponseUtil.success(model_content=summary)


@account_controller.get(
    '/stat/category',
    summary='分类占比统计接口',
    description='用于按分类统计当前用户的收支占比',
    response_model=DataResponseModel[list[CategoryStatModel]],
)
async def get_account_stat_category(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    bill_type: Annotated[str, Query(alias='billType', description='账单类型（0支出 1收入）')] = '0',
    begin_date: Annotated[str | None, Query(alias='beginDate', description='开始日期（YYYY-MM-DD）')] = None,
    end_date: Annotated[str | None, Query(alias='endDate', description='结束日期（YYYY-MM-DD）')] = None,
    x_ledger_id: Annotated[int | None, Header(alias='X-Ledger-Id')] = None,
) -> Response:
    ledger_id = await AccountLedgerService.resolve_ledger_id(query_db, current_user.user.user_id, x_ledger_id)
    stat_list = await AccountBillService.category_stat_services(
        query_db, current_user.user.user_id, bill_type, begin_date, end_date, ledger_id=ledger_id
    )
    logger.info('分类占比统计成功')

    return ResponseUtil.success(data=[item.model_dump(by_alias=True) for item in stat_list])


@account_controller.get(
    '/stat/rank',
    summary='排行榜统计接口',
    description='用于统计当前用户的分类排行与单笔排行',
    response_model=DataResponseModel[dict],
)
async def get_account_stat_rank(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    bill_type: Annotated[str, Query(alias='billType', description='账单类型（0支出 1收入）')] = '0',
    begin_date: Annotated[str | None, Query(alias='beginDate', description='开始日期（YYYY-MM-DD）')] = None,
    end_date: Annotated[str | None, Query(alias='endDate', description='结束日期（YYYY-MM-DD）')] = None,
    limit: Annotated[int, Query(description='返回条数')] = 10,
) -> Response:
    result = await AccountBillService.rank_services(
        query_db, current_user.user.user_id, bill_type, begin_date, end_date, limit
    )
    logger.info('排行榜统计成功')

    return ResponseUtil.success(
        data={key: [item.model_dump(by_alias=True) for item in value] for key, value in result.items()}
    )


@account_controller.get(
    '/stat/trend',
    summary='月度趋势统计接口',
    description='用于统计当前用户近几个月的收支趋势',
    response_model=DataResponseModel[list[MonthStatModel]],
)
async def get_account_stat_trend(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    months: Annotated[int, Query(description='统计月份数量')] = 6,
) -> Response:
    trend_list = await AccountBillService.trend_services(query_db, current_user.user.user_id, months)
    logger.info('月度趋势统计成功')

    return ResponseUtil.success(data=[item.model_dump(by_alias=True) for item in trend_list])


@account_controller.get(
    '/budget',
    summary='获取预算接口',
    description='用于获取当前用户指定月份的预算与执行进度',
    response_model=DataResponseModel[dict],
)
async def get_account_budget(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    budget_month: Annotated[str, Query(alias='budgetMonth', description='预算月份（YYYY-MM）')],
) -> Response:
    result = await AccountBudgetService.get_budget_services(query_db, current_user.user.user_id, budget_month)
    logger.info('获取预算成功')

    return ResponseUtil.success(data=result)


@account_controller.post(
    '/budget',
    summary='保存预算接口',
    description='用于保存当前用户指定月份的预算，金额为0表示删除该条预算',
    response_model=ResponseBaseModel,
)
@Log(title='记账预算', business_type=BusinessType.UPDATE)
async def save_account_budget(
    request: Request,
    save_budget: BudgetModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    save_budget.create_by = current_user.user.user_name
    save_budget.update_by = current_user.user.user_name
    result = await AccountBudgetService.save_budget_services(query_db, current_user.user.user_id, save_budget)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.post(
    '/upload',
    summary='上传记账图片接口',
    description='用于上传记账凭证图片，返回可直接访问的相对地址',
    response_model=DataResponseModel[dict],
)
async def upload_account_image(
    request: Request,
    file: Annotated[UploadFile, File(description='图片文件')],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIX:
        raise ServiceException(message='仅支持 jpg、png、webp、gif 格式图片')
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise ServiceException(message='图片不能超过 5MB')
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f'{uuid.uuid4().hex}{suffix}'
    (UPLOAD_DIR / file_name).write_bytes(content)
    logger.info('记账图片上传成功')

    return ResponseUtil.success(data={'url': f'/account/uploads/{file_name}'})


@account_controller.get(
    '/recurring/list',
    summary='获取周期记账规则列表接口',
    description='用于获取当前用户的周期记账规则，并补记到期账单',
    response_model=DataResponseModel[list[dict]],
)
async def get_account_recurring_list(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountRecurringService.get_list_services(query_db, current_user.user.user_id)
    logger.info('获取周期规则列表成功')

    return ResponseUtil.success(data=result)


@account_controller.post(
    '/recurring',
    summary='新增周期记账规则接口',
    description='用于创建房租、订阅等周期性账单',
    response_model=ResponseBaseModel,
)
@Log(title='周期记账', business_type=BusinessType.INSERT)
async def add_account_recurring(
    request: Request,
    add_recurring: RecurringModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_recurring.create_by = current_user.user.user_name
    add_recurring.update_by = current_user.user.user_name
    result = await AccountRecurringService.add_services(query_db, current_user.user.user_id, add_recurring)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.put(
    '/recurring',
    summary='修改周期记账规则接口',
    description='用于修改周期记账规则',
    response_model=ResponseBaseModel,
)
@Log(title='周期记账', business_type=BusinessType.UPDATE)
async def edit_account_recurring(
    request: Request,
    edit_recurring: RecurringModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_recurring.update_by = current_user.user.user_name
    result = await AccountRecurringService.edit_services(query_db, current_user.user.user_id, edit_recurring)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.delete(
    '/recurring/{recurring_ids}',
    summary='删除周期记账规则接口',
    description='用于删除周期记账规则，已生成的账单保留',
    response_model=ResponseBaseModel,
)
@Log(title='周期记账', business_type=BusinessType.DELETE)
async def delete_account_recurring(
    request: Request,
    recurring_ids: Annotated[str, PathParam(alias='recurring_ids', description='逗号分隔的规则ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountRecurringService.delete_services(
        query_db, current_user.user.user_id, _parse_ids(recurring_ids)
    )
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.post(
    '/recurring/{recurring_id}/toggle',
    summary='启用或暂停周期规则接口',
    description='用于切换周期记账规则的启用状态',
    response_model=ResponseBaseModel,
)
@Log(title='周期记账', business_type=BusinessType.UPDATE)
async def toggle_account_recurring(
    request: Request,
    recurring_id: Annotated[int, PathParam(alias='recurring_id', description='规则ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountRecurringService.toggle_services(query_db, current_user.user.user_id, recurring_id)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.post(
    '/ai/parse',
    summary='自然语言解析记账接口',
    description='把「午饭 35 微信」这类口语解析为结构化账单，可选用大模型',
    response_model=DataResponseModel[dict],
)
async def parse_account_text(
    request: Request,
    payload: dict,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    text = str((payload or {}).get('text', ''))
    result = await AccountAiService.parse_services(query_db, current_user.user.user_id, text)
    logger.info(f'AI 记账解析：{text[:30]} -> {result.get("success")}')

    return ResponseUtil.success(data=result)


@account_controller.get(
    '/ledger/list',
    summary='获取账本列表接口',
    description='用于获取当前用户可用的账本（含共享账本）',
    response_model=DataResponseModel[list[dict]],
)
async def get_account_ledger_list(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountLedgerService.get_list_services(query_db, current_user.user.user_id)
    logger.info('获取账本列表成功')

    return ResponseUtil.success(data=result)


@account_controller.post(
    '/ledger',
    summary='创建共享账本接口',
    description='用于创建一个可邀请他人加入的账本',
    response_model=ResponseBaseModel,
)
@Log(title='记账账本', business_type=BusinessType.INSERT)
async def add_account_ledger(
    request: Request,
    add_ledger: LedgerModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_ledger.create_by = current_user.user.user_name
    add_ledger.update_by = current_user.user.user_name
    result = await AccountLedgerService.create_services(query_db, current_user.user.user_id, add_ledger)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.put(
    '/ledger',
    summary='重命名账本接口',
    description='用于修改账本名称，仅拥有者可操作',
    response_model=ResponseBaseModel,
)
@Log(title='记账账本', business_type=BusinessType.UPDATE)
async def edit_account_ledger(
    request: Request,
    edit_ledger: LedgerModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountLedgerService.rename_services(query_db, current_user.user.user_id, edit_ledger)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.post(
    '/ledger/join',
    summary='加入账本接口',
    description='通过邀请码加入共享账本',
    response_model=ResponseBaseModel,
)
@Log(title='记账账本', business_type=BusinessType.INSERT)
async def join_account_ledger(
    request: Request,
    payload: dict,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountLedgerService.join_services(
        query_db, current_user.user.user_id, str((payload or {}).get('inviteCode', ''))
    )
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.get(
    '/ledger/{ledger_id}/members',
    summary='获取账本成员接口',
    description='用于查看账本成员与邀请码',
    response_model=DataResponseModel[dict],
)
async def get_account_ledger_members(
    request: Request,
    ledger_id: Annotated[int, PathParam(alias='ledger_id', description='账本ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountLedgerService.members_services(query_db, current_user.user.user_id, ledger_id)
    logger.info('获取账本成员成功')

    return ResponseUtil.success(data=result)


@account_controller.post(
    '/ledger/{ledger_id}/leave',
    summary='退出账本接口',
    description='用于退出共享账本',
    response_model=ResponseBaseModel,
)
@Log(title='记账账本', business_type=BusinessType.DELETE)
async def leave_account_ledger(
    request: Request,
    ledger_id: Annotated[int, PathParam(alias='ledger_id', description='账本ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    result = await AccountLedgerService.leave_services(query_db, current_user.user.user_id, ledger_id)
    logger.info(result.message)

    return ResponseUtil.success(msg=result.message)


@account_controller.post(
    '/ocr',
    summary='图片识别记账接口',
    description='上传支付截图或小票，识别金额、商户与日期',
    response_model=DataResponseModel[dict],
)
async def ocr_account_image(
    request: Request,
    file: Annotated[UploadFile, File(description='账单截图')],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    suffix = Path(file.filename or '').suffix.lower() or '.png'
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise ServiceException(message='图片不能超过 5MB')
    result = await AccountOcrService.recognize_services(content, suffix)
    logger.info(f'图片识别：金额={result.get("amount")} 商户={result.get("merchant")}')

    return ResponseUtil.success(data=result)
