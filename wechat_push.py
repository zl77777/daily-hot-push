"""
公众号推送模块

支持:
  1. 订阅号 — 客服消息 (48h内互动用户) / 群发消息 (每天1次，全员)
  2. 服务号 — 模板消息
"""
import asyncio
import json
import time

import aiohttp

from config import Config


class WeChatPusher:
    """公众号消息推送"""

    # 微信 API 入口
    API_BASE = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self, config: Config):
        self.app_id = config.wechat_app_id
        self.app_secret = config.wechat_app_secret
        self.mode = config.wechat_push_mode
        self._access_token: str = ""
        self._token_expires: float = 0

    # -------------------------------------------------------
    # Access Token 管理（自动缓存 + 续期）
    # -------------------------------------------------------
    async def _get_token(self) -> str:
        """获取 access_token，带缓存"""
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

    # -------------------------------------------------------
    # 群发消息（订阅号：每天1次，全员接收）
    # -------------------------------------------------------
    async def push_mass_text(self, content: str) -> bool:
        """
        订阅号群发文字消息

        注意：
          - 订阅号每天只能群发 1 次
          - 文字消息上限约 2048 字节
          - 必须是认证订阅号
        """
        token = await self._get_token()

        body = {
            "filter": {
                "is_to_all": True,
            },
            "text": {
                "content": content,
            },
            "msgtype": "text",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/message/mass/sendall?access_token={token}",
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()

        errcode = data.get("errcode", -1)
        if errcode == 0:
            msg_id = data.get("msg_id", "")
            print(f"  [微信] 群发成功 msg_id={msg_id}")
            return True

        errmsg = data.get("errmsg", "")
        print(f"  [微信] 群发失败: [{errcode}] {errmsg}")
        return False

    # -------------------------------------------------------
    # 客服消息（48h内有互动的用户）
    # -------------------------------------------------------
    async def push_customer_message(self, content: str, openid: str) -> bool:
        """向指定用户发送客服消息（48h 限制）"""
        token = await self._get_token()

        body = {
            "touser": openid,
            "msgtype": "text",
            "text": {"content": content},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/message/custom/send?access_token={token}",
                json=body,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()

        return data.get("errcode") == 0

    async def push_customer_broadcast(self, content: str) -> int:
        """群发客服消息给所有符合48h条件的用户"""
        openids = await self._get_active_users()
        if not openids:
            print("  [微信] 没有 48h 内活跃的用户")
            return 0

        # 并发发送（微信限制约 600次/分钟，控制并发数）
        sem = asyncio.Semaphore(50)
        async def send_one(oid: str):
            async with sem:
                await asyncio.sleep(0.1)  # 限速
                ok = await self.push_customer_message(content, oid)
                return ok

        results = await asyncio.gather(*[send_one(oid) for oid in openids])
        success = sum(1 for r in results if r)
        print(f"  [微信] 客服消息发送 {success}/{len(openids)}")
        return success

    # -------------------------------------------------------
    # 模板消息（服务号）
    # -------------------------------------------------------
    async def push_template(self, openid: str, template_id: str, data: dict, jump_url: str = "") -> bool:
        """服务号模板消息推送"""
        token = await self._get_token()

        body = {
            "touser": openid,
            "template_id": template_id,
            "data": data,
        }
        if jump_url:
            body["url"] = jump_url

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/message/template/send?access_token={token}",
                json=body,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()

        return data.get("errcode") == 0

    # -------------------------------------------------------
    # 核心入口：根据配置自动选择推送方式
    # -------------------------------------------------------
    async def push(self, content: str, brief: str = "") -> dict:
        """
        根据 WECHAT_PUSH_MODE 自动分发

        mass:     订阅号群发（每天1次全员）
        template: 服务号模板消息（需 openid）
        """
        if not self.app_id or not self.app_secret:
            print("  [微信] ⚠️  未配置公众号密钥，跳过推送")
            print("  [微信] 推送内容预览：")
            print("-" * 50)
            print(content[:800])
            print("-" * 50)
            return {"status": "skipped", "reason": "not configured"}

        try:
            if self.mode == "mass":
                ok = await self.push_mass_text(content)
                return {"status": "success" if ok else "failed", "mode": "mass"}

            elif self.mode == "template":
                # 模板消息需要 openid 列表，从 _get_active_users 获取
                openids = await self._get_active_users()
                if not openids:
                    return {"status": "skipped", "reason": "no active users"}

                from formatter import format_template_message
                tmpl_data = format_template_message(content, brief)

                results = []
                for oid in openids[:100]:  # 一次最多100个
                    ok = await self.push_template(oid, "YOUR_TEMPLATE_ID", tmpl_data)
                    results.append(ok)
                success = sum(1 for r in results if r)
                return {"status": "success", "mode": "template", "count": f"{success}/{len(results)}"}

            else:
                return {"status": "skipped", "reason": f"unknown mode: {self.mode}"}

        except RuntimeError as e:
            print(f"  [微信] 推送异常: {e}")
            return {"status": "failed", "reason": str(e)}

    # -------------------------------------------------------
    # 获取活跃用户列表
    # -------------------------------------------------------
    async def _get_active_users(self) -> list[str]:
        """获取关注者 openid 列表"""
        token = await self._get_token()
        openids: list[str] = []
        next_openid = ""

        async with aiohttp.ClientSession() as session:
            while True:
                params = {"access_token": token}
                if next_openid:
                    params["next_openid"] = next_openid

                async with session.get(
                    f"{self.API_BASE}/user/get",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()

                if "data" not in data:
                    break

                openids.extend(data["data"].get("openid", []))
                next_openid = data.get("next_openid", "")
                if not next_openid:
                    break

        return openids
