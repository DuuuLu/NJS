﻿"""------------------------------导入依赖------------------------------"""
import httpx
import asyncio
import requests
from loguru import logger
from nonebot.rule import to_me
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException
from nonebot.plugin.on import on_keyword, on_message, on_notice, on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    Message,
    NotifyEvent,
    MessageEvent,
    MessageSegment,
    PokeNotifyEvent,
    GroupMessageEvent,
)
# 从 utils 中导入一堆东西
from .utils import *
#-------------------ChatGPT-------------------------#
from .chatgpt import Chatbot
from .config import config
from .data import setting
chat_bot = Chatbot(
    token=setting.token or config.chatgpt_session_token,
    model=config.chatgpt_model,
    account=config.chatgpt_account,
    password=config.chatgpt_password,
    api=config.chatgpt_api,
    proxies=config.chatgpt_proxies,
    presets=setting.presets,
    timeout=config.chatgpt_timeout,
)
session = Session(config.chatgpt_scope)

logger.info(logo) # 在日志中输出打印logo



"""------------------------------响应部分------------------------------"""
ai = on_message(rule=to_me(), priority=99, block=True)
attack = on_keyword(curse, rule=to_me(), block=True, priority=1) # ban 人的响应器, curse 是关键词列表
remove_CD = on_command("remove_qq", aliases={"rm_qq"}, permission=SUPERUSER, priority=5, block=True, rule=to_me())
# -------------------------------api部分---------------------切换均需要艾特
api_switch = on_command("切换", aliases={"change", "switch"}, rule=to_me(), priority=3, permission=SUPERUSER, block=True)
setu_switch = on_command("切换图片api", rule=to_me(), priority=1, permission=SUPERUSER, block=True)
api_check = on_command("查看当前api", aliases={"查看api"}, priority=5, block=True, rule=to_me()) # 普通用户也可以查询
poke = on_notice(rule=to_me(), block=False) # 戳一戳
# -------------------------------ChatGPT------------------------------
refresh = on_command("api刷新对话", aliases={"api刷新会话"},priority=50, block=True,  rule=to_me()) # 重新开始 ChatGPT 的对话
refresh = on_command("token刷新对话", aliases={"token刷新会话"}, block=True, rule=to_me(), priority=10)



"""------------------------------预处理信息------------------------------"""
@attack.handle()
async def handle_receive(event: MessageEvent):
    img = Path(os.path.join(os.path.dirname(__file__), "resource")) / "1.jpg"
    qid = event.get_user_id()
    data = read_json_ban()
    mid = event.message_id
    write_json_ban(qid, event.time, mid, data) # 写入 json 记录用户时间
    await attack.send(message=f"{random.choice(attack_sendmessage)}"+MessageSegment.image(img), at_sender=True)

@event_preprocessor # 阻断信息
async def event_preblock_sb(event: Event, bot: Bot):
    # 当event类型为MessageEvent(消息事件)或NotifyEvent(提醒事件)
    if isinstance(event,MessageEvent) or isinstance(event,NotifyEvent):
        # 如果不是超级用户, 执行以下操作
        if not event.get_user_id() in bot.config.superusers:
            qid = event.get_user_id()
            data = read_json_ban()
            try:
                cd = event.time - data[qid][0]
            except Exception:
                cd = ban_cd_time + 1
            if cd > ban_cd_time:
                return
            blockreason = "这货骂了我家bot"
            if blockreason:
                logger.info(f'当前事件已阻断，原因：{blockreason}')
                raise IgnoredException(blockreason)
    # 其它事件跳过
    else:
        pass

@remove_CD.handle() # 超级用户用来移除被 ban 的用户
async def _(msg: Message = CommandArg()):
    # 获取消息文本
    qid = msg.extract_plain_text()
    boolean = False
    try:
        remove_json_ban(qid)
        boolean = True
    except:
        pass
    if boolean:
        await remove_CD.finish(f"ID:{qid}CD已清除, 下次别骂{Bot_NICKNAME}了")
    else:
        await remove_CD.finish(f"{Bot_NICKNAME}记忆里没有这号人欸")



