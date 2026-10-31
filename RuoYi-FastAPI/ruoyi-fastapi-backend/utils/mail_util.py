import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from config.env import AppConfig, MailConfig
from exceptions.exception import ServiceException
from utils.log_util import logger


class MailUtil:
    """
    邮件发送工具类

    仅依赖标准库 smtplib，默认使用 SSL 直连（腾讯企业邮箱 465 端口）。
    发送方法为同步阻塞调用，业务侧需通过 asyncio.to_thread 交给线程池执行，
    避免占用事件循环。
    """

    @classmethod
    def is_enabled(cls) -> bool:
        """
        判断邮件发送能力是否可用

        :return: 配置齐全且开关打开时为 True
        """
        return bool(MailConfig.mail_enabled and MailConfig.mail_host and MailConfig.mail_user)

    @classmethod
    def send_html(
        cls,
        receiver: str,
        subject: str,
        html: str,
        plain_text: str | None = None,
    ) -> None:
        """
        发送 HTML 邮件

        :param receiver: 收件人邮箱
        :param subject: 邮件主题
        :param html: HTML 正文
        :param plain_text: 纯文本兜底正文，为空时由 HTML 简单降级
        :return: None
        :raises ServiceException: 配置缺失或投递失败
        """
        if not cls.is_enabled():
            raise ServiceException(message='邮件服务未开启')

        message = EmailMessage()
        message['From'] = formataddr((MailConfig.mail_from_name, MailConfig.mail_sender))
        message['To'] = receiver
        message['Subject'] = subject
        message['Date'] = formatdate(localtime=True)
        message['Message-ID'] = make_msgid()
        message.set_content(plain_text or '请使用支持 HTML 的邮件客户端查看本邮件', subtype='plain', charset='utf-8')
        message.add_alternative(html, subtype='html', charset='utf-8')

        port = MailConfig.mail_port or (465 if MailConfig.mail_ssl else 587)
        try:
            if MailConfig.mail_ssl:
                server = smtplib.SMTP_SSL(
                    MailConfig.mail_host,
                    port,
                    timeout=MailConfig.mail_timeout,
                    context=ssl.create_default_context(),
                )
            else:
                server = smtplib.SMTP(MailConfig.mail_host, port, timeout=MailConfig.mail_timeout)
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            try:
                server.login(MailConfig.mail_user, MailConfig.mail_password)
                server.send_message(message, from_addr=MailConfig.mail_sender, to_addrs=[receiver])
            finally:
                try:
                    server.quit()
                except smtplib.SMTPException:
                    pass
        except (OSError, smtplib.SMTPException) as exc:
            logger.error(f'发送邮件到{receiver}失败：{exc}')
            raise ServiceException(message='验证码邮件发送失败，请稍后重试') from exc

        logger.info(f'验证码邮件已发送至{receiver}')

    @classmethod
    def send_email_code(cls, receiver: str, code: str, scene: str = 'register') -> None:
        """
        发送邮箱验证码邮件

        :param receiver: 收件人邮箱
        :param code: 验证码
        :param scene: 业务场景，register 注册，reset 重置密码
        :return: None
        """
        title = '注册验证码' if scene == 'register' else '身份验证码'
        action = '注册账号' if scene == 'register' else '重置密码'
        ttl = MailConfig.mail_code_ttl_minutes
        html = f"""\
<div style="margin:0;padding:32px 0;background:#f5f7fa;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="width:520px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 28px rgba(31,36,48,0.08);">
    <div style="padding:28px 32px;background:linear-gradient(140deg,#1aa86c 0%,#35c98c 100%);color:#ffffff;">
      <div style="font-size:20px;font-weight:600;letter-spacing:1px;">{AppConfig.app_name}</div>
      <div style="margin-top:6px;font-size:13px;opacity:0.86;">{action}验证码</div>
    </div>
    <div style="padding:32px;">
      <div style="font-size:15px;color:#1f2430;line-height:26px;">你正在{action}，本次验证码为：</div>
      <div style="margin:20px 0;padding:18px 0;text-align:center;background:#f2fbf7;border:1px dashed #b7e6d1;border-radius:12px;font-size:34px;font-weight:700;letter-spacing:10px;color:#1aa86c;">{code}</div>
      <div style="font-size:13px;color:#8a8f9c;line-height:24px;">验证码 {ttl} 分钟内有效，请勿转发给他人。</div>
      <div style="font-size:13px;color:#8a8f9c;line-height:24px;">若非本人操作，请忽略本邮件。</div>
    </div>
    <div style="padding:18px 32px;border-top:1px solid #eef0f3;font-size:12px;color:#b6bac4;text-align:center;">本邮件由系统自动发送，请勿直接回复</div>
  </div>
</div>"""
        plain = f'你正在{action}，验证码：{code}，{ttl} 分钟内有效。若非本人操作请忽略本邮件。'
        cls.send_html(receiver, f'【{AppConfig.app_name}】{title}：{code}', html, plain)
