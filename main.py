"""
AstrBot 崩坏：星穹铁道金句插件 v1.2.0

功能描述：
- 随机输出《崩坏：星穹铁道》角色经典台词/金句
- 支持用户自定义添加、删除、列表查看金句
- 支持防刷屏机制（用户冷却、群聊日限）
- 支持统计分析

作者: HamLJYH
版本: 1.2.0
日期: 2026-06-26
"""

# 标准库
import asyncio
import functools
import json
import os
import random
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

# 第三方库
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

# =============================================================================
# 常量定义
# =============================================================================

MAX_QUOTE_LENGTH = 500
MAX_CHARACTER_LENGTH = 50
MAX_SOURCE_LENGTH = 50
MAX_KEYWORD_LENGTH = 100

DEFAULT_QUOTES_PER_PAGE = 10
DEFAULT_USER_COOLDOWN_SECONDS = 10
DEFAULT_GROUP_DAILY_LIMIT = 50

CUSTOM_QUOTES_FILENAME = "custom_quotes.json"

# =============================================================================
# 工具函数
# =============================================================================

def handle_errors(func):
    """统一错误处理装饰器

    捕获并处理函数执行过程中的各种异常，向用户返回友好的错误提示。
    """
    @functools.wraps(func)
    async def wrapper(
        self,
        event: AstrMessageEvent,
        *args: Any,
        **kwargs: Any
    ) -> AsyncGenerator[Any, None]:
        try:
            async for result in func(self, event, *args, **kwargs):
                yield result
        except PermissionError as e:
            logger.error(f"[{func.__name__}] 权限不足: {e}", exc_info=True)
            yield event.plain_result("❌ 权限不足，请检查文件权限")
        except (IOError, OSError) as e:
            logger.error(f"[{func.__name__}] 文件操作失败: {e}", exc_info=True)
            yield event.plain_result("❌ 文件操作失败，请检查文件是否存在")
        except asyncio.TimeoutError as e:
            logger.error(f"[{func.__name__}] 操作超时: {e}", exc_info=True)
            yield event.plain_result("❌ 操作超时，请稍后重试")
        except ValueError as e:
            logger.warning(f"[{func.__name__}] 参数错误: {e}")
            yield event.plain_result(f"❌ 参数错误: {str(e)}")
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"[{func.__name__}] 执行失败 [{error_type}]: {e}",
                exc_info=True
            )
            yield event.plain_result("❌ 操作失败，请联系管理员")

    return wrapper

# =============================================================================
# 插件主类
# =============================================================================

