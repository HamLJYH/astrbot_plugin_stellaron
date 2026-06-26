from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import random
import json
import os
import time

@register("astrbot_plugin_honkai_quotes", "HamLJYH", "崩坏星穹铁道金句插件", "1.2.0", "https://github.com/HamLJYH/astrbot_plugin_stellar")
class HonkaiStarRailQuotes(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)

        # 读取配置（AstrBotConfig 继承自 Dict）
        self.config = config

        # 总开关
        self.anti_spam_enabled = self.config.get("anti_spam_enabled", True)

        # 用户冷却配置
        self.user_cooldown_enabled = self.config.get("user_cooldown_enabled", True)
        self.user_cooldown_seconds = self.config.get("user_cooldown_seconds", 10)

        # 群聊日限配置
        self.group_daily_limit_enabled = self.config.get("group_daily_limit_enabled", True)
        self.group_daily_limit = self.config.get("group_daily_limit", 50)

        # 用户冷却记录：{user_id: last_trigger_timestamp}
        # 只保留最近 user_cooldown_seconds 内的记录，超时自动清理
        self.user_cooldown = {}

        # 群聊每日触发记录：{group_id: {"count": int, "date": str}}
        # 只保留当天的记录，跨天自动清理
        self.group_daily_count = {}

        # 默认金句库
        self.default_quotes = [
            {"content": "煌煌威灵，尊吾敕命，斩无赦！", "character": "景元", "source": "角色语音"},
            {"content": "人们会为一子妙手力挽狂澜而喜，却不为大局危倾而忧。", "character": "景元", "source": "剧情台词"},
            {"content": "就让这一轮月华，照彻万川！", "character": "镜流", "source": "角色语音"},
            {"content": "死亡何时而至？我等得有些心焦了。", "character": "刃", "source": "角色语音"},
            {"content": "此番美景，我虽求而不得，却能邀诸位共赏。", "character": "刃", "source": "角色语音"},
            {"content": "庸人会以自己的方式，创造持有率最高的角色。", "character": "真理医生", "source": "角色语音"},
            {"content": "知识应当流通与分享，真理亦是如此。", "character": "真理医生", "source": "角色语音"},
            {"content": "我来押注，我来博弈，我来赢取。我任命运拨转轮盘，孤注一掷，遍历死地而后生。一切献给——琥珀王。", "character": "砂金", "source": "角色语音"},
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
            {"content": "邀诸位共赏。", "character": "知更鸟", "source": "角色语音"},
            {"content": "对…对不起……", "character": "丹恒", "source": "剧情台词"},
            {"content": "一想到工作，我就浑身头疼……", "character": "银狼", "source": "角色语音"},
            {"content": "愿，此行，终抵群星！", "character": "星期日", "source": "剧情台词"},
            {"content": "我将寻征追猎", "character": "飞霄", "source": "角色语音"},
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

        # 用户自定义金句文件路径
        self.custom_quotes_file = os.path.join(os.path.dirname(__file__), "custom_quotes.json")
        self.custom_quotes = self._load_custom_quotes()

        # 合并默认和用户自定义
        self.all_quotes = self.default_quotes + self.custom_quotes
        logger.info(f"崩铁金句插件加载完成，共 {len(self.all_quotes)} 条金句（默认 {len(self.default_quotes)} 条，自定义 {len(self.custom_quotes)} 条）")

    def _get_today_str(self) -> str:
        """获取今天的日期字符串"""
        return time.strftime("%Y-%m-%d", time.localtime())

    def _clean_expired_records(self):
        """清理过期记录，防止内存泄漏

        - 用户冷却记录：只保留未超时的（当前时间 - 记录时间 < user_cooldown_seconds）
        - 群聊日限记录：只保留当天的
        """
        current_time = time.time()
        expire_time = current_time - self.user_cooldown_seconds

        # 清理用户冷却记录（删除超时的）
        expired_users = [
            uid for uid, t in self.user_cooldown.items() 
            if t < expire_time
        ]
        for uid in expired_users:
            del self.user_cooldown[uid]

        # 清理群聊计数记录（非今天的）
        today = self._get_today_str()
        expired_groups = [
            gid for gid, data in self.group_daily_count.items() 
            if data.get("date") != today
        ]
        for gid in expired_groups:
            del self.group_daily_count[gid]

    def _check_user_cooldown(self, user_id: str) -> tuple:
        """检查用户冷却机制

        Returns:
            (bool, str): (是否允许触发, 提示信息)
        """
        if not self.anti_spam_enabled or not self.user_cooldown_enabled:
            return True, ""

        self._clean_expired_records()

        current_time = time.time()
        last_time = self.user_cooldown.get(user_id, 0)

        if current_time - last_time < self.user_cooldown_seconds:
            remaining = int(self.user_cooldown_seconds - (current_time - last_time))
            return False, f"触发太快了啦！请 {remaining} 秒后再试~"

        self.user_cooldown[user_id] = current_time
        return True, ""

    def _check_group_limit(self, group_id: str) -> tuple:
        """检查群聊每日触发上限

        Returns:
            (bool, str): (是否允许触发, 提示信息)
        """
        if not self.anti_spam_enabled or not self.group_daily_limit_enabled:
            return True, ""

        self._clean_expired_records()

        today = self._get_today_str()

        if group_id not in self.group_daily_count:
            self.group_daily_count[group_id] = {"count": 0, "date": today}

        group_data = self.group_daily_count[group_id]

        # 如果日期不是今天，重置计数
        if group_data.get("date") != today:
            group_data = {"count": 0, "date": today}
            self.group_daily_count[group_id] = group_data

        if group_data["count"] >= self.group_daily_limit:
            return False, f"本群今天的金句次数已经用完啦！明天再来吧~（上限: {self.group_daily_limit}次/天）"

        group_data["count"] += 1
        return True, ""

    def _load_custom_quotes(self):
        """加载用户自定义金句"""
        if os.path.exists(self.custom_quotes_file):
            try:
                with open(self.custom_quotes_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载自定义金句失败: {e}")
                return []
        return []

    def _save_custom_quotes(self):
        """保存用户自定义金句"""
        try:
            with open(self.custom_quotes_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_quotes, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存自定义金句失败: {e}")
            return False

    def _format_quote(self, quote):
        """格式化金句输出"""
        content = quote.get("content", "")
        character = quote.get("character", "未知角色")
        source = quote.get("source", "")

        result = "**" + character + "**"
        if source:
            result += " · *" + source + "*"
        result += "\n\n" + content
        return result

    @filter.command_group("崩铁")
    def honkai_group(self):
        """崩坏：星穹铁道金句插件"""
        pass

    @honkai_group.command("金句")
    async def honkai_quote(self, event: AstrMessageEvent):
        """随机输出一条崩坏星穹铁道的金句"""
        if not self.all_quotes:
            yield event.plain_result("暂无金句，请先使用 /崩铁 添加 添加一些金句吧！")
            return

        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id()) if event.get_group_id() else None

        # 用户冷却检查（私聊和群聊都生效）
        allowed, msg = self._check_user_cooldown(user_id)
        if not allowed:
            yield event.plain_result(msg)
            return

        # 群聊每日限制检查（仅群聊生效）
        if group_id:
            allowed, msg = self._check_group_limit(group_id)
            if not allowed:
                yield event.plain_result(msg)
                return

        quote = random.choice(self.all_quotes)
        yield event.plain_result(self._format_quote(quote))

    @honkai_group.command("添加")
    async def add_quote(self, event: AstrMessageEvent):
        """添加一条自定义金句。用法: /崩铁 添加 金句内容 [角色名] [来源]"""
        # 从消息文本解析参数
        message = event.message_str
        if message.startswith("/崩铁 添加"):
            args_str = message[len("/崩铁 添加"):].strip()
        else:
            args_str = message[len("崩铁 添加"):].strip()

        if not args_str or not args_str.strip():
            yield event.plain_result(
                "金句内容不能为空！" + chr(10) +
                "用法: /崩铁 添加 金句内容 [角色名] [来源]" + chr(10) +
                "示例: /崩铁 添加 \"规则就是用来打破的\" 开拓者"
            )
            return

        # 解析参数：支持引号包裹的内容
        if args_str.startswith('"') or args_str.startswith("'"):
            quote_char = args_str[0]
            end_idx = args_str.find(quote_char, 1)
            if end_idx != -1:
                new_content = args_str[1:end_idx].strip()
                remaining = args_str[end_idx+1:].strip()
                # 解析剩余部分：角色名和来源
                parts = remaining.split(" ", 1)
                new_character = parts[0].strip() if parts[0].strip() else "未知角色"
                new_source = parts[1].strip() if len(parts) > 1 else ""
            else:
                parts = args_str.split(" ", 2)
                new_content = parts[0].strip().strip('"').strip("'")
                new_character = parts[1].strip() if len(parts) > 1 else "未知角色"
                new_source = parts[2].strip() if len(parts) > 2 else ""
        else:
            parts = args_str.split(" ", 2)
            new_content = parts[0].strip()
            new_character = parts[1].strip() if len(parts) > 1 else "未知角色"
            new_source = parts[2].strip() if len(parts) > 2 else ""

        if not new_content:
            yield event.plain_result("金句内容不能为空！")
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
                "金句添加成功！" + chr(10) + chr(10) +
                self._format_quote(new_quote) + chr(10) + chr(10) +
                f"当前共有 {len(self.all_quotes)} 条金句（自定义 {len(self.custom_quotes)} 条）"
            )
        else:
            yield event.plain_result("金句添加失败，请检查文件权限。")

    @honkai_group.command("删除")
    async def delete_quote(self, event: AstrMessageEvent):
        """删除包含指定关键词的自定义金句。用法: /崩铁 删除 关键词"""
        # 从消息文本解析参数
        message = event.message_str
        if message.startswith("/崩铁 删除"):
            keyword = message[len("/崩铁 删除"):].strip()
        else:
            keyword = message[len("崩铁 删除"):].strip()

        if not keyword or not keyword.strip():
            yield event.plain_result(
                "关键词不能为空！" + chr(10) +
                "用法: /崩铁 删除 关键词" + chr(10) +
                "示例: /崩铁 删除 史瓦罗"
            )
            return

        keyword = keyword.strip()

        # 只能删除自定义金句
        original_count = len(self.custom_quotes)
        self.custom_quotes = [
            q for q in self.custom_quotes 
            if keyword not in q.get("content", "")
        ]
        deleted_count = original_count - len(self.custom_quotes)

        if deleted_count == 0:
            yield event.plain_result("未找到包含「" + keyword + "」的自定义金句。" + chr(10) + "注意：默认金句无法删除。")
            return

        self.all_quotes = self.default_quotes + self.custom_quotes

        if self._save_custom_quotes():
            yield event.plain_result(
                "已删除 " + str(deleted_count) + " 条包含「" + keyword + "」的金句。" + chr(10) +
                f"当前共有 {len(self.all_quotes)} 条金句（自定义 {len(self.custom_quotes)} 条）"
            )
        else:
            yield event.plain_result("删除失败，请检查文件权限。")

    @honkai_group.command("列表")
    async def list_quotes(self, event: AstrMessageEvent, page: int = 1):
        """列出所有自定义金句。用法: /崩铁 列表 [页码]"""
        if not self.custom_quotes:
            yield event.plain_result("暂无自定义金句。" + chr(10) + "使用 /崩铁 添加 来添加你的第一条金句吧！")
            return

        per_page = 10
        total_pages = (len(self.custom_quotes) + per_page - 1) // per_page

        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * per_page
        end = start + per_page
        page_quotes = self.custom_quotes[start:end]

        result = "自定义金句列表（第 " + str(page) + "/" + str(total_pages) + " 页，共 " + str(len(self.custom_quotes)) + " 条）" + chr(10)
        result += "-" * 30 + chr(10)

        for i, quote in enumerate(page_quotes, start=start + 1):
            content = quote.get("content", "")
            character = quote.get("character", "未知角色")
            # 截断过长的内容
            if len(content) > 30:
                content = content[:30] + "..."
            result += str(i) + ". [" + character + "] " + content + chr(10)

        if total_pages > 1:
            result += chr(10) + "使用 /崩铁 列表 " + str(page + 1 if page < total_pages else 1) + " 翻页"

        yield event.plain_result(result)

    @honkai_group.command("统计")
    async def stats_quotes(self, event: AstrMessageEvent):
        """查看金句统计信息"""
        # 统计各角色金句数量
        char_count = {}
        for quote in self.all_quotes:
            char = quote.get("character", "未知角色")
            char_count[char] = char_count.get(char, 0) + 1

        # 按数量排序
        sorted_chars = sorted(char_count.items(), key=lambda x: (-x[1], x[0]))[:10]

        result = "崩铁金句统计" + chr(10)
        result += "-" * 30 + chr(10)
        result += "总金句数: " + str(len(self.all_quotes)) + chr(10)
        result += "  - 默认金句: " + str(len(self.default_quotes)) + chr(10)
        result += "  - 自定义金句: " + str(len(self.custom_quotes)) + chr(10) + chr(10)

        result += "金句最多的角色 TOP10:" + chr(10)
        for i, (char, count) in enumerate(sorted_chars, 1):
            result += str(i) + ". " + char + ": " + str(count) + "条" + chr(10)

        # 显示防刷屏配置
        result += chr(10) + "防刷屏配置:" + chr(10)
        result += "-" * 30 + chr(10)
        result += "总开关: " + ("已开启" if self.anti_spam_enabled else "已关闭") + chr(10)
        result += "  用户冷却: " + ("已开启" if self.user_cooldown_enabled else "已关闭")
        if self.user_cooldown_enabled:
            result += "（" + str(self.user_cooldown_seconds) + "秒）"
        result += chr(10)
        result += "  群聊日限: " + ("已开启" if self.group_daily_limit_enabled else "已关闭")
        if self.group_daily_limit_enabled:
            result += "（" + str(self.group_daily_limit) + "次/天）"
        result += chr(10)

        yield event.plain_result(result)

    @honkai_group.command("帮助")
    async def help_quotes(self, event: AstrMessageEvent):
        """查看崩铁金句插件帮助信息"""
        # 配置状态
        spam_status = "已开启" if self.anti_spam_enabled else "已关闭"
        user_cooldown_status = "已开启" if self.user_cooldown_enabled else "已关闭"
        user_cooldown_time = f"{self.user_cooldown_seconds}秒" if self.user_cooldown_enabled else "N/A"
        group_limit_status = "已开启" if self.group_daily_limit_enabled else "已关闭"
        group_limit = f"{self.group_daily_limit}次/天" if self.group_daily_limit_enabled else "N/A"

        help_lines = [
            "崩坏：星穹铁道金句插件",
            "",
            "配置信息:",
            "  总开关: " + spam_status,
            "  用户冷却: " + user_cooldown_status + "（间隔: " + user_cooldown_time + "）",
            "  群聊日限: " + group_limit_status + "（上限: " + group_limit + "）",
            "",
            "指令列表:",
            "------------------------------",
            "/崩铁 金句 - 随机输出一条金句",
            "/崩铁 添加 <内容> [角色名] [来源] - 添加自定义金句",
            "/崩铁 删除 <关键词> - 删除包含关键词的自定义金句",
            "/崩铁 列表 [页码] - 查看自定义金句列表",
            "/崩铁 统计 - 查看金句统计信息",
            "/崩铁 帮助 - 显示此帮助信息",
            "",
            "使用示例:",
            "------------------------------",
            "/崩铁 金句",
            "-> 随机输出一条金句",
            "",
            '/崩铁 添加 "规则就是用来打破的" 开拓者',
            "-> 添加一条开拓者的金句",
            "",
            '/崩铁 添加 "帮帮我，史瓦罗先生！" 克拉拉 角色语音',
            "-> 添加带来源的金句",
            "",
            "/崩铁 删除 史瓦罗",
            '-> 删除所有包含"史瓦罗"的自定义金句',
            "",
            "/崩铁 列表 2",
            "-> 查看第2页自定义金句",
            "",
            "注意事项:",
            "------------------------------",
            "- 默认金句无法删除，只能删除自定义金句",
            "- 自定义金句保存在插件目录的 custom_quotes.json 中",
            "- 添加金句时内容必填，角色名和来源可选",
            "- 防刷屏配置可在 AstrBot WebUI 插件配置中修改",
        ]
        help_text = chr(10).join(help_lines)
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件卸载时保存数据"""
        self._save_custom_quotes()
        logger.info("崩铁金句插件已卸载，数据已保存。")