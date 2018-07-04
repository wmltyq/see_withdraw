import os
import re
import time
import itchat
from itchat.content import *

# 说明：可以撤回的有文字、语音、视频、图片、位置、名片、分享、附件
msg_dict = {}

# 文件存储临时目录
rev_tmp_dir = 'RevTmp/'
# 是否删除缓存文件，默认删除
del_tmp_file = True

if not os.path.exists(rev_tmp_dir):
    os.mkdir(rev_tmp_dir)


# 将接收到的信息存放在字典中，当接收到信息时对字典中超时的信息进行清理，不接受不具有撤回功能的信息
@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO])
def handler_receive_msg(msg):
    # 获取的是本地时间戳并格式化本地时间戳：2018-07-04 14:55:13
    msg_time_rec = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    # 消息ID
    msg_id = msg['MsgId']
    # 消息时间
    # msg_time = msg['CreateTime']
    # 消息发送人昵称，这里也可以使用RemarkiName备注，但是自己或者没有备注的人为None
    if msg['ToUserName'] != 'filehelper':
        remark_name = msg['User']['RemarkName']
    else:
        remark_name = 'filehelper'
    # 如果备注不为空就取备注值
    if remark_name != '':
        msg_from = remark_name
    else:
        msg_from = msg['User']['NickName']
    # 消息内容
    msg_content = None
    # 分享的链接
    msg_share_url = None

    if msg['Type'] == 'Text' or msg['Type'] == 'Friends':
        msg_content = msg['Text']
    elif msg['Type'] == 'Recording' or msg['Type'] == 'Attachment' or msg['Type'] == 'Video' or msg[
        'Type'] == 'Picture':
        msg_content = msg['FileName']
        # 保存文件
        msg['Text'](rev_tmp_dir + msg['FileName'])
    elif msg['Type'] == 'Card':
        msg_content = '「' + msg['RecommendInfo']['NickName'] + '」的名片'
    elif msg['Type'] == 'Map':
        x, y, location = re.search('<location x="(.*?) y="(.*?)".*label="(.*?)".*', msg['OriContent']).group(1, 2, 3)
        if location is None:
            msg_content = '纬度：' + x + ' 经度：' + y
        else:
            msg_content = location
    elif msg['Type'] == 'Sharing':
        msg_content = msg['Text']
        msg_share_url = msg['Url']

    # 更新字典
    msg_dict.update({
        msg_id: {
            'msg_from': msg_from,
            # 'msg_time': msg_time,
            'msg_time_rec': msg_time_rec,
            'msg_type': msg['Type'],
            'msg_content': msg_content,
            'msg_share_url': msg_share_url
        }
    })


@itchat.msg_register([NOTE])
def send_msg_helper(msg):
    if re.search('\<\!\[CDATA\[.*撤回了一条消息\]\]\>', msg['Content']) is not None:
        # 保存消息的id
        old_msg_id = re.search('<msgid>(.*?)</msgid>', msg['Content']).group(1)
        old_msg = msg_dict.get(old_msg_id, {})
        msg_body = old_msg.get('msg_time_rec') + '\n"' + old_msg.get('msg_from') + '"撤回了「' + old_msg.get(
            'msg_type') + '」消息：\n' + old_msg.get('msg_content')
        # 如果是分享存在链接
        if old_msg['msg_type'] == 'Sharing':
            msg_body += old_msg.get('msg_share_url')

        # 将撤回消息发送到文件助手
        itchat.send(msg_body, toUserName='filehelper')

        # 有文件的话也要将文件发送回去
        if old_msg['msg_type'] == 'Picture' or old_msg['msg_type'] == 'Recording' or old_msg['msg_type'] == 'Video' or \
                old_msg['msg_type'] == 'Attachment':
            # 发送的图片以微信网页版的形式呈现
            file = '@fil@%s' % (rev_tmp_dir + old_msg['msg_content'])
            itchat.send(msg=file, toUserName='filehelper')
            if del_tmp_file:
                os.remove(rev_tmp_dir + old_msg['msg_content'])

        # 将撤回的消息保存到本地文件
        with open(rev_tmp_dir + 'rev_tmp.txt', 'a', encoding='utf-8') as file:
            file.write(msg_body + '\n\n')

        # 删除字典旧消息
        msg_dict.pop(old_msg_id)


if __name__ == '__main__':
    itchat.auto_login(hotReload=True)
    itchat.run()
