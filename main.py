#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import telegram.ext
import telegram
import sys
import datetime
import os
import logging
import threading
import traceback
import html

Version_Code = 'v1.1.0'  # 版本号

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )

PATH = os.path.dirname(os.path.realpath(__file__)) + '/'

CONFIG = json.loads(open(PATH + 'config.json', 'r').read())  # 加载配置文件

LANG = json.loads(open(PATH + 'lang/' + CONFIG['Lang'] + '.json'
                  ).read())  # 加载语言文件

MESSAGE_LOCK = False

message_list = json.loads(open(PATH + 'data.json', 'r').read())  # 加载消息数据

PREFERENCE_LOCK = False

preference_list = json.loads(open(PATH + 'preference.json', 'r').read())  # 加载用户资料与设置

def save_data():  # 保存消息数据
    global MESSAGE_LOCK
    while MESSAGE_LOCK:
        time.sleep(0.05)
    MESSAGE_LOCK = True
    f = open(PATH + 'data.json', 'w')
    f.write(json.dumps(message_list))
    f.close()
    MESSAGE_LOCK = False

def save_preference():  # 保存用户资料与设置
    global PREFERENCE_LOCK
    while PREFERENCE_LOCK:
        time.sleep(0.05)
    PREFERENCE_LOCK = True
    f = open(PATH + 'preference.json', 'w')
    f.write(json.dumps(preference_list))
    f.close()
    PREFERENCE_LOCK = False

def save_config():  # 保存配置
    f = open(PATH + 'config.json', 'w')
    f.write(json.dumps(CONFIG, indent=4))
    f.close()

def init_user(user):  # 初始化用户
    global preference_list
    if not str(user.id) in preference_list:  # 如果用户是第一次使用Bot
        preference_list[str(user.id)] = {}
        preference_list[str(user.id)]['notification'] = False  # 默认关闭消息发送提示
        preference_list[str(user.id)]['blocked'] = False # 默认用户未被封禁
        preference_list[str(user.id)]['name'] = user.full_name  # 保存用户昵称
        threading.Thread(target=save_preference).start()
        return
    if not 'blocked' in preference_list[str(user.id)]: # 兼容1.0.x版本
        preference_list[str(user.id)]['blocked'] = False
    if preference_list[str(user.id)]['name'] != user.full_name:  # 如果用户的昵称变了
        preference_list[str(user.id)]['name'] = user.full_name
        threading.Thread(target=save_preference).start()

updater = telegram.ext.Updater(token=CONFIG['Token'], use_context=True)
dispatcher = updater.dispatcher

me = updater.bot.get_me()
CONFIG['ID'] = me.id
CONFIG['Username'] = '@' + me.username

print('Starting... (ID: ' + str(CONFIG['ID']) + ', Username: ' \
    + CONFIG['Username'] + ')')

def error_handler(update: object, context:telegram.ext.CallbackContext): # 处理错误信息
    global CONFIG

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    
    update_str = update.to_dict() if isinstance(update, telegram.Update) else str(update)

    message = LANG['error_found'] + '<pre>update = {' + html.escape(json.dumps(update_str, indent=2, ensure_ascii=False)) + '}</pre>\n\n' + '<pre>context.chat_data = ' + html.escape(str(context.chat_data)) + '</pre>\n\n' + '<pre>context.user_data = ' + html.escape(str(context.user_data)) + '</pre>\n\n' + '<pre>{\n' + html.escape(tb_string) + '\n}</pre>'
    context.bot.send_message(chat_id=CONFIG['Record_Channel_ID'], text=message, parse_mode=telegram.ParseMode.HTML)

