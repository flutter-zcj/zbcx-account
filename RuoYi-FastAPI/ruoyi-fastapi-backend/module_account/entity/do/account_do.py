from sqlalchemy import CHAR, Column, Date, Integer, Numeric, String, Text

from common.mixin import AuditTimeMixin
from config.database import Base


class AcctCategory(AuditTimeMixin, Base):
    """
    记账分类表
    """

    __tablename__ = 't_acct_category'
    __table_args__ = {'comment': '记账分类表'}

    category_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='分类ID')
    user_id = Column(Integer, nullable=False, index=True, comment='所属用户ID')
    category_name = Column(String(30), nullable=False, comment='分类名称')
    category_type = Column(CHAR(1), nullable=False, comment='分类类型（0支出 1收入）')
    icon = Column(String(50), nullable=True, server_default='wallet', comment='分类图标标识')
    color = Column(String(20), nullable=True, server_default='#1AA86C', comment='分类颜色')
    sort_num = Column(Integer, nullable=True, server_default='0', comment='显示顺序')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1停用）')
    del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0存在 2删除）')
    create_by = Column(String(64), nullable=True, server_default='', comment='创建者')
    update_by = Column(String(64), nullable=True, server_default='', comment='更新者')
    remark = Column(String(255), nullable=True, comment='备注')


class AcctAccount(AuditTimeMixin, Base):
    """
    记账资产账户表

    余额不落库，由账目实时聚合：期初余额 + 收入 - 支出 ± 转账
    """

    __tablename__ = 't_acct_account'
    __table_args__ = {'comment': '记账资产账户表'}

    account_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='账户ID')
    user_id = Column(Integer, nullable=False, index=True, comment='所属用户ID')
    account_name = Column(String(30), nullable=False, comment='账户名称')
    account_type = Column(CHAR(1), nullable=False, server_default='0', comment='账户类型（0现金 1储蓄卡 2信用卡 3花呗 4理财 5借入 6借出）')
    icon = Column(String(50), nullable=True, server_default='wallet', comment='账户图标标识')
    color = Column(String(20), nullable=True, server_default='#1AA86C', comment='账户颜色')
    init_balance = Column(Numeric(12, 2), nullable=False, server_default='0', comment='期初余额')
    is_include = Column(CHAR(1), nullable=True, server_default='0', comment='是否计入总资产（0计入 1不计入）')
    sort_num = Column(Integer, nullable=True, server_default='0', comment='显示顺序')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1停用）')
    del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0存在 2删除）')
    create_by = Column(String(64), nullable=True, server_default='', comment='创建者')
    update_by = Column(String(64), nullable=True, server_default='', comment='更新者')
    remark = Column(String(255), nullable=True, comment='备注')


class AcctBill(AuditTimeMixin, Base):
    """
    记账账单表
    """

    __tablename__ = 't_acct_bill'
    __table_args__ = {'comment': '记账账单表'}

    bill_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='账单ID')
    user_id = Column(Integer, nullable=False, index=True, comment='所属用户ID')
    category_id = Column(Integer, nullable=True, comment='分类ID')
    bill_type = Column(CHAR(1), nullable=False, comment='账单类型（0支出 1收入 2转账）')
    amount = Column(Numeric(12, 2), nullable=False, server_default='0', comment='金额')
    bill_date = Column(Date, nullable=False, comment='账单日期')
    pay_method = Column(String(20), nullable=True, server_default='cash', comment='支付方式')
    account_id = Column(Integer, nullable=True, index=True, comment='账户ID（支出为付款账户，转账为转出账户）')
    to_account_id = Column(Integer, nullable=True, index=True, comment='转入账户ID（仅转账使用）')
    tag = Column(String(20), nullable=True, comment='标签')
    images = Column(Text, nullable=True, comment='图片地址JSON数组')
    recurring_id = Column(Integer, nullable=True, index=True, comment='来源周期规则ID')
    ledger_id = Column(Integer, nullable=True, index=True, comment='所属账本ID')
    remark = Column(String(255), nullable=True, comment='备注')
    del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0存在 2删除）')
    create_by = Column(String(64), nullable=True, server_default='', comment='创建者')
    update_by = Column(String(64), nullable=True, server_default='', comment='更新者')


