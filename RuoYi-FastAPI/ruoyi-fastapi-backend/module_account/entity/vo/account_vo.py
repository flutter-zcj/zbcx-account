from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_validation_decorator import NotBlank, Size

from common.types import ApiUtcDateTime


class CategoryModel(BaseModel):
    """
    记账分类表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    category_id: int | None = Field(default=None, description='分类ID')
    user_id: int | None = Field(default=None, description='所属用户ID')
    category_name: str | None = Field(default=None, description='分类名称')
    category_type: Literal['0', '1'] | None = Field(default=None, description='分类类型（0支出 1收入）')
    icon: str | None = Field(default='wallet', description='分类图标标识')
    color: str | None = Field(default='#1AA86C', description='分类颜色')
    sort_num: int | None = Field(default=0, description='显示顺序')
    status: Literal['0', '1'] | None = Field(default='0', description='状态（0正常 1停用）')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: ApiUtcDateTime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: ApiUtcDateTime | None = Field(default=None, description='更新时间')
    remark: str | None = Field(default=None, description='备注')

    @NotBlank(field_name='category_name', message='分类名称不能为空')
    @Size(field_name='category_name', min_length=0, max_length=30, message='分类名称不能超过30个字符')
    def get_category_name(self) -> str | None:
        return self.category_name

    def validate_fields(self) -> None:
        self.get_category_name()


class CategoryQueryModel(CategoryModel):
    """
    记账分类查询模型
    """


class AccountModel(BaseModel):
    """
    记账资产账户表对应pydantic模型

    balance、expense、income 为实时聚合结果，不落库
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    account_id: int | None = Field(default=None, description='账户ID')
    user_id: int | None = Field(default=None, description='所属用户ID')
    account_name: str | None = Field(default=None, description='账户名称')
    account_type: Literal['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] | None = Field(
        default='0', description='账户类型（0现金 1储蓄卡 2信用卡 3花呗 4理财 5借入 6借出 7微信 8支付宝 9其他）'
    )
    icon: str | None = Field(default='wallet', description='账户图标标识')
    color: str | None = Field(default='#1AA86C', description='账户颜色')
    init_balance: float | None = Field(default=0, description='期初余额')
    is_include: Literal['0', '1'] | None = Field(default='0', description='是否计入总资产（0计入 1不计入）')
    sort_num: int | None = Field(default=0, description='显示顺序')
    status: Literal['0', '1'] | None = Field(default='0', description='状态（0正常 1停用）')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: ApiUtcDateTime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: ApiUtcDateTime | None = Field(default=None, description='更新时间')
    remark: str | None = Field(default=None, description='备注')
    balance: float | None = Field(default=None, description='当前余额（实时聚合）')
    expense: float | None = Field(default=None, description='累计支出（实时聚合）')
    income: float | None = Field(default=None, description='累计收入（实时聚合）')

    @NotBlank(field_name='account_name', message='账户名称不能为空')
    @Size(field_name='account_name', min_length=0, max_length=30, message='账户名称不能超过30个字符')
    def get_account_name(self) -> str | None:
        return self.account_name

    def validate_fields(self) -> None:
        self.get_account_name()


class BillModel(BaseModel):
    """
    记账账单表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    bill_id: int | None = Field(default=None, description='账单ID')
    user_id: int | None = Field(default=None, description='所属用户ID')
    category_id: int | None = Field(default=None, description='分类ID')
    bill_type: Literal['0', '1', '2'] | None = Field(default='0', description='账单类型（0支出 1收入 2转账）')
    amount: float | None = Field(default=None, description='金额')
    bill_date: date | None = Field(default=None, description='账单日期')
    pay_method: str | None = Field(default='cash', description='支付方式')
    account_id: int | None = Field(default=None, description='账户ID（支出为付款账户，转账为转出账户）')
    to_account_id: int | None = Field(default=None, description='转入账户ID（仅转账使用）')
    tag: str | None = Field(default=None, description='标签')
    images: str | None = Field(default=None, description='图片地址JSON数组')
    ledger_id: int | None = Field(default=None, description='所属账本ID')
    recurring_id: int | None = Field(default=None, description='来源周期规则ID')
    remark: str | None = Field(default=None, description='备注')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: ApiUtcDateTime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: ApiUtcDateTime | None = Field(default=None, description='更新时间')
    category_name: str | None = Field(default=None, description='分类名称（关联查询展示）')
    category_icon: str | None = Field(default=None, description='分类图标（关联查询展示）')
    category_color: str | None = Field(default=None, description='分类颜色（关联查询展示）')
    account_name: str | None = Field(default=None, description='账户名称（关联查询展示）')
    to_account_name: str | None = Field(default=None, description='转入账户名称（关联查询展示）')


class BillPageQueryModel(BaseModel):
    """
    记账账单分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')
    bill_type: Literal['0', '1', '2'] | None = Field(default=None, description='账单类型（0支出 1收入 2转账）')
    category_id: int | None = Field(default=None, description='分类ID')
    account_id: int | None = Field(default=None, description='账户ID')
    begin_date: str | None = Field(default=None, description='开始日期（YYYY-MM-DD）')
    end_date: str | None = Field(default=None, description='结束日期（YYYY-MM-DD）')
    keyword: str | None = Field(default=None, description='关键字（分类/标签/备注/金额）')
    tag: str | None = Field(default=None, description='标签')