@register(
    "astrbot_plugin_stellaron",
    "HamLJYH",
    "崩坏：星穹铁道金句插件",
    "1.2.0",
    "https://github.com/HamLJYH/astrbot_plugin_stellaron"
)
class StellaronPlugin(Star):
    """崩坏：星穹铁道金句插件主类"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)

        # 读取配置（AstrBotConfig 继承自 Dict）
        self.config = config

        # 总开关
        self.anti_spam_enabled: bool = self.config.get("anti_spam_enabled", True)

        # 用户冷却配置
        self.user_cooldown_enabled: bool = self.config.get(
            "user_cooldown_enabled", True
        )
        self.user_cooldown_seconds: int = self.config.get(
            "user_cooldown_seconds", DEFAULT_USER_COOLDOWN_SECONDS
        )

        # 群聊日限配置
        self.group_daily_limit_enabled: bool = self.config.get(
            "group_daily_limit_enabled", True
        )
        self.group_daily_limit: int = self.config.get(
            "group_daily_limit", DEFAULT_GROUP_DAILY_LIMIT
        )

        # 用户冷却记录：{user_id: last_trigger_timestamp}
        # 只保留最近 user_cooldown_seconds 内的记录，超时自动清理
        self.user_cooldown: Dict[str, float] = {}
        self._cooldown_lock = asyncio.Lock()

        # 群聊每日触发记录：{group_id: {"count": int, "date": str}}
        # 只保留当天的记录，跨天自动清理
        self.group_daily_count: Dict[str, Dict[str, Any]] = {}
        self._group_lock = asyncio.Lock()

        # 默认金句库
        self.default_quotes: List[Dict[str, str]] = self._load_default_quotes()

        # 用户自定义金句文件路径
        self.custom_quotes_file: str = os.path.join(
            os.path.dirname(__file__), CUSTOM_QUOTES_FILENAME
        )
        self.custom_quotes: List[Dict[str, str]] = self._load_custom_quotes()

        # 合并默认和用户自定义
        self.all_quotes: List[Dict[str, str]] = (
            self.default_quotes + self.custom_quotes
        )

        logger.info(
            f"崩铁金句插件加载完成，共 {len(self.all_quotes)} 条金句"
            f"（默认 {len(self.default_quotes)} 条，自定义 {len(self.custom_quotes)} 条）"
        )

        # 注册 Web API（供插件 Pages 使用）
        self._register_web_apis()

    def _load_default_quotes(self) -> List[Dict[str, str]]:
        """加载内置默认金句"""
        return [
            {"content": "煌煌威灵，尊吾敕命，斩无赦！", "character": "景元", "source": "角色语音"},
            {"content": "人们会为一子妙手力挽狂澜而喜，却不为大局危倾而忧。", "character": "景元", "source": "剧情台词"},
            {"content": "就让这一轮月华，照彻万川！", "character": "镜流", "source": "角色语音"},
            {"content": "死亡何时而至？我等得有些心焦了。", "character": "刃", "source": "角色语音"},
            {"content": "此番美景，我虽求而不得，却能邀诸位共赏。", "character": "刃", "source": "角色语音"},
            {"content": "庸人会以自己的方式，创造持有率最高的角色。", "character": "真理医生", "source": "角色语音"},
            {"content": "知识应当流通与分享，真理亦是如此。", "character": "真理医生", "source": "角色语音"},
            {"content": "我来押注，我来博弈，我来赢取。我任命运拨转轮盘，孤注一掷，遍历死地而后生。一切献给——琥珀王。", "character": "砂金", "source": "角色故事"},
            {"content": "强牌慢打，故作姿态，你让我有些心急了。", "character": "砂金", "source": "剧情台词"},
            {"content": "我将，点燃星海！", "character": "流萤", "source": "角色语音"},
            {"content": "我的过去或许不在从前，而是在我的未来里，所以我一定会一站站走下去，哪怕有一天没有列车。", "character": "三月七", "source": "剧情台词"},
            {"content": "所以列车并没有终点，旅程所谓的终点，只有你能决定。", "character": "姬子", "source": "剧情台词"},
            {"content": "每天和大家生活在一起，似乎任何人都不会发生改变，只有离开很久的人，才会产生某种惊人的变化。", "character": "姬子", "source": "剧情台词"},
            {"content": "这片银河容得下任何的可能性，而人的命运，也不应当只有上天给予的那一条道路。", "character": "瓦尔特", "source": "剧情台词"},
            {"content": "筑城者为我们砌成堡垒，使我们远离风雪，但我们必须铭记，风雪从未消失。", "character": "布洛妮娅", "source": "剧情台词"},
            {"content": "工作不算争取价值，是劳动换取酬劳，工作的时候偷闲才是为自己争取价值。", "character": "青雀", "source": "剧情台词"},
            {"content": "大人们总是用长大以后就明白的道理来糊弄虎克，虎克反倒觉得大人们有很多长大以后就忘记了的道理。", "character": "虎克", "source": "剧情台词"},
            {"content": "人不能总是单独面对问题，把挣扎永远藏在心里，要学会依靠他人，至少是亲近的人。", "character": "杰帕德", "source": "剧情台词"},
            {"content": "人是向往自由的动物，如果太久看不到天空，也是会生病的。", "character": "娜塔莎", "source": "剧情台词"},
            {"content": "史瓦罗常把人类喜欢无休止的争斗挂在嘴上，但如果只靠退让，难道就能获得和平？", "character": "希儿", "source": "剧情台词"},
            {"content": "万一被卷入了麻烦事，自己的真心如何并不重要，重要的是，如何找到适合自己扮演的角色。", "character": "罗刹", "source": "剧情台词"},
            {"content": "帮帮我，史瓦罗先生！", "character": "克拉拉", "source": "角色语音"},
            {"content": "愿母神三度为你阖眼，令你的血脉永远鼓动，旅途永远坦然，诡计永不败露。", "character": "砂金", "source": "剧情台词"},
            {"content": "是你在偷看我吗？", "character": "黄泉", "source": "角色语音"},
            {"content": "是时候说再见了。", "character": "黄泉", "source": "角色语音"},
            {"content": "邀诸位共赏。", "character": "刃", "source": "角色语音"},
            {"content": "愿，此行，终抵群星！", "character": "星期日", "source": "剧情台词"},
            {"content": "我将，寻征追猎！", "character": "飞霄", "source": "角色语音"},
            {"content": "星穹列车正在向外…奔跑…可恶的星穹列车！不许发车！", "character": "斯科特", "source": "剧情台词"},
            {"content": "我来抵押，我来典当，我来清算。我令价值流通不息，以物易物，权衡利弊而后行。一切献给——琥珀王。", "character": "翡翠", "source": "角色语音"},
            {"content": "我来评估，我来核算，我来追偿。我令账目分毫不差，锱铢必较，追索债务于星海。一切献给——琥珀王。", "character": "托帕", "source": "角色语音"},
            {"content": "生命如星尘般渺小，却也能绽放出超越星辰的光芒。", "character": "阮梅", "source": "剧情台词"},
            {"content": "尾巴大爷，帮帮我！", "character": "藿藿", "source": "角色语音"},
            {"content": "判官的笔，落下便是定数。", "character": "寒鸦", "source": "角色语音"},
            {"content": "人死如灯灭，但执念不灭。", "character": "雪衣", "source": "角色语音"},
            {"content": "面具之下，谁才是真正的自己？", "character": "花火", "source": "剧情台词"},
            {"content": "记忆是灵魂的回响，是过去对未来的低语。", "character": "黑天鹅", "source": "剧情台词"},
            {"content": "虚无并非空无一物，而是万物的终点。", "character": "黄泉", "source": "剧情台词"},
            {"content": "秩序并非枷锁，而是让万物各安其位的法则。", "character": "星期日", "source": "剧情台词"},
            {"content": "歌声是心灵的桥梁，即使相隔星海，也能传递温暖。", "character": "知更鸟", "source": "剧情台词"},
            {"content": "他宝了个贝的，这票干完我就收手！", "character": "波提欧", "source": "角色语音"},
            {"content": "忍法·奥义·乱破！", "character": "乱破", "source": "角色语音"},
            {"content": "往事如烟，唯有前行才是归途。", "character": "忘归人", "source": "剧情台词"},
            {"content": "知识的尽头，是更广阔的未知。", "character": "那刻夏", "source": "剧情台词"},
            {"content": "死亡不是终点，遗忘才是。", "character": "遐蝶", "source": "剧情台词"},
            {"content": "万敌当前，我亦不退。", "character": "万敌", "source": "角色语音"},
            {"content": "英雄之旅，从不因终点而止步。", "character": "白厄", "source": "剧情台词"},
            {"content": "金线织就命运，而我，是执针之人。", "character": "阿格莱雅", "source": "角色语音"},
            {"content": "小小的身体，也能承载大大的梦想。", "character": "缇宝", "source": "剧情台词"},
            {"content": "风会指引方向，也会带走一切。", "character": "赛飞儿", "source": "剧情台词"},
            {"content": "风过无痕，但留下了自由的气息。", "character": "风堇", "source": "剧情台词"},
            {"content": "可是，当真如此吗？", "character": "来古士", "source": "剧情台词"},
            {"content": "天才的头脑，不是用来理解庸人的。", "character": "大黑塔", "source": "角色语音"},
        ]

    def _get_today_str(self) -> str:
        """获取今天的日期字符串"""
        return time.strftime("%Y-%m-%d", time.localtime())

    async def _clean_expired_records(self) -> None:
        """清理过期记录，防止内存泄漏

        - 用户冷却记录：只保留未超时的（当前时间 - 记录时间 < user_cooldown_seconds）
        - 群聊日限记录：只保留当天的
        """
        current_time = time.time()
        expire_time = current_time - self.user_cooldown_seconds
        today = self._get_today_str()

        async with self._cooldown_lock:
            expired_users = [
                uid for uid, t in self.user_cooldown.items()
                if t < expire_time
            ]
            for uid in expired_users:
                del self.user_cooldown[uid]

        async with self._group_lock:
            expired_groups = [
                gid for gid, data in self.group_daily_count.items()
                if data.get("date") != today
            ]
            for gid in expired_groups:
                del self.group_daily_count[gid]

    async def _check_user_cooldown(self, user_id: str) -> Tuple[bool, str]:
        """检查用户冷却机制

        Args:
            user_id: 用户ID

        Returns:
            (bool, str): (是否允许触发, 提示信息)
        """
        if not self.anti_spam_enabled or not self.user_cooldown_enabled:
            return True, ""

        await self._clean_expired_records()
        current_time = time.time()

        async with self._cooldown_lock:
            last_time = self.user_cooldown.get(user_id, 0)
            if current_time - last_time < self.user_cooldown_seconds:
                remaining = int(
                    self.user_cooldown_seconds - (current_time - last_time)
                )
                return False, f"触发太快了啦！请 {remaining} 秒后再试~"

            self.user_cooldown[user_id] = current_time
            return True, ""

    async def _check_group_limit(self, group_id: str) -> Tuple[bool, str]:
        """检查群聊每日触发上限

        Args:
            group_id: 群聊ID

        Returns:
            (bool, str): (是否允许触发, 提示信息)
        """
        if not self.anti_spam_enabled or not self.group_daily_limit_enabled:
            return True, ""

        await self._clean_expired_records()
        today = self._get_today_str()

        async with self._group_lock:
            if group_id not in self.group_daily_count:
                self.group_daily_count[group_id] = {"count": 0, "date": today}

            group_data = self.group_daily_count[group_id]

            # 如果日期不是今天，重置计数
            if group_data.get("date") != today:
                group_data = {"count": 0, "date": today}
                self.group_daily_count[group_id] = group_data

            if group_data["count"] >= self.group_daily_limit:
                return False, (
                    f"本群今天的金句次数已经用完啦！明天再来吧~"
                    f"（上限: {self.group_daily_limit}次/天）"
                )

            group_data["count"] += 1
            return True, ""

    def _load_custom_quotes(self) -> List[Dict[str, str]]:
        """加载用户自定义金句

        Returns:
            自定义金句列表
        """
        if not os.path.exists(self.custom_quotes_file):
            return []

        try:
            with open(self.custom_quotes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            logger.warning("custom_quotes.json 格式不正确，应为列表")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"解析自定义金句 JSON 失败: {e}")
            return []
        except Exception as e:
            logger.error(f"加载自定义金句失败: {e}")
            return []

    def _save_custom_quotes(self) -> bool:
        """保存用户自定义金句

        Returns:
            是否保存成功
        """
        try:
            with open(self.custom_quotes_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_quotes, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存自定义金句失败: {e}")
            return False

    def _format_quote(self, quote: Dict[str, str]) -> str:
        """格式化金句输出

        Args:
            quote: 金句字典，包含 content, character, source

        Returns:
            格式化后的字符串
        """
        content = quote.get("content", "")
        character = quote.get("character", "未知角色")
        source = quote.get("source", "")

        result = f"**{character}**"
        if source:
            result += f" · *{source}*"
        result += f"\n{content}"  # ← 修复：\n 用转义，不要真的换行
        return result

    def _validate_quote_content(self, content: str) -> Tuple[bool, str]:
        """验证金句内容

        Args:
            content: 金句内容

        Returns:
            (bool, str): (是否有效, 错误信息)
        """
        if not content or not content.strip():
            return False, "金句内容不能为空"
        if len(content) > MAX_QUOTE_LENGTH:
            return False, f"金句内容过长（最大 {MAX_QUOTE_LENGTH} 字符）"
        return True, ""

    def _validate_character(self, character: str) -> Tuple[bool, str]:
        """验证角色名

        Args:
            character: 角色名

        Returns:
            (bool, str): (是否有效, 错误信息)
        """
        if len(character) > MAX_CHARACTER_LENGTH:
            return False, f"角色名过长（最大 {MAX_CHARACTER_LENGTH} 字符）"
        return True, ""

    def _validate_source(self, source: str) -> Tuple[bool, str]:
        """验证来源

        Args:
            source: 来源

        Returns:
            (bool, str): (是否有效, 错误信息)
        """
        if len(source) > MAX_SOURCE_LENGTH:
            return False, f"来源过长（最大 {MAX_SOURCE_LENGTH} 字符）"
        return True, ""

    # =========================================================================
    # 指令组定义
    # =========================================================================

    @filter.command_group("崩铁")
    def honkai_group(self):
        """崩坏：星穹铁道金句插件指令组"""
        pass

    @honkai_group.command("金句")
    @handle_errors
    async def honkai_quote(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """随机输出一条崩坏星穹铁道的金句"""
        if not self.all_quotes:
            yield event.plain_result(
                "暂无金句，请先使用 /崩铁 添加 添加一些金句吧！"
            )
            return

        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id()) if event.get_group_id() else None

        # 用户冷却检查（私聊和群聊都生效）
        allowed, msg = await self._check_user_cooldown(user_id)
        if not allowed:
            yield event.plain_result(msg)
            return

        # 群聊每日限制检查（仅群聊生效）
        if group_id:
            allowed, msg = await self._check_group_limit(group_id)
            if not allowed:
                yield event.plain_result(msg)
                return

        quote = random.choice(self.all_quotes)
        yield event.plain_result(self._format_quote(quote))

    @honkai_group.command("添加")
    @handle_errors
    async def add_quote(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """添加一条自定义金句

        用法: /崩铁 添加 金句内容 [角色名] [来源]
        示例: /崩铁 添加 "规则就是用来打破的" 开拓者
        """
        # 从消息文本解析参数
        message = event.message_str
        prefix = "/崩铁 添加" if message.startswith("/崩铁 添加") else "崩铁 添加"
        args_str = message[len(prefix):].strip()

        if not args_str:
            yield event.plain_result(
                "金句内容不能为空！\n"
                "用法: /崩铁 添加 金句内容 [角色名] [来源]\n"
                '示例: /崩铁 添加 "规则就是用来打破的" 开拓者'
            )
            return

        # 解析参数：支持引号包裹的内容
        new_content = ""
        new_character = "未知角色"
        new_source = ""

        if args_str.startswith('"') or args_str.startswith("'"):
            quote_char = args_str[0]
            end_idx = args_str.find(quote_char, 1)
            if end_idx != -1:
                new_content = args_str[1:end_idx].strip()
                remaining = args_str[end_idx + 1:].strip()
                parts = remaining.split(" ", 1)
                new_character = parts[0].strip() if parts[0].strip() else "未知角色"
                new_source = parts[1].strip() if len(parts) > 1 else ""
            else:
                # 引号未闭合，按空格分割
                parts = args_str.split(" ", 2)
                new_content = parts[0].strip().strip('"').strip("'")
                new_character = parts[1].strip() if len(parts) > 1 else "未知角色"
                new_source = parts[2].strip() if len(parts) > 2 else ""
        else:
            parts = args_str.split(" ", 2)
            new_content = parts[0].strip()
            new_character = parts[1].strip() if len(parts) > 1 else "未知角色"
            new_source = parts[2].strip() if len(parts) > 2 else ""

        # 验证输入
        valid, err_msg = self._validate_quote_content(new_content)
        if not valid:
            yield event.plain_result(f"❌ {err_msg}")
            return

        valid, err_msg = self._validate_character(new_character)
        if not valid:
            yield event.plain_result(f"❌ {err_msg}")
            return

        valid, err_msg = self._validate_source(new_source)
        if not valid:
            yield event.plain_result(f"❌ {err_msg}")
            return

        new_quote = {
            "content": new_content,
            "character": new_character,
            "source": new_source
        }

        self.custom_quotes.append(new_quote)
        self.all_quotes = self.default_quotes + self.custom_quotes

        if self._save_custom_quotes():
            yield event.plain_result(
                f"金句添加成功！\n"  # ← 修复：\n 用转义
                f"{self._format_quote(new_quote)}\n"
                f"当前共有 {len(self.all_quotes)} 条金句"
                f"（自定义 {len(self.custom_quotes)} 条）"
            )
        else:
            yield event.plain_result("❌ 金句添加失败，请检查文件权限。")

    @honkai_group.command("删除")
    @handle_errors
    async def delete_quote(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """删除包含指定关键词的自定义金句

        用法: /崩铁 删除 关键词
        示例: /崩铁 删除 史瓦罗
        """
        # 从消息文本解析参数
        message = event.message_str
        prefix = "/崩铁 删除" if message.startswith("/崩铁 删除") else "崩铁 删除"
        keyword = message[len(prefix):].strip()

        if not keyword:
            yield event.plain_result(
                "关键词不能为空！\n"
                "用法: /崩铁 删除 关键词\n"
                "示例: /崩铁 删除 史瓦罗"
            )
            return

        if len(keyword) > MAX_KEYWORD_LENGTH:
            yield event.plain_result(
                f"❌ 关键词过长（最大 {MAX_KEYWORD_LENGTH} 字符）"
            )
            return

        # 只能删除自定义金句
        original_count = len(self.custom_quotes)
        self.custom_quotes = [
            q for q in self.custom_quotes
            if keyword not in q.get("content", "")
        ]
        deleted_count = original_count - len(self.custom_quotes)

        if deleted_count == 0:
            yield event.plain_result(
                f"未找到包含「{keyword}」的自定义金句。\n"
                "注意：默认金句无法删除。"
            )
            return

        self.all_quotes = self.default_quotes + self.custom_quotes

        if self._save_custom_quotes():
            yield event.plain_result(
                f"已删除 {deleted_count} 条包含「{keyword}」的金句。\n"
                f"当前共有 {len(self.all_quotes)} 条金句"
                f"（自定义 {len(self.custom_quotes)} 条）"
            )
        else:
            yield event.plain_result("❌ 删除失败，请检查文件权限。")

    @honkai_group.command("列表")
    @handle_errors
    async def list_quotes(
        self,
        event: AstrMessageEvent,
        page: int = 1
    ) -> AsyncGenerator[Any, None]:
        """列出所有自定义金句

        用法: /崩铁 列表 [页码]
        """
        if not self.custom_quotes:
            yield event.plain_result(
                "暂无自定义金句。\n"
                "使用 /崩铁 添加 来添加你的第一条金句吧！"
            )
            return

        per_page = DEFAULT_QUOTES_PER_PAGE
        total_pages = (len(self.custom_quotes) + per_page - 1) // per_page

        page = max(1, min(page, total_pages))

        start = (page - 1) * per_page
        end = start + per_page
        page_quotes = self.custom_quotes[start:end]

        lines = [
            f"自定义金句列表（第 {page}/{total_pages} 页，"
            f"共 {len(self.custom_quotes)} 条）",
            "-" * 30,
        ]

        for i, quote in enumerate(page_quotes, start=start + 1):
            content = quote.get("content", "")
            character = quote.get("character", "未知角色")
            # 截断过长的内容
            if len(content) > 30:
                content = content[:30] + "..."
            lines.append(f"{i}. [{character}] {content}")

        if total_pages > 1:
            next_page = page + 1 if page < total_pages else 1
            lines.append(f"\n使用 /崩铁 列表 {next_page} 翻页")  # ← 修复：\n 用转义

        yield event.plain_result("\n".join(lines))

    @honkai_group.command("统计")
    @handle_errors
    async def stats_quotes(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """查看金句统计信息"""
        # 统计各角色金句数量
        char_count: Dict[str, int] = {}
        for quote in self.all_quotes:
            char = quote.get("character", "未知角色")
            char_count[char] = char_count.get(char, 0) + 1

        # 按数量排序，取前10
        sorted_chars = sorted(
            char_count.items(),
            key=lambda x: (-x[1], x[0])
        )[:10]

        # 构建横向排列的 TOP10 字符串
        top10_parts = []
        for i, (char, count) in enumerate(sorted_chars, 1):
            top10_parts.append(f"{i}.{char}({count})")
        top10_str = "  ".join(top10_parts)

        lines = [
            "📊 崩铁金句统计",
            "-" * 30,
            f"总金句数: {len(self.all_quotes)}",
            f"  • 默认金句: {len(self.default_quotes)}",
            f"  • 自定义金句: {len(self.custom_quotes)}",
            "",
            "🏆 金句最多的角色 TOP10:",
            top10_str,
        ]

        yield event.plain_result("\n".join(lines))


    @honkai_group.command("帮助")
    @handle_errors
    async def help_quotes(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """查看崩铁金句插件帮助信息"""
        spam_status = "✅ 已开启" if self.anti_spam_enabled else "❌ 已关闭"
        user_cd_status = "✅ 已开启" if self.user_cooldown_enabled else "❌ 已关闭"
        user_cd_time = f"{self.user_cooldown_seconds}秒" if self.user_cooldown_enabled else "N/A"
        group_limit_status = "✅ 已开启" if self.group_daily_limit_enabled else "❌ 已关闭"
        group_limit = f"{self.group_daily_limit}次/天" if self.group_daily_limit_enabled else "N/A"

        help_text = f"""📖 崩坏：星穹铁道金句插件 v1.2.0