class AcctBudget(AuditTimeMixin, Base):
    """
    记账预算表

    category_id 为空表示当月总预算，不为空表示分类预算
    """

    __tablename__ = 't_acct_budget'
    __table_args__ = {'comment': '记账预算表'}

    budget_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='预算ID')
    user_id = Column(Integer, nullable=False, index=True, comment='所属用户ID')
    budget_month = Column(String(7), nullable=False, comment='预算月份（YYYY-MM）')
    category_id = Column(Integer, nullable=True, comment='分类ID（为空表示总预算）')
    amount = Column(Numeric(12, 2), nullable=False, server_default='0', comment='预算金额')
    create_by = Column(String(64), nullable=True, server_default='', comment='创建者')
    update_by = Column(String(64), nullable=True, server_default='', comment='更新者')


class AcctRecurring(AuditTimeMixin, Base):
    """
    记账周期规则表

    到期后由服务层懒执行生成账单，规则本身不产生金额
    """

    __tablename__ = 't_acct_recurring'
    __table_args__ = {'comment': '记账周期规则表'}

    recurring_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='规则ID')
    user_id = Column(Integer, nullable=False, index=True, comment='所属用户ID')
    title = Column(String(30), nullable=False, comment='规则名称')
    bill_type = Column(CHAR(1), nullable=False, server_default='0', comment='账单类型（0支出 1收入 2转账）')
    amount = Column(Numeric(12, 2), nullable=False, server_default='0', comment='金额')
    category_id = Column(Integer, nullable=True, comment='分类ID')
    account_id = Column(Integer, nullable=True, comment='账户ID')
    to_account_id = Column(Integer, nullable=True, comment='转入账户ID（仅转账）')
    tag = Column(String(20), nullable=True, comment='标签')
    remark = Column(String(255), nullable=True, comment='备注')
    pay_method = Column(String(20), nullable=True, server_default='cash', comment='支付方式')
    rule_type = Column(CHAR(1), nullable=False, server_default='2', comment='周期类型（0每天 1每周 2每月 3每年）')
    interval_num = Column(Integer, nullable=False, server_default='1', comment='间隔数')
    day_of_month = Column(Integer, nullable=True, comment='每月几号（1-31）')
    day_of_week = Column(Integer, nullable=True, comment='每周几（1-7）')
    start_date = Column(Date, nullable=False, comment='开始日期')
    end_date = Column(Date, nullable=True, comment='结束日期')
    next_run_date = Column(Date, nullable=False, index=True, comment='下次生成日期')
    last_run_date = Column(Date, nullable=True, comment='上次生成日期')
    run_count = Column(Integer, nullable=False, server_default='0', comment='已生成次数')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0启用 1暂停）')
    del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0存在 2删除）')
    create_by = Column(String(64), nullable=True, server_default='', comment='创建者')
    update_by = Column(String(64), nullable=True, server_default='', comment='更新者')


class AcctLedger(AuditTimeMixin, Base):
    """
    记账账本表

    每个用户默认有一个「我的账本」，可创建共享账本邀请他人加入
    """

    __tablename__ = 't_acct_ledger'
    __table_args__ = {'comment': '记账账本表'}

    ledger_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='账本ID')
    owner_id = Column(Integer, nullable=False, index=True, comment='拥有者用户ID')
    ledger_name = Column(String(30), nullable=False, comment='账本名称')
    invite_code = Column(String(12), nullable=True, unique=True, comment='邀请码')
    is_default = Column(CHAR(1), nullable=True, server_default='1', comment='是否默认账本（0否 1是）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1停用）')
    del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0存在 2删除）')
    create_by = Column(String(64), nullable=True, server_default='', comment='创建者')
    update_by = Column(String(64), nullable=True, server_default='', comment='更新者')


class AcctLedgerMember(AuditTimeMixin, Base):
    """
    记账账本成员表
    """

    __tablename__ = 't_acct_ledger_member'
    __table_args__ = {'comment': '记账账本成员表'}

    member_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='成员ID')
    ledger_id = Column(Integer, nullable=False, index=True, comment='账本ID')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    role = Column(CHAR(1), nullable=True, server_default='1', comment='角色（0拥有者 1成员）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1退出）')
    del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0存在 2删除）')
    create_by = Column(String(64), nullable=True, server_default='', comment='创建者')
    update_by = Column(String(64), nullable=True, server_default='', comment='更新者')
