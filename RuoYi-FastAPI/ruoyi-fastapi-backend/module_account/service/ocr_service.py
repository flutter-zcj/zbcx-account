import os
import re
import subprocess
import tempfile
from datetime import date
from typing import Any

from exceptions.exception import ServiceException


class AccountOcrService:
    """
    图片识别记账服务

    使用服务器本地 tesseract 做 OCR（chi_sim + eng），从支付截图/小票中
    提取金额、商户、日期，返回可预填的账单草稿。

    未安装 tesseract 时明确返回不可用，前端降级为手动填金额。
    """

    TESSERACT = '/usr/bin/tesseract'
    LANG = 'chi_sim+eng'
    AMOUNT_KEYWORDS = ('合计', '总计', '实付', '应付', '支付金额', '付款金额', '金额', '付款')
    MERCHANT_KEYWORDS = ('商户名称', '商户', '收款方', '商家', '店铺')
    # 日期中的数字不能当作金额
    DATE_STRIP_PATTERN = re.compile(r'\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}日?|\d{1,2}:\d{2}(?::\d{2})?')
    AMOUNT_PATTERN = re.compile(r'(?:[¥￥]\s*)?(-?\d{1,7}(?:\.\d{1,2})?)')
    DATE_PATTERN = re.compile(r'(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})')

    @classmethod
    def is_available(cls) -> bool:
        """
        检查 OCR 是否可用

        :return: 是否可用
        """
        return os.path.exists(cls.TESSERACT)

    @classmethod
    async def recognize_services(cls, content: bytes, suffix: str) -> dict[str, Any]:
        """
        识别图片中的账单信息

        :param content: 图片二进制
        :param suffix: 文件后缀
        :return: 识别结果
        """
        if not cls.is_available():
            raise ServiceException(message='服务器未安装 OCR 组件，请手动填写金额')
        text = cls._run_ocr(content, suffix)
        if not text.strip():
            raise ServiceException(message='没识别出文字，换张清晰点的截图试试')

        amount = cls._extract_amount(text)
        merchant = cls._extract_merchant(text)
        bill_date = cls._extract_date(text)

        return {
            'amount': amount,
            'merchant': merchant,
            'billDate': bill_date,
            'text': text[:500],
            'confidence': 'high' if amount else 'low',
        }

    @classmethod
    def _run_ocr(cls, content: bytes, suffix: str) -> str:
        """
        调用 tesseract 识别文字

        :param content: 图片二进制
        :param suffix: 文件后缀
        :return: 识别文本
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or '.png') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            result = subprocess.run(
                [cls.TESSERACT, tmp_path, 'stdout', '-l', cls.LANG, '--psm', '6'],
                capture_output=True,
                timeout=25,
            )
            return result.stdout.decode('utf-8', 'ignore')
        except subprocess.TimeoutExpired:
            raise ServiceException(message='图片识别超时，请重试')
        except Exception:
            return ''
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    @classmethod
    def _extract_amount(cls, text: str) -> float | None:
        """
        提取金额：优先关键词所在行，其次带货币符号，最后取最大值

        :param text: OCR 文本
        :return: 金额
        """
        lines = [cls.DATE_STRIP_PATTERN.sub(' ', line.strip()) for line in text.splitlines() if line.strip()]
        candidates: list[tuple[int, float]] = []

        for index, line in enumerate(lines):
            if not any(keyword in line for keyword in cls.AMOUNT_KEYWORDS):
                continue
            for match in cls.AMOUNT_PATTERN.finditer(line):
                value = abs(float(match.group(1)))
                if 0 < value < 100000:
                    candidates.append((3, value))
            # 关键词行没数字时看下一行
            if index + 1 < len(lines) and not candidates:
                for match in cls.AMOUNT_PATTERN.finditer(lines[index + 1]):
                    value = abs(float(match.group(1)))
                    if 0 < value < 100000:
                        candidates.append((2, value))

        for line in lines:
            for match in cls.AMOUNT_PATTERN.finditer(line):
                raw = match.group(0)
                value = abs(float(match.group(1)))
                if ('¥' in raw or '￥' in raw) and 0 < value < 100000:
                    candidates.append((2, value))

        if not candidates:
            for match in cls.AMOUNT_PATTERN.finditer(cls.DATE_STRIP_PATTERN.sub(' ', text)):
                value = abs(float(match.group(1)))
                if 0 < value < 100000:
                    candidates.append((1, value))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

        return round(candidates[0][1], 2)

    @classmethod
    def _extract_merchant(cls, text: str) -> str | None:
        """
        提取商户名称

        :param text: OCR 文本
        :return: 商户名
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if any(keyword in line for keyword in cls.MERCHANT_KEYWORDS):
                # 「商户名称：星巴克」优先用右侧内容，去掉误识别的分隔符
                parts = re.split(r'[：:]', line, maxsplit=1)
                cleaned = parts[1] if len(parts) > 1 else line
                for keyword in cls.MERCHANT_KEYWORDS:
                    cleaned = cleaned.replace(keyword, '')
                cleaned = re.sub(r'^[\s名称商户二]+', '', cleaned).strip()
                if cleaned:
                    return cleaned[:20]
        # 退化：取第一行中文较多的文本
        for line in lines[:5]:
            if len(re.findall(r'[\u4e00-\u9fa5]', line)) >= 2 and not cls.AMOUNT_PATTERN.search(line):
                return line[:20]

        return None

    @classmethod
    def _extract_date(cls, text: str) -> str:
        """
        提取日期，默认今天

        :param text: OCR 文本
        :return: YYYY-MM-DD
        """
        match = cls.DATE_PATTERN.search(text)
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
            except ValueError:
                pass

        return date.today().isoformat()