━━━━━━━━━━━━━━━━━━━━

⚙️ 配置信息:
  总开关: {spam_status}
  用户冷却: {user_cd_status}（间隔: {user_cd_time}）
  群聊日限: {group_limit_status}（上限: {group_limit}）

🔧 指令列表:
━━━━━━━━━━━━━━━━━━━━
/崩铁 金句 - 随机输出一条金句
/崩铁 添加 <内容> [角色] [来源] - 添加自定义金句
/崩铁 删除 <关键词> - 删除包含关键词的自定义金句
/崩铁 列表 [页码] - 查看自定义金句列表
/崩铁 统计 - 查看金句统计信息
/崩铁 帮助 - 显示此帮助信息

💡 使用示例:
━━━━━━━━━━━━━━━━━━━━
/崩铁 金句
 → 随机输出一条金句

/崩铁 添加 "规则就是用来打破的" 开拓者
 → 添加一条开拓者的金句

/崩铁 添加 "帮帮我，史瓦罗先生！" 克拉拉 角色语音
 → 添加带来源的金句

/崩铁 删除 史瓦罗
 → 删除所有包含"史瓦罗"的自定义金句

/崩铁 列表 2
 → 查看第2页自定义金句

⚠️ 注意事项:
━━━━━━━━━━━━━━━━━━━━
• 默认金句无法删除，只能删除自定义金句
• 自定义金句保存在插件目录的 custom_quotes.json 中
• 添加金句时内容必填，角色名和来源可选
• 防刷屏配置可在 AstrBot WebUI 插件配置中修改
"""
        yield event.plain_result(help_text)

    async def terminate(self) -> None:
        """插件卸载时保存数据"""
        self._save_custom_quotes()
        logger.info("崩铁金句插件已卸载，数据已保存。")

    # =========================================================================
    # Web API (供插件 Pages 使用)
    # =========================================================================

    def _register_web_apis(self) -> None:
        """注册插件 Web API"""
        PLUGIN_NAME = "astrbot_plugin_stellaron"

        self.context.register_web_api(
            f"/{PLUGIN_NAME}/custom-quotes/list",
            self._api_list_custom_quotes,
            ["GET"],
            "获取自定义金句列表",
        )

        self.context.register_web_api(
            f"/{PLUGIN_NAME}/custom-quotes/add",
            self._api_add_custom_quote,
            ["POST"],
            "添加自定义金句",
        )

        self.context.register_web_api(
            f"/{PLUGIN_NAME}/custom-quotes/delete",
            self._api_delete_custom_quote,
            ["POST"],
            "删除自定义金句",
        )

    async def _api_list_custom_quotes(self):
        """API: 获取自定义金句列表"""
        from astrbot.api.web import json_response, request

        page = request.query.get("page", 1, type=int)
        per_page = request.query.get("per_page", 10, type=int)
        keyword = request.query.get("keyword", "", type=str).strip()

        quotes = self.custom_quotes
        if keyword:
            quotes = [
                q for q in quotes
                if keyword in q.get("content", "")
                or keyword in q.get("character", "")
            ]

        total = len(quotes)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))

        start = (page - 1) * per_page
        end = start + per_page
        page_quotes = quotes[start:end]

        return json_response({
            "quotes": page_quotes,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_custom": len(self.custom_quotes),
            "total_default": len(self.default_quotes),
        })

    async def _api_add_custom_quote(self):
        """API: 添加自定义金句"""
        from astrbot.api.web import error_response, json_response, request

        payload = await request.json(default={})

        content = payload.get("content", "").strip()
        character = payload.get("character", "未知角色").strip()
        source = payload.get("source", "").strip()

        if not content:
            return error_response("金句内容不能为空", status_code=400)

        if len(content) > MAX_QUOTE_LENGTH:
            return error_response(f"金句内容过长（最大 {MAX_QUOTE_LENGTH} 字符）", status_code=400)

        if len(character) > MAX_CHARACTER_LENGTH:
            return error_response(f"角色名过长（最大 {MAX_CHARACTER_LENGTH} 字符）", status_code=400)

        if len(source) > MAX_SOURCE_LENGTH:
            return error_response(f"来源过长（最大 {MAX_SOURCE_LENGTH} 字符）", status_code=400)

        new_quote = {
            "content": content,
            "character": character or "未知角色",
            "source": source,
        }

        self.custom_quotes.append(new_quote)
        self.all_quotes = self.default_quotes + self.custom_quotes

        if self._save_custom_quotes():
            return json_response({"saved": True, "total": len(self.custom_quotes)})
        else:
            return error_response("保存失败，请检查文件权限", status_code=500)

    async def _api_delete_custom_quote(self):
        """API: 删除自定义金句（通过索引）"""
        from astrbot.api.web import error_response, json_response, request

        payload = await request.json(default={})
        index = payload.get("index", -1)

        logger.info(f"[WebAPI] 删除请求, index={index}, 当前自定义金句数={len(self.custom_quotes)}")

        if not isinstance(index, int) or index < 0 or index >= len(self.custom_quotes):
            logger.warning(f"[WebAPI] 删除失败: 无效索引 {index}")
            return error_response("无效的索引", status_code=400)

        deleted_quote = self.custom_quotes.pop(index)
        self.all_quotes = self.default_quotes + self.custom_quotes

        if self._save_custom_quotes():
            logger.info(f"[WebAPI] 删除成功: {deleted_quote.get('content', '')[:30]}...")
            return json_response({
                "deleted": 1,
                "content": deleted_quote.get("content", ""),
                "total": len(self.custom_quotes),
            })
        else:
            # 恢复数据
            self.custom_quotes.insert(index, deleted_quote)
            self.all_quotes = self.default_quotes + self.custom_quotes
            logger.error("[WebAPI] 删除失败: 保存文件失败")
            return error_response("保存失败，请检查文件权限", status_code=500)