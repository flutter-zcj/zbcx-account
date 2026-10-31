import json
import os
import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from module_account.dao.account_dao import AccountAccountDao, AccountCategoryDao


class AccountAiService:
    """
    AI 记账解析服务

    默认使用规则引擎（零依赖、离线可用）；配置了 LLM 环境变量后优先走大模型，
    失败自动降级到规则引擎，保证功能始终可用。

    环境变量：
        ACCOUNT_LLM_KEY    接口密钥（不配置则只用规则引擎）
        ACCOUNT_LLM_BASE   接口地址，默认 OpenAI 兼容 https://api.openai.com/v1
        ACCOUNT_LLM_MODEL  模型名，默认 gpt-4o-mini
    """

    # 分类别名词典：命中别名即可归入对应分类
    CATEGORY_ALIAS: dict[str, tuple[str, ...]] = {
        '餐饮': ('吃饭', '午饭', '早餐', '午餐', '晚餐', '外卖', '咖啡', '奶茶', '宵夜', '聚餐', '食堂', '烧烤', '火锅', '面', '饭'),
        '交通': ('打车', '地铁', '公交', '加油', '停车', '高铁', '机票', '火车', '滴滴', '共享单车', '骑车', '油费'),
        '购物': ('买', '购物', '超市', '网购', '淘宝', '京东', '拼多多', '衣服', '鞋', '日用'),
        '居住': ('房租', '水电', '物业', '燃气', '宽带', '取暖'),
        '娱乐': ('电影', '游戏', 'ktv', '旅游', '门票', '演出', '健身'),
        '医疗': ('药', '医院', '看病', '体检', '挂号', '牙'),
        '学习': ('书', '课程', '培训', '学费', '考试', '文具'),
        '人情': ('礼金', '请客', '份子', '送礼', '红包'),
        '通讯': ('话费', '流量', '手机费', '充值'),
        '工资': ('工资', '薪水', '发薪'),
        '奖金': ('奖金', '年终奖', '绩效'),
        '理财': ('利息', '收益', '分红', '基金'),
        '兼职': ('兼职', '外快', '私活'),
        '红包': ('收红包', '压岁钱'),
    }

    INCOME_WORDS = ('收入', '工资', '薪水', '奖金', '收到', '报销', '利息', '收益', '分红', '退款', '退款', '卖了', '外快')
    ACCOUNT_ALIAS: dict[str, tuple[str, ...]] = {
        '微信': ('微信', 'wx', 'wechat'),
        '支付宝': ('支付宝', 'zfb', 'alipay', '花呗'),
        '现金': ('现金', '现钞'),
        '银行卡': ('银行卡', '储蓄卡', '借记卡', '刷卡', '信用卡'),
    }

    DATE_WORDS = {'今天': 0, '今日': 0, '昨天': 1, '昨日': 1, '前天': 2, '大前天': 3}

    AMOUNT_PATTERN = re.compile(r'(?:[¥￥$]\s*)?(\d+(?:\.\d{1,2})?)\s*(?:元|块|块钱)?')
    DATE_PATTERN = re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?')
    MONTH_DAY_PATTERN = re.compile(r'(\d{1,2})月(\d{1,2})[日号]')

    @classmethod
    async def parse_services(cls, query_db: AsyncSession, user_id: int, text: str) -> dict[str, Any]:
        """
        解析一句自然语言为结构化账单

        :param query_db: orm对象
        :param user_id: 用户ID
        :param text: 用户输入
        :return: 解析结果
        """
        content = (text or '').strip()
        if not content:
            return {'success': False, 'message': '请说说这笔账，比如「午饭 35 微信」'}

        categories = await AccountCategoryDao.get_category_list(query_db, user_id)
        accounts = await AccountAccountDao.get_account_list(query_db, user_id)

        llm_result = await cls._parse_with_llm(content, categories, accounts)
        if llm_result:
            llm_result['source'] = 'llm'
            return {'success': True, 'data': llm_result}

        result = cls._parse_with_rules(content, categories, accounts)
        result['source'] = 'rule'
        if not result.get('amount'):
            return {'success': False, 'message': '没听出金额，试试「午饭 35」这样的说法'}

        return {'success': True, 'data': result}

    @classmethod
    def _parse_with_rules(cls, text: str, categories: list, accounts: list) -> dict[str, Any]:
        """
        规则引擎解析

        :param text: 用户输入
        :param categories: 用户分类列表
        :param accounts: 用户账户列表
        :return: 解析结果
        """
        working = text
        bill_date = cls._extract_date(working)
        working = cls._strip_date(working)

        amount, amount_span = cls._extract_amount(working)
        if amount_span:
            working = working[: amount_span[0]] + working[amount_span[1] :]

        bill_type = '1' if any(word in text for word in cls.INCOME_WORDS) else '0'

        category = cls._match_category(working, categories, bill_type)
        account = cls._match_account(working, accounts)

        remark = cls._clean_remark(working, category, account)
        confidence = 'high' if amount and category else ('medium' if amount else 'low')

        return {
            'amount': amount,
            'billType': bill_type,
            'categoryId': category.category_id if category else None,
            'categoryName': category.category_name if category else None,
            'categoryIcon': category.icon if category else None,
            'accountId': account.account_id if account else (accounts[0].account_id if accounts else None),
            'accountName': account.account_name if account else (accounts[0].account_name if accounts else None),
            'billDate': bill_date.isoformat(),
            'remark': remark or text,
            'confidence': confidence,
            'rawText': text,
        }

    @classmethod
    def _extract_amount(cls, text: str) -> tuple[float | None, tuple[int, int] | None]:
        """
        提取金额，优先取带货币符号或单位的数字，否则取最大值

        :param text: 文本
        :return: (金额, 匹配位置)
        """
        candidates = []
        for match in cls.AMOUNT_PATTERN.finditer(text):
            value = float(match.group(1))
            if value <= 0:
                continue
            weighted = value
            # 带货币符号或「元/块」的权重更高
            raw = match.group(0)
            if any(symbol in raw for symbol in ('¥', '￥', '$', '元', '块')):
                weighted = value * 1000
            candidates.append((weighted, value, match.span()))
        if not candidates:
            return None, None
        candidates.sort(key=lambda item: item[0], reverse=True)

        return candidates[0][1], candidates[0][2]

    @classmethod
    def _extract_date(cls, text: str) -> date:
        """
        从文本中识别日期，默认今天

        :param text: 文本
        :return: 日期
        """
        today = date.today()
        for word, offset in cls.DATE_WORDS.items():
            if word in text:
                return today - timedelta(days=offset)
        full = cls.DATE_PATTERN.search(text)
        if full:
            try:
                return date(int(full.group(1)), int(full.group(2)), int(full.group(3)))
            except ValueError:
                pass
        month_day = cls.MONTH_DAY_PATTERN.search(text)
        if month_day:
            try:
                return date(today.year, int(month_day.group(1)), int(month_day.group(2)))
            except ValueError:
                pass

        return today

    @classmethod
    def _strip_date(cls, text: str) -> str:
        """
        移除文本中的日期片段，避免被当成金额

        :param text: 文本
        :return: 处理后的文本
        """
        for word in cls.DATE_WORDS:
            text = text.replace(word, ' ')
        text = cls.DATE_PATTERN.sub(' ', text)
        text = cls.MONTH_DAY_PATTERN.sub(' ', text)

        return text

    @classmethod
    def _match_category(cls, text: str, categories: list, bill_type: str) -> Any:
        """
        匹配分类：先精确命中分类名，再走别名词典

        :param text: 文本
        :param categories: 分类列表
        :param bill_type: 账单类型
        :return: 分类对象或 None
        """
        candidates = [item for item in categories if item.category_type == bill_type]
        for item in candidates:
            if item.category_name and item.category_name in text:
                return item
        for item in candidates:
            aliases = cls.CATEGORY_ALIAS.get(item.category_name or '', ())
            if any(alias in text for alias in aliases):
                return item

        return None

    @classmethod
    def _match_account(cls, text: str, accounts: list) -> Any:
        """
        匹配账户

        :param text: 文本
        :param accounts: 账户列表
        :return: 账户对象或 None
        """
        for account in accounts:
            if account.account_name and account.account_name in text:
                return account
            aliases = cls.ACCOUNT_ALIAS.get(account.account_name or '', ())
            if any(alias in text.lower() for alias in aliases):
                return account

        return None

    @classmethod
    def _clean_remark(cls, text: str, category: Any, account: Any) -> str:
        """
        清理备注：去掉已识别的分类名与账户名

        :param text: 文本
        :param category: 分类
        :param account: 账户
        :return: 备注
        """
        remark = text
        if category:
            remark = remark.replace(category.category_name or '', ' ')
            for alias in cls.CATEGORY_ALIAS.get(category.category_name or '', ()):
                remark = remark.replace(alias, ' ')
        if account:
            remark = remark.replace(account.account_name or '', ' ')
        for word in ('收入', '支出', '花了', '付了', '消费', '元', '块'):
            remark = remark.replace(word, ' ')
        remark = re.sub(r'\s+', ' ', remark).strip(' ，,。.')

        return remark[:60]

    @classmethod
    async def _parse_with_llm(cls, text: str, categories: list, accounts: list) -> dict[str, Any] | None:
        """
        可选的大模型解析，未配置密钥或调用失败时返回 None 由规则引擎兜底

        :param text: 用户输入
        :param categories: 分类列表
        :param accounts: 账户列表
        :return: 解析结果或 None
        """
        api_key = os.getenv('ACCOUNT_LLM_KEY', '').strip()
        if not api_key:
            return None
        base_url = os.getenv('ACCOUNT_LLM_BASE', 'https://api.openai.com/v1').rstrip('/')
        model = os.getenv('ACCOUNT_LLM_MODEL', 'gpt-4o-mini')
        category_names = [item.category_name for item in categories if item.category_type == '0']
        account_names = [item.account_name for item in accounts]
        prompt = (
            '你是记账助手。把用户的一句话解析成 JSON，只输出 JSON，不要解释。\n'
            f'可用分类：{category_names}\n可用账户：{account_names}\n'
            '字段：amount(数字)、billType("0"支出/"1"收入)、categoryName、accountName、'
            'billDate(YYYY-MM-DD)、remark(简短备注)。无法判断的字段留空字符串。\n'
            f'用户说：{text}'
        )
        try:
            import httpx

            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(
                    f'{base_url}/chat/completions',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={
                        'model': model,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0,
                    },
                )
                resp.raise_for_status()
                content = resp.json()['choices'][0]['message']['content']
            match = re.search(r'\{[\s\S]*\}', content)
            if not match:
                return None
            payload = json.loads(match.group(0))
            amount = float(payload.get('amount') or 0)
            if amount <= 0:
                return None
            category = next(
                (item for item in categories if item.category_name == payload.get('categoryName')), None
            )
            account = next((item for item in accounts if item.account_name == payload.get('accountName')), None)

            return {
                'amount': amount,
                'billType': '1' if str(payload.get('billType')) == '1' else '0',
                'categoryId': category.category_id if category else None,
                'categoryName': category.category_name if category else payload.get('categoryName') or None,
                'categoryIcon': category.icon if category else None,
                'accountId': account.account_id if account else (accounts[0].account_id if accounts else None),
                'accountName': account.account_name if account else (accounts[0].account_name if accounts else None),
                'billDate': payload.get('billDate') or date.today().isoformat(),
                'remark': (payload.get('remark') or text)[:60],
                'confidence': 'high',
                'rawText': text,
            }
        except Exception:
            return None