def process_msg(update: telegram.Update, context: telegram.ext.CallbackContext):  # 处理消息
    global message_list
    init_user(update.message.from_user)
    if CONFIG['Admin'] == 0:  # 如果未设置管理员
        context.bot.send_message(chat_id=update.message.from_user.id,
                         text=LANG['please_setup_first'])
        return
    if update.message.from_user.id == CONFIG['Admin']:  # 如果是管理员发送的消息
        if update.message.reply_to_message:  # 如果未回复消息
            if str(update.message.reply_to_message.message_id) in message_list:  # 如果消息数据存在
                msg = update.message
                sender_id = message_list[str(update.message.reply_to_message.message_id)]['sender_id']
                # 匿名转发
                try:
                    if msg.audio:
                        context.bot.send_audio(chat_id=sender_id,
                                audio=msg.audio, caption=msg.caption)
                    elif msg.document:
                        context.bot.send_document(chat_id=sender_id,
                                document=msg.document,
                                caption=msg.caption)
                    elif msg.voice:
                        context.bot.send_voice(chat_id=sender_id,
                                voice=msg.voice, caption=msg.caption)
                    elif msg.video:
                        context.bot.send_video(chat_id=sender_id,
                                video=msg.video, caption=msg.caption)
                    elif msg.sticker:
                        context.bot.send_sticker(chat_id=sender_id,
                                sticker=update.message.sticker)
                    elif msg.photo:
                        context.bot.send_photo(chat_id=sender_id,
                                photo=msg.photo[0], caption=msg.caption)
                    elif msg.text_markdown_v2:
                        context.bot.send_message(chat_id=sender_id,
                                text=msg.text_markdown_v2,
                                parse_mode=telegram.ParseMode.MARKDOWN_V2)
                    else:
                        context.bot.send_message(chat_id=CONFIG['Admin'],
                                text=LANG['reply_type_not_supported'])
                        return
                except Exception as e:
                    if e.message \
                        == 'Forbidden: bot was blocked by the user':
                        context.bot.send_message(chat_id=CONFIG['Admin'],
                                text=LANG['blocked_alert'])  # Bot被停用
                    else:
                        context.bot.send_message(chat_id=CONFIG['Admin'],
                                text=LANG['reply_message_failed'])
                    return
                if preference_list[str(update.message.from_user.id)]['notification']:  # 如果启用消息发送提示
                    context.bot.send_message(chat_id=update.message.chat_id,
                            text=LANG['reply_message_sent']
                            % (preference_list[str(sender_id)]['name'], str(sender_id)),
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
            else:
                context.bot.send_message(chat_id=CONFIG['Admin'],
                                 text=LANG['reply_to_message_no_data'])
        else:
            context.bot.send_message(chat_id=CONFIG['Admin'],
                             text=LANG['reply_to_no_message'])
    else: # 如果不是管理员发送的消息
        if preference_list[str(update.message.from_user.id)]['blocked']:
            context.bot.send_message(chat_id=update.message.from_user.id,text=LANG['be_blocked_alert'])
            return
        fwd_msg = context.bot.forward_message(chat_id=CONFIG['Admin'],
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id)  # 转发消息
        if fwd_msg.sticker:  # 如果是贴纸，则发送发送者身份提示
            context.bot.send_message(chat_id=CONFIG['Admin'],
                             text=LANG['info_data'] 
                             % (update.message.from_user.full_name, str(update.message.from_user.id)),
                             parse_mode=telegram.ParseMode.MARKDOWN_V2,
                             reply_to_message_id=fwd_msg.message_id)
        if preference_list[str(update.message.from_user.id)]['notification']:  # 如果启用消息发送提示
            context.bot.send_message(chat_id=update.message.from_user.id,text=LANG['message_received_notification'])
        message_list[str(fwd_msg.message_id)] = {}
        message_list[str(fwd_msg.message_id)]['sender_id'] = update.message.from_user.id
        threading.Thread(target=save_data).start()  # 保存消息数据
    pass

def process_command(update: telegram.Update, context: telegram.ext.CallbackContext):  # 处理指令
    init_user(update.message.from_user)
    id = update.message.from_user.id
    global CONFIG
    global preference_list
    command = update.message.text[1:].replace(CONFIG['Username'], ''
            ).lower().split()
    if command[0] == 'start':
        context.bot.send_message(chat_id=update.message.chat_id,
                         text=LANG['start'])
        return
    elif command[0] == 'version':
        context.bot.send_message(chat_id=update.message.chat_id,
                         text='Telegram Private Message Chat Bot\n'
                         + Version_Code
                         + '\nnull'
                         )
        return
    elif command[0] == 'setadmin': # 设置管理员
        if CONFIG['Admin'] == 0:  # 判断管理员是否未设置
            CONFIG['Admin'] = int(update.message.from_user.id)
            save_config()
            context.bot.send_message(chat_id=update.message.chat_id,
                             text=LANG['set_admin_successful'])
        else:
            context.bot.send_message(chat_id=update.message.chat_id,
                             text=LANG['set_admin_failed'])
        return
    elif command[0] == 'togglenotification': # 切换消息发送提示开启状态
        preference_list[str(id)]['notification'] = \
            preference_list[str(id)]['notification'] == False
        threading.Thread(target=save_preference).start()
        if preference_list[str(id)]['notification']:
            context.bot.send_message(chat_id=update.message.chat_id,
                             text=LANG['togglenotification_on'])
        else:
            context.bot.send_message(chat_id=update.message.chat_id,
                             text=LANG['togglenotification_off'])
    elif command[0] == 'info': # 发送者信息
        if update.message.from_user.id == CONFIG['Admin'] \
            and update.message.chat_id == CONFIG['Admin']:
            if update.message.reply_to_message:
                if str(update.message.reply_to_message.message_id) in message_list:
                    sender_id = message_list[str(update.message.reply_to_message.message_id)]['sender_id']
                    context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=LANG['info_data']
                        % (preference_list[str(sender_id)]['name'], str(sender_id)),
                        parse_mode=telegram.ParseMode.MARKDOWN_V2,
                        reply_to_message_id=update.message.reply_to_message.message_id)
                else:
                    context.bot.send_message(chat_id=update.message.chat_id,text=LANG['reply_to_message_no_data'])
            else:
                context.bot.send_message(chat_id=update.message.chat_id,text=LANG['reply_to_no_message'])
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=LANG['not_an_admin'])
    elif command[0] == 'ping': # Ping~Pong!
        context.bot.send_message(chat_id=update.message.chat_id, text='嗯？刚刚是你叫我吗？')
    elif command[0] == 'ban': # 封禁用户    
        if update.message.from_user.id == CONFIG['Admin'] \
            and update.message.chat_id == CONFIG['Admin']:
            if update.message.reply_to_message:
                if str(update.message.reply_to_message.message_id) in message_list:
                    sender_id = message_list[str(update.message.reply_to_message.message_id)]['sender_id']
                    preference_list[str(sender_id)]['blocked'] = True
                    context.bot.send_message(chat_id=update.message.chat_id,
                            text=LANG['ban_user']
                            % (preference_list[str(sender_id)]['name'],
                            str(sender_id)),
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
                    context.bot.send_message(chat_id=sender_id,text=LANG['be_blocked_alert'])
                else:
                    context.bot.send_message(chat_id=update.message.chat_id,text=LANG['reply_to_message_no_data'])
            else:
                context.bot.send_message(chat_id=update.message.chat_id,text=LANG['reply_to_no_message'])
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=LANG['not_an_admin'])
    elif command[0] == 'unban': # 解禁用户
        if update.message.from_user.id == CONFIG['Admin'] \
            and update.message.chat_id == CONFIG['Admin']:
            if update.message.reply_to_message:
                if str(update.message.reply_to_message.message_id) in message_list:
                    sender_id = message_list[str(update.message.reply_to_message.message_id)]['sender_id']
                    preference_list[str(sender_id)]['blocked'] = False
                    context.bot.send_message(chat_id=update.message.chat_id,
                            text=LANG['unban_user']
                            % (preference_list[str(sender_id)]['name'],
                            str(sender_id)),
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
                    context.bot.send_message(chat_id=sender_id,text=LANG['be_unbanned'])
                else:
                    context.bot.send_message(chat_id=update.message.chat_id,text=LANG['reply_to_message_no_data'])
            elif len(command) == 2:
                if command[1] in preference_list:
                    preference_list[command[1]]['blocked'] = False
                    context.bot.send_message(chat_id=update.message.chat_id,
                            text=LANG['unban_user']
                            % (preference_list[command[1]]['name'],
                            command[1]),
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
                    context.bot.send_message(chat_id=int(command[1]),text=LANG['be_unbanned'])
                else:
                    context.bot.send_message(chat_id=update.message.chat_id,text=LANG['user_not_found'])
            else:
                context.bot.send_message(chat_id=update.message.chat_id,text=LANG['reply_or_enter_id'])
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=LANG['not_an_admin'])
    elif command[0] == 'bad_command' : #测试发送错误信息
        if update.message.from_user.id == CONFIG['Admin'] \
            and update.message.chat_id == CONFIG['Admin']:
            context.bot.wrong_method_name()
    else: # 指令不存在
        context.bot.send_message(chat_id=update.message.chat_id, text=LANG['nonexistent_command'])

# 添加Handle

dispatcher.add_handler(telegram.ext.MessageHandler(telegram.ext.Filters.all
                       & telegram.ext.Filters.chat_type.private
                       & ~telegram.ext.Filters.command
                       & ~telegram.ext.Filters.status_update,
                       process_msg))  # 处理消息

dispatcher.add_handler(telegram.ext.MessageHandler(telegram.ext.Filters.command
                       & telegram.ext.Filters.chat_type.private, process_command))  # 处理指令

dispatcher.add_error_handler(error_handler, run_async=False)

updater.start_polling()  # 开始轮询
print('Started')
updater.idle()
print('Stopping...')
save_data()  # 保存消息数据
save_preference()  # 保存用户资料与设置
print('Data saved.')
print('Stopped.')
