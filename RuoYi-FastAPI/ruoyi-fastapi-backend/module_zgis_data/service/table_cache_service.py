from utils.log_util import logger


class TableCacheService:
    """
    zgis 配置表缓存服务占位实现

    说明：原实现依赖业务侧私有模块，当前仓库未提供，此处仅保留可启动的占位逻辑，
    后续补齐真实实现时直接替换本文件即可。
    """

    @classmethod
    async def load_all_tables_to_cache(cls, session, redis) -> None:
        """
        加载 zgis 配置表到缓存（占位）

        :param session: 数据库会话
        :param redis: redis对象
        :return: None
        """
        logger.info('⏭️ 跳过 zgis 表缓存加载（module_zgis_data 占位实现）')
