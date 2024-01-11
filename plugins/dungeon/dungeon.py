# encoding:utf-8

import plugins
from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common import const
from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf
from plugins import *


# https://github.com/bupticybee/ChineseAiDungeonChatGPT
class StoryTeller:
    def __init__(self, bot, sessionid, story):
        self.bot = bot
        self.sessionid = sessionid
        bot.sessions.clear_session(sessionid)
        self.first_interact = True
        self.story = story

    def reset(self):
        self.bot.sessions.clear_session(self.sessionid)
        self.first_interact = True

    def action(self, user_action):
        if user_action[-1] != "。":
            user_action = user_action + "。"
        if self.first_interact:
            prompt = (
                """你将扮演一个文字冒险游戏的作者，你的任务是用生动的语言和我互动，一起创造一个引人入胜的故事。你需要注意以下几点：
- 描述时要控制好节奏，不要让我感到无聊或者迷失。
- 仔细描述各个人物的心情和周边环境，让我能够感同身受，产生共鸣。
- 一次只需写四到六句话，不要过长或者过短，保持适当的段落长度。
- 尽量使用有趣的词汇和修辞手法，避免重复和陈词滥调，提高文采和吸引力。\n开头是:"""
                + self.story
                + " "
                + user_action
            )
            self.first_interact = False
        else:
            prompt = f"""继续你的文字冒险游戏，一次只需要续写四到六句话，描述接下来发生的事情,{user_action}。你需要注意以下几点：
- 续写时要保持好故事的连贯性和逻辑性，不要出现突兀或者不合理的情节。
- 描述时要注意时间的流逝，总共就只讲5分钟内发生的事情，不要跳跃或者拖沓。
- 尽量设置一些有趣的转折和冲突，让我感到惊喜和紧张，激发我的好奇心和探索欲。
- 适当地使用对话和心理描写，让人物的性格和情感更加鲜明和真实。""" 
        return prompt


@plugins.register(
    name="Dungeon",
    desire_priority=0,
    namecn="文字冒险",
    desc="A plugin to play dungeon game",
    version="1.0",
    author="lanvent",
)
class Dungeon(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[Dungeon] inited")
        # 目前没有设计session过期事件，这里先暂时使用过期字典
        if conf().get("expires_in_seconds"):
            self.games = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            self.games = dict()

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return
        bottype = Bridge().get_bot_type("chat")
        if bottype not in [const.SYDNEY, const.OPEN_AI, const.CHATGPT, const.CHATGPTONAZURE, const.LINKAI]:
            return
        bot = Bridge().get_bot("chat")
        content = e_context["context"].content[:]
        clist = e_context["context"].content.split(maxsplit=1)
        sessionid = e_context["context"]["session_id"]
        logger.debug("[Dungeon] on_handle_context. content: %s" % clist)
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        if clist[0] == f"{trigger_prefix}停止冒险" or clist[0] == "清除记忆":
            if sessionid in self.games:
                self.games[sessionid].reset()
                del self.games[sessionid]
                reply = Reply(ReplyType.INFO, "冒险结束!")
                e_context["reply"] = reply
                if clist[0] == f"{trigger_prefix}停止冒险":
                    e_context.action = EventAction.BREAK_PASS
        elif clist[0] == f"{trigger_prefix}开始冒险" or sessionid in self.games:
            if sessionid not in self.games or clist[0] == f"{trigger_prefix}开始冒险":
                if len(clist) > 1:
                    story = clist[1]
                else:
                    story = "你在树林里冒险，指不定会从哪里蹦出来一些奇怪的东西，你握紧手上的手枪，希望这次冒险能够找到一些值钱的东西，你往树林深处走去。"
                self.games[sessionid] = StoryTeller(bot, sessionid, story)
                reply = Reply(ReplyType.INFO, "冒险开始，你可以输入任意内容，让故事继续下去。故事背景是：" + story)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
            else:
                prompt = self.games[sessionid].action(content)
                e_context["context"].type = ContextType.TEXT
                e_context["context"].content = prompt
                e_context.action = EventAction.BREAK  # 事件结束，不跳过处理context的默认逻辑

    def get_help_text(self, **kwargs):
        help_text = "可以和Sydney一起玩文字冒险游戏。\n"
        if kwargs.get("verbose") != True:
            return help_text
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        help_text = f"{trigger_prefix}开始冒险 " + "背景故事: 开始一个基于{背景故事}的文字冒险，之后你的所有消息会协助完善这个故事。\n" + f"{trigger_prefix}停止冒险: 结束游戏。\n"
        if kwargs.get("verbose") == True:
            help_text += f"\n命令例子: '{trigger_prefix}开始冒险 你在树林里冒险，指不定会从哪里蹦出来一些奇怪的东西，你握紧手上的手枪，希望这次冒险能够找到一些值钱的东西，你往树林深处走去。'"
        return help_text
