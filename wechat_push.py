"""
公众号推送模块 —— 图文文章发布

流程: AI 生成内容 → HTML 排版 → 上传封面图 → 创建草稿 → 发布文章
"""
import asyncio
import json
import time
import base64
import struct
import zlib

import aiohttp

from config import Config


class WeChatPusher:
    """公众号图文文章发布"""

    API_BASE = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self, config: Config):
        self.app_id = config.wechat_app_id
        self.app_secret = config.wechat_app_secret
        self.mode = config.wechat_push_mode
        self._access_token: str = ""
        self._token_expires: float = 0

    # ============================================================
    # Access Token
    # ============================================================
    async def _get_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires - 300:
            return self._access_token

        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.API_BASE}/token",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()

        token = data.get("access_token", "")
        if not token:
            errcode = data.get("errcode", "")
            errmsg = data.get("errmsg", "")
            raise RuntimeError(f"获取 access_token 失败: [{errcode}] {errmsg}")

        self._access_token = token
        self._token_expires = now + data.get("expires_in", 7200)
        return token

    # ============================================================
    # 主入口：创建草稿 + 发布文章
    # ============================================================
    async def publish_article(
        self,
        title: str,
        content_html: str,
        digest: str = "",
        author: str = "AI 热点速递",
    ) -> dict:
        """
        创建草稿并发布文章

        返回: {"status": "published"|"draft_only"|"failed", "msg": "..."}
        """
        if not self.app_id or not self.app_secret:
            print("  [微信] [WARN] 未配置公众号密钥，仅预览")
            return {"status": "skipped", "reason": "not configured"}

        try:
            # 1. 上传封面图
            print("  [微信] 上传封面图...")
            thumb_media_id = await self._upload_cover_image()

            # 2. 创建草稿
            print("  [微信] 创建草稿...")
            draft_media_id = await self._create_draft(
                title=title,
                content=content_html,
                thumb_media_id=thumb_media_id,
                digest=digest,
                author=author,
            )
            if not draft_media_id:
                return {"status": "failed", "reason": "创建草稿失败"}

            print(f"  [微信] 草稿创建成功 media_id={draft_media_id}")

            # 3. 发布文章
            print("  [微信] 发布文章...")
            pub_result = await self._publish_draft(draft_media_id)

            if pub_result.get("success"):
                print("  [微信] 文章发布成功!")
                return {"status": "published", "media_id": draft_media_id}

            # 发布失败，草稿已保存
            print(f"  [微信] 发布失败，但草稿已保存: {pub_result.get('reason', '')}")
            return {"status": "draft_only", "media_id": draft_media_id, "msg": "草稿已保存，请手动发布"}

        except RuntimeError as e:
            print(f"  [微信] 异常: {e}")
            return {"status": "failed", "reason": str(e)}

    # ============================================================
    # 上传封面图（生成纯色 PNG，包含日期）
    # ============================================================
    async def _upload_cover_image(self) -> str:
        """生成封面图并上传到微信素材库，返回 media_id"""
        from datetime import datetime

        # 生成一张 900x500 的纯色 PNG 封面图
        png_bytes = self._make_cover_png(
            width=900,
            height=500,
            text=datetime.now().strftime("%Y.%m.%d"),
        )

        token = await self._get_token()
        url = f"{self.API_BASE}/material/add_material?access_token={token}&type=image"

        data = aiohttp.FormData()
        data.add_field(
            "media",
            png_bytes,
            filename="cover.png",
            content_type="image/png",
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                result = await resp.json()

        media_id = result.get("media_id", "")
        if not media_id:
            errcode = result.get("errcode", "")
            errmsg = result.get("errmsg", "")
            print(f"  [微信] 封面上传失败: [{errcode}] {errmsg}")
            # 返回空串，后续创建草稿时尝试不用封面
            return ""
        return media_id

    @staticmethod
    def _make_cover_png(width: int, height: int, text: str) -> bytes:
        """用纯 Python 生成一张简单的 PNG 图片（蓝色渐变 + 日期文字）"""
        def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk = chunk_type + data
            return (
                struct.pack(">I", len(data))
                + chunk
                + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
            )

        # IHDR
        ihdr_data = struct.pack(
            ">IIBBBBB", width, height, 8, 2, 0, 0, 0  # bit depth  # color type RGB
        )
        ihdr = make_chunk(b"IHDR", ihdr_data)

        # IDAT: raw RGB pixels, no filter, zlib compressed
        raw = b""
        for y in range(height):
            raw += b"\x00"  # filter: none
            for x in range(width):
                r = int(30 + (y / height) * 40)
                g = int(60 + (y / height) * 80)
                b = int(120 + (y / height) * 80)
                raw += struct.pack("BBB", r, g, b)

        compressed = zlib.compress(raw)
        idat = make_chunk(b"IDAT", compressed)

        # IEND
        iend = make_chunk(b"IEND", b"")

        # PNG signature
        signature = b"\x89PNG\r\n\x1a\n"
        return signature + ihdr + idat + iend

    # ============================================================
    # 创建草稿
    # ============================================================
    async def _create_draft(
        self,
        title: str,
        content: str,
        thumb_media_id: str = "",
        digest: str = "",
        author: str = "AI 热点速递",
    ) -> str:
        """创建图文草稿，返回 draft_media_id"""
        token = await self._get_token()

        article = {
            "title": title,
            "content": content,
            "author": author,
            "digest": digest,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        if thumb_media_id:
            article["thumb_media_id"] = thumb_media_id

        body = {"articles": [article]}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/draft/add?access_token={token}",
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()

        media_id = data.get("media_id", "")
        if not media_id:
            errcode = data.get("errcode", "")
            errmsg = data.get("errmsg", "")
            print(f"  [微信] 创建草稿失败: [{errcode}] {errmsg}")
            return ""
        return media_id

    # ============================================================
    # 发布草稿
    # ============================================================
    async def _publish_draft(self, media_id: str) -> dict:
        """发布草稿"""
        token = await self._get_token()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/freepublish/submit?access_token={token}",
                json={"media_id": media_id},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()

        errcode = data.get("errcode", -1)
        if errcode == 0:
            return {"success": True, "publish_id": data.get("publish_id", "")}

        errmsg = data.get("errmsg", "")
        print(f"  [微信] 发布失败: [{errcode}] {errmsg}")

        # 如果是权限问题，提示用户手动发布
        if errcode == 48001:
            return {"success": False, "reason": "无发布权限，请在公众号后台手动发布草稿"}
        return {"success": False, "reason": f"[{errcode}] {errmsg}"}

    # ============================================================
    # 兼容旧接口
    # ============================================================
    async def push(self, content: str, brief: str = "") -> dict:
        """兼容旧调用——默认走文章发布流程"""
        from datetime import datetime

        title = f"全球热点速递 | {datetime.now().strftime('%Y年%m月%d日')}"
        digest = brief[:120] if brief else "今日全球热点一文速览"

        return await self.publish_article(
            title=title,
            content_html=content,
            digest=digest,
        )