"""------------------------------api部分------------------------------"""
@api_switch.handle()
async def _(switch_msg: Message = CommandArg()):
    switch_msg = switch_msg.extract_plain_text().strip()
    global api_num
    if switch_msg == "小爱同学api模式2":
        api_num = 0
    elif switch_msg == "小爱同学api模式1":
        api_num = 1
    elif switch_msg == "青云客api":
        api_num = 2
    elif switch_msg == "ChatGPTapi模式1":
        api_num = 3
    elif switch_msg == "ChatGPTapi模式2":
        api_num = 4
    else:
        await api_switch.finish("没有这个api哦~")
    finish_msg = f"切换成功, 当前智能回复api为{api_num}".replace('1', "小爱同学模式1").replace('2', "青云客"
        ).replace('3', "ChatGPT(使用Token)").replace('4', "ChatGPT(使用API)").replace('0', "小爱同学模式2")
    await api_switch.finish(finish_msg)

@setu_switch.handle()
async def _():
    global setu_flag
    setu_flag = not setu_flag
    await setu_switch.send(message=f"切换成功, 当前戳一戳图片api为{'MirlKoi' if setu_flag else 'Pixiv'}")

@api_check.handle()
async def check():
    check_msg = f"当前图片 api 为 {setu_flag};\n当前聊天 api 为 {api_num}".replace('1', "小爱同学模式1").replace('2', "青云客").replace('3',
        "ChatGPT(使用Token)").replace('4', "ChatGPT(使用API)").replace('0', "小爱同学模式2").replace('True', "MirlKoi").replace('False', "Pixiv")
    await api_check.send(check_msg)




"""------------------------------智能回复部分------------------------------"""
@ai.handle()
async def _(event: MessageEvent):
    # 获取消息文本
    msg = str(event.get_message())
    # 去掉带中括号的内容(去除cq码)
    msg = re.sub(r"\[.*?\]", "", msg)
    # 如果是光艾特bot(没消息返回)或者打招呼的话,就回复以下内容
    if (not msg) or msg.isspace() or msg in [
        "你好啊",
        "你好",
        "在吗",
        "在不在",
        "您好",
        "您好啊",
        "你好",
        "在",
    ]:
        await ai.finish(Message(random.choice(hello__reply)))
    # 获取用户nickname
    if isinstance(event, GroupMessageEvent):
        nickname = event.sender.card or event.sender.nickname
    else:
        nickname = event.sender.nickname
    # 从字典里获取结果
    result = await get_chat_result(msg, nickname)
    # 如果词库没有结果，则调用api获取智能回复
    if result == None:
        if api_num in [0, 1]:
            msg = msg.replace(" ","") # 去除消息中的空格, 不知道为什么, 如果消息中存在空格, 这个 api 大概率会返回空字符
            logger.debug("传入的信息为{}".format(msg))
            xiaoai_url = f"https://xiaoapi.cn/API/lt_xiaoai.php?type=json&msg={msg}"
            message, voice = await xiaoice_reply(xiaoai_url)
            if api_num == 1:
                logger.info("来自小爱同学的智能回复: " + message)
                await ai.finish(message=message)
            elif api_num == 0:
                logger.info("尝试发送语音...")
                response = requests.get(voice)
                with open('./src/plugins/nonebot_plugin_smart_reply/voice.mp3', 'wb') as f:
                    f.write(response.content)
                await ai.finish(message=MessageSegment.record(file="./src/plugins/nonebot_plugin_smart_reply/voice.mp3").record(file=voice))

        elif api_num == 2:
            qinyun_url = f"http://api.qingyunke.com/api.php?key=free&appid=0&msg={msg}"
            message = await qinyun_reply(qinyun_url)
            logger.info("来自青云客的智能回复: " + message)
            await ai.finish(message=message)

        else:
            # 冷却时间
            qid = event.get_user_id() 
            try:
                cd = event.time - openai_cd_dir[qid]
            except KeyError:
                cd = api_cd_time + 1
            if (cd>api_cd_time or event.get_user_id() in nonebot.get_driver().config.superusers):  # 超过cd时间或者是超级用户
                openai_cd_dir.update({qid: event.time}) # 记录cd
                if api_num == 3:
                    played_name = config.chatgpt_default_preset
                    if not chat_bot.presets.get(played_name):
                        played_name = ""
                    cvst = session[event]
                    try:
                        if config.chatgpt_notice:
                            msg = "收到请求，等待响应..."
                            if not has_title:
                                msg += f"\n首次请求，人格设定: {played_name if played_name else '无'}"
                            await ai.send(msg)
                        msg = await chat_bot(**cvst, played_name=played_name).get_chat_response(msg)
                        if (msg == "token失效，请重新设置token" and chat_bot.session_token != config.chatgpt_session_token):
                            chat_bot.session_token = config.chatgpt_session_token
                            msg = await chat_bot(**cvst, played_name=played_name).get_chat_response(msg)
                        elif (msg == "会话不存在"):
                            if config.chatgpt_auto_refresh:
                                has_title = False
                                cvst['conversation_id'].append(None)
                                cvst['parent_id'].append(chat_bot.id)
                                await ai.send("会话不存在，已自动刷新对话，等待响应...")
                                msg = await chat_bot(**cvst, played_name=played_name).get_chat_response(msg)
                            else:
                                msg += ",请刷新会话"
                    except Exception as e:
                        lockers[event.user_id] = False
                        error = f"{type(e).__name__}: {e}"
                        logger.opt(exception=e).error(f"ChatGPT request failed: {error}")
                        await ai.finish(f"请求 ChatGPT 服务器时出现问题，请稍后再试\n错误信息: {error}")
                    lockers[event.user_id] = False
                    await ai.finish(msg, at_sender=True)

                elif api_num == 4:
                    if api_key == "寄":                             
                        await ai.finish("请先配置openai_api_key")
                    loop = asyncio.get_event_loop() # 获取事件循环
                    try:
                        res = await loop.run_in_executor(None, get_openai_reply, msg) # 开一个不会阻塞asyncio的线程调用get_openai_reply函数
                    except Exception as e:                                            # 如果出错
                        await ai.finish(str(e))                                       # 发送错误信息
                    await ai.finish(MessageSegment.text(res),at_sender=True)          # 发送结果
            else:
                await ai.finish(MessageSegment.text(f"{Bot_NICKNAME}冷却中... 剩余时间 {api_cd_time - cd:.0f} 秒"),at_sender=True)
    await ai.finish(Message(result))



