from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, ButtonsTemplate, PostbackEvent ,PostbackAction, TemplateSendMessage, JoinEvent
)

app = Flask(__name__)

line_bot_api = LineBotApi('your channel access token')
handler = WebhookHandler('your channel seacret')

@app.route("/")
def test():
    return "OK"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


group_box = {}
@handler.add(JoinEvent)
def join_event(event):
    groupId = event.source.group_id
    group_summary = line_bot_api.get_group_summary(groupId)
    
    if not groupId in group_box:
        group_box[groupId] = {}
    group_box[groupId]['users_profile'] = {}
    group_box[groupId]['user_check'] = {}

    if not groupId in group_box[groupId]:
        group_box[groupId]['groupName'] = group_summary.group_name

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(
            text=f"招待ありがとう！\n{group_box[groupId]['groupName']}への参加を確認しました。\n\n[利用目的]\nこのボットは報連相がままならないチームの補助ツールとして使うことを目的としています。これを使えばグループに既読を付けることなく重要なチャットを確認することができます。\n\n[※注意]\n機能を利用するには友達登録をしてください。\n「コマンド」と打てば機能を確認できます。"
        )
    )
    

users = {}
text_box = {}
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    text_message = event.message.text
    try:
        groupId = event.source.group_id
        group_name = line_bot_api.get_group_summary(groupId).group_name
    except: 
        pass
    userId = event.source.user_id

    user_profile = line_bot_api.get_profile(userId)
    user_name = user_profile.display_name

    if not userId in text_box:
        text_box[userId] = []
    if text_message != "よろしく":
        text_box[userId].append(text_message)
    if len(text_box[userId]) > 1:
        text_box[userId].pop(0)

    # 「よろしく」の直前のチャットを連絡する
    if text_message == "よろしく":
        try:
            detail_text = text_box[userId][0]
            buttons_template = ButtonsTemplate(
                title='確認したらボタンを押してね', text=detail_text, actions=[
                PostbackAction(label="確認しました", data="check-txt")
                ]
            )

            # チェックリストを初期化する
            group_box[groupId]['user_check']['userIds'] = []
            group_box[groupId]['user_check']['user_name'] = []

            template_message = TemplateSendMessage(alt_text="スマートフォンからボタンを押してね", template=buttons_template)
            line_bot_api.reply_message(event.reply_token, template_message)
            if group_box[groupId]['users_profile']:
                for user in group_box[groupId]['users_profile']:
                        line_bot_api.push_message(
                            user, 
                            TextSendMessage(text=f"{group_name}から{user_name}より\n\n{detail_text}")
                        )
                        # buttons_template = ButtonsTemplate(
                        #     title=f"{group_name}から{user_name}より", text=detail_text, actions=[
                        #     PostbackAction(label="確認しました", data="check-txt")
                        #     ]
                        # )
                        # template_message = TemplateSendMessage(alt_text="スマートフォンからボタンを押してね", template=buttons_template)
                        # line_bot_api.push_message(user, template_message)
            
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="この機能はグループラインでしか利用できません。"))
    
    # コマンドを表示する
    if text_message == "コマンド":
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="〇よろしく:\n直前のチャットを個別に送信\n〇点呼:\n確認ボタンを押した人を表示\n〇登録:\n個別チャットへの連絡を登録\n〇解除\n〇撤退:退出")
        )


    # 確認ボタンを押した人を確認する
    if text_message == "点呼":
        try:
            number = line_bot_api.get_group_members_count(groupId)
            rest_number = number - len(group_box[groupId]['user_check']['user_name'])
            name_list = ', '.join(group_box[groupId]['user_check']['user_name'])
            if name_list == '':
                line_bot_api.reply_message(
                        event.reply_token, 
                        TextSendMessage(text="誰の連絡も確認できません。")
                    )
            elif rest_number == 0:
                line_bot_api.reply_message(
                            event.reply_token, 
                            TextSendMessage(text="全員の確認が取れました。ご協力ありがとうございました。")
                        )
            else:
                line_bot_api.reply_message(
                            event.reply_token, 
                            TextSendMessage(text=f"{name_list}の連絡を確認。残り{rest_number}人です。")
                        )
        except:
            if event.source.group_id:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="まだお知らせは来てません。"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="この機能はグループラインでしか利用できません。"))
    
    # 個別チャットへ連絡したい人を登録する
    if text_message == "登録":
        try:
            groupId = event.source.group_id
            buttons_template = ButtonsTemplate(
                title='個別チャットへの連絡', text='登録ボタンを押した方のみ、今後このグループの重要なチャットを個別チャットに送ります。', actions=[
                PostbackAction(label="登録", data="register-chat")
                ]
            )
            template_message = TemplateSendMessage(alt_text="スマートフォンからボタンを押してね。", template=buttons_template)
            line_bot_api.reply_message(event.reply_token, template_message)
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="この機能はグループラインでしか利用できません。"))

    # 個別チャットへの連絡を解除する
    if text_message == "解除":
        try:
            groupId = event.source.group_id
            buttons_template = ButtonsTemplate(
                title='解除ボタン', text='登録を解除します', actions=[
                PostbackAction(label="解除", data="cancel-chat")
                ]
            )
            template_message = TemplateSendMessage(alt_text="スマートフォンからボタンを押してね", template=buttons_template)
            line_bot_api.reply_message(event.reply_token, template_message)
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="この機能はグループラインでしか利用できません。"))

    # 退出処理
    if text_message == "撤退":
        try:
            #グループトークからの退出処理
            group_name = line_bot_api.get_group_summary(groupId).group_name

            line_bot_api.reply_message(event.reply_token, TextSendMessage(f"{group_name}の安全を確認。即刻離脱します。"))
            group_box.pop(groupId)
            line_bot_api.leave_group(groupId)

        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="この機能はグループラインでしか利用できません。"))
        
