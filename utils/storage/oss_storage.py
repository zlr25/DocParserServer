import os
from typing import Optional

import oss2

from .base import StorageBase
from utils.log_utils import setup_logger

logger = setup_logger(__name__, './logs/app.log')


class OSSStorage(StorageBase):
    """OSS SDK 实现的存储后端（支持私有云）"""

    def __init__(self, config: dict):
        self.endpoint = config.get('endpoint')
        self.access_key = config.get('access_key')
        self.secret_key = config.get('secret_key')
        self.bucket = config.get('bucket')

        logger.info(f"OSS endpoint: {self.endpoint}")
        logger.info(f"OSS bucket: {self.bucket}")

        # 创建 OSS 认证对象
        self.auth = oss2.Auth(self.access_key, self.secret_key)
        # 创建 Bucket 对象
        self.bucket_obj = oss2.Bucket(self.auth, self.endpoint, self.bucket)

    def upload_file(self, file_path: str, bucket_name: Optional[str] = None,
                    overwrite_file_name: Optional[str] = None) -> Optional[str]:
        """
        上传文件到 OSS

        Args:
            file_path: 本地文件路径
            bucket_name: 目标桶名称（可选，暂不支持切换桶）
            overwrite_file_name: 覆盖文件名（可选）

        Returns:
            str: 文件下载链接，失败返回 None
        """
        try:
            original_filename = os.path.basename(file_path)
            file_extension = os.path.splitext(original_filename)[1]
            if overwrite_file_name:
                object_name = overwrite_file_name + file_extension
            else:
                object_name = original_filename

            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"File '{file_path}' does not exist.")
                return None

            # 上传文件到 OSS
            with open(file_path, 'rb') as f:
                self.bucket_obj.put_object(object_name, f)

            logger.info(f"File '{object_name}' uploaded to OSS bucket '{self.bucket}'")

            # 获取下载链接
            download_url = self.get_download_url(object_name)
            logger.info(f"File uploaded successfully, download link: {download_url}")
            return download_url

        except oss2.exceptions.OssError as e:
            logger.error(f"OSS error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file to OSS: {e}")
            return None

    def get_download_url(self, object_name: str, bucket_name: Optional[str] = None,
                         expires: int = 3600 * 24 * 7) -> str:
        """
        获取文件下载链接（签名 URL，默认 7 天有效期）

        Args:
            object_name: 对象名称
            bucket_name: 桶名称（可选，暂不支持切换桶）
            expires: URL 有效期（秒），默认 7 天

        Returns:
            str: 下载链接
        """
        # 生成签名 URL
        signed_url = self.bucket_obj.sign_url('GET', object_name, expires)
        # 如果 endpoint 不包含协议前缀，添加 https
        if not signed_url.startswith('http'):
            signed_url = f"https://{signed_url}"
        return signed_url