"""------------------------------ChatGPT刷新会话------------------------------"""
@refresh.handle()
async def refresh_conversation(event: MessageEvent) -> None:
    if not check_purview(event):
        await refresh.finish("当前为公共会话模式, 仅支持群管理操作")
    session[event]['conversation_id'].append(None)
    session[event]['parent_id'].append(chat_bot.id)
    await refresh.send("当前会话已刷新")



"""------------------------------戳一戳部分------------------------------"""
@poke.handle()
async def _poke(bot: Bot,event: PokeNotifyEvent)-> bool:
    if event.is_tome:
        probability = random.random()
        # 20% 概率发送图片
        if probability < 0.20:
            if setu_flag:
                async def func(client,url):
                    resp = await client.get(url,headers={'Referer':'http://www.weibo.com/',})
                    if resp.status_code == 200:
                        return resp.content
                    else:
                        return None
                res = httpx.get(url='https://dev.iw233.cn/api.php?sort=pc&type=json', headers={'Referer':'http://www.weibo.com/'})
                res = res.text
                res = ''.join(x for x in res if x.isprintable())
                res = json.loads(res)["pic"]
                async with httpx.AsyncClient() as client:
                    task_list = []
                    for url in res:
                        task = asyncio.create_task(func(client,url))
                        task_list.append(task)
                    image_list = await asyncio.gather(*task_list)
                image_list = [image for image in image_list if image]
                pic_url = image_list[0]
                
                # res = requests.get('https://img.moehu.org/pic.php?return=json&id=img1&num=1').json()
                # pic_url = res["pic"][0]
                message="别戳了别戳了,这张图给你了,让我安静一会儿,60秒后我要撤回\n" + MessageSegment.image(file=pic_url)
            else:
                pic = await get_setu()
                message="别戳了别戳了,这张setu给你了,让我安静一会儿,60秒后我要撤回\n" + Message(pic[1]) + Message(pic[0])
            setu_msg_id = await poke.send(message)
            setu_msg_id = setu_msg_id['message_id']
            await asyncio.sleep(60)
            await bot.delete_msg(message_id=setu_msg_id)
            return
        # 25% 概率回复 ".resource/audio" 目录下的 *.aac 语音
        elif probability < 0.45:
            # 发送语音需要配置ffmpeg, 不行就随机回复poke_reply的内容
            try:
                await poke.send(MessageSegment.record(Path(aac_file_path)/random.choice(aac_file_list)))
            except:
                await poke.send(message=f"{random.choice(poke_reply)}")
        # 20% 概率戳回去
        elif probability < 0.65:
            await poke.send(Message(f"[CQ:poke,qq={event.user_id}]"))
        # 35% 概率回复戳一戳文本
        else:
            await poke.send(message=f"{random.choice(poke_reply)}")