rest_number = 1
@handler.add(PostbackEvent)
def handle_postback(event):
    if event.postback.data == "check-txt":

        userId = event.source.user_id
        user_profile = line_bot_api.get_profile(userId)
        groupId = event.source.group_id

        # もしuser_checkにuserが入ってないなら
        if not userId in group_box[groupId]['user_check']['userIds']:
            group_box[groupId]['user_check']['userIds'].append(userId)
            group_box[groupId]['user_check']['user_name'].append(user_profile.display_name)

            # 最後なら最後ですと通知する
            number = line_bot_api.get_group_members_count(groupId)
            rest_number = number - len(group_box[groupId]['user_check']['userIds'])
            if rest_number == 0:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"{user_profile.display_name}、確認しました。\n\nこれで全員の確認が取れました。ご協力ありがとうございました。")
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"{user_profile.display_name}、確認しました。")
                )
        else: 
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"{user_profile.display_name}の確認はすでに取れてます。")
            )
            

    if event.postback.data == 'register-chat':
        # 後で消す
        # groupId = event.source.group_id
        # group_box[groupId] = {}
        # group_box[groupId]['users_profile'] = {}
        # group_box[groupId]['user_check'] = {}

        if event.source.group_id:
            userId = event.source.user_id
            groupId = event.source.group_id
            user_profile = line_bot_api.get_profile(userId)

            if not userId in group_box[groupId]['users_profile']:
                group_box[groupId]['users_profile'][userId] = user_profile.display_name

                line_bot_api.reply_message(
                    event.reply_token, 
                    TextSendMessage(text=f"{group_box[groupId]['users_profile'][userId]}の登録を確認しました。")
                )
            else: 
                line_bot_api.reply_message(
                    event.reply_token, 
                    TextSendMessage(text=f"{group_box[groupId]['users_profile'][userId]}はすでに登録されています。")
                )

    if event.postback.data == 'cancel-chat':
        groupId = event.source.group_id
        if event.source.group_id:
            userId = event.source.user_id
            user_profile = line_bot_api.get_profile(userId)
            
            cancel_user_name = user_profile.display_name
            if userId in group_box[groupId]['users_profile']:
                line_bot_api.reply_message(
                    event.reply_token, 
                    TextSendMessage(text=f"{cancel_user_name}の登録を解除しました。")
                )
                group_box[groupId]['users_profile'].pop(userId)

            else:
                line_bot_api.reply_message(
                    event.reply_token, 
                    TextSendMessage(text=f"{cancel_user_name}は登録してません。")
                )
            

if __name__ == "__main__":
    app.run()