class SummaryModel(BaseModel):
    """
    收支汇总模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    total_income: float = Field(default=0, description='收入合计')
    total_expense: float = Field(default=0, description='支出合计')
    balance: float = Field(default=0, description='结余')
    bill_count: int = Field(default=0, description='账单笔数')


class CategoryStatModel(BaseModel):
    """
    分类统计模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    category_id: int | None = Field(default=None, description='分类ID')
    category_name: str | None = Field(default=None, description='分类名称')
    category_color: str | None = Field(default=None, description='分类颜色')
    category_icon: str | None = Field(default=None, description='分类图标')
    bill_type: str | None = Field(default=None, description='账单类型（0支出 1收入）')
    amount: float = Field(default=0, description='金额合计')
    bill_count: int = Field(default=0, description='账单笔数')
    percent: float = Field(default=0, description='占比（百分比）')


class MonthStatModel(BaseModel):
    """
    月度趋势统计模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    month: str = Field(description='月份（YYYY-MM）')
    income: float = Field(default=0, description='收入合计')
    expense: float = Field(default=0, description='支出合计')


class RankItemModel(BaseModel):
    """
    排行榜条目模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    key: str | None = Field(default=None, description='排行键（分类ID或账单ID）')
    name: str | None = Field(default=None, description='名称')
    amount: float = Field(default=0, description='金额')
    bill_count: int = Field(default=0, description='笔数')
    percent: float = Field(default=0, description='占比（百分比）')
    color: str | None = Field(default=None, description='颜色')
    icon: str | None = Field(default=None, description='图标')


class BudgetModel(BaseModel):
    """
    预算模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    budget_id: int | None = Field(default=None, description='预算ID')
    user_id: int | None = Field(default=None, description='所属用户ID')
    budget_month: str | None = Field(default=None, description='预算月份（YYYY-MM）')
    category_id: int | None = Field(default=None, description='分类ID（为空表示总预算）')
    amount: float | None = Field(default=0, description='预算金额')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: ApiUtcDateTime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: ApiUtcDateTime | None = Field(default=None, description='更新时间')
    used: float | None = Field(default=None, description='已使用金额（实时聚合）')
    category_name: str | None = Field(default=None, description='分类名称（关联查询展示）')
    category_color: str | None = Field(default=None, description='分类颜色（关联查询展示）')


class BudgetSaveModel(BaseModel):
    """
    预算保存模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    budget_month: str = Field(description='预算月份（YYYY-MM）')
    total_amount: float | None = Field(default=None, description='当月总预算')
    category_budgets: list[BudgetModel] | None = Field(default=None, description='分类预算列表')


class RecurringModel(BaseModel):
    """
    记账周期规则模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    recurring_id: int | None = Field(default=None, description='规则ID')
    user_id: int | None = Field(default=None, description='所属用户ID')
    title: str | None = Field(default=None, description='规则名称')
    bill_type: Literal['0', '1', '2'] | None = Field(default='0', description='账单类型（0支出 1收入 2转账）')
    amount: float | None = Field(default=0, description='金额')
    category_id: int | None = Field(default=None, description='分类ID')
    account_id: int | None = Field(default=None, description='账户ID')
    to_account_id: int | None = Field(default=None, description='转入账户ID（仅转账）')
    tag: str | None = Field(default=None, description='标签')
    remark: str | None = Field(default=None, description='备注')
    pay_method: str | None = Field(default='cash', description='支付方式')
    rule_type: Literal['0', '1', '2', '3'] | None = Field(default='2', description='周期类型（0每天 1每周 2每月 3每年）')
    interval_num: int | None = Field(default=1, description='间隔数')
    day_of_month: int | None = Field(default=None, description='每月几号（1-31）')
    day_of_week: int | None = Field(default=None, description='每周几（1-7）')
    start_date: date | None = Field(default=None, description='开始日期')
    end_date: date | None = Field(default=None, description='结束日期')
    next_run_date: date | None = Field(default=None, description='下次生成日期')
    last_run_date: date | None = Field(default=None, description='上次生成日期')
    run_count: int | None = Field(default=0, description='已生成次数')
    status: Literal['0', '1'] | None = Field(default='0', description='状态（0启用 1暂停）')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: ApiUtcDateTime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: ApiUtcDateTime | None = Field(default=None, description='更新时间')
    category_name: str | None = Field(default=None, description='分类名称（关联查询展示）')
    category_icon: str | None = Field(default=None, description='分类图标（关联查询展示）')
    category_color: str | None = Field(default=None, description='分类颜色（关联查询展示）')
    account_name: str | None = Field(default=None, description='账户名称（关联查询展示）')

    @NotBlank(field_name='title', message='规则名称不能为空')
    @Size(field_name='title', min_length=0, max_length=30, message='规则名称不能超过30个字符')
    def get_title(self) -> str | None:
        return self.title

    def validate_fields(self) -> None:
        self.get_title()


class LedgerModel(BaseModel):
    """
    记账账本模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    ledger_id: int | None = Field(default=None, description='账本ID')
    owner_id: int | None = Field(default=None, description='拥有者用户ID')
    ledger_name: str | None = Field(default=None, description='账本名称')
    invite_code: str | None = Field(default=None, description='邀请码')
    is_default: Literal['0', '1'] | None = Field(default='1', description='是否默认账本')
    status: Literal['0', '1'] | None = Field(default='0', description='状态')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: ApiUtcDateTime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: ApiUtcDateTime | None = Field(default=None, description='更新时间')
    member_count: int | None = Field(default=None, description='成员数')
    bill_count: int | None = Field(default=None, description='账单数')
    owner_name: str | None = Field(default=None, description='拥有者名称')
    role: str | None = Field(default=None, description='当前用户角色（0拥有者 1成员）')

    @NotBlank(field_name='ledger_name', message='账本名称不能为空')
    @Size(field_name='ledger_name', min_length=0, max_length=30, message='账本名称不能超过30个字符')
    def get_ledger_name(self) -> str | None:
        return self.ledger_name

    def validate_fields(self) -> None:
        self.get_ledger_name()
