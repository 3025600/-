
import requests
import requests.adapters
import base64
import re
import json
from requests.structures import CaseInsensitiveDict

# 从控制台输入token
USER_TOKEN = input("请输入你的token: ")



def getPrettyJSON(obj):
    try:
        if type(obj) == str:
            return json.dumps(json.loads(obj), ensure_ascii=False, indent=2)
        elif type(obj) == bytes:
            return json.dumps(json.loads(obj.decode()), ensure_ascii=False, indent=2)
        elif type(obj) == CaseInsensitiveDict:
            return json.dumps(dict(obj), ensure_ascii=False, indent=2)
        else:
            return json.dumps(obj, ensure_ascii=False, indent=2)
    except:
        return obj

def printPrettyJSON(obj):
    print(getPrettyJSON(obj))

# 解码响应中 data 字段的里面的 base64 数据
def decodeData(data: str):
    try:
        return json.loads(base64.b64decode(re.search('ey.*', data).group().encode()).decode())
    except:
        try:
            return decodeData(re.search('ey(.*)', data).group(1))
        except:
            return data

# 网络请求记录，用于 debug
class vocabgoAdapter(requests.adapters.HTTPAdapter):
    def send(self, request: requests.PreparedRequest, **kwargs):
        print(f"\n-> {request.method} {request.url}\n{getPrettyJSON(request.body)}")
        response = super().send(request, **kwargs)
        print(f"<- {response.status_code}\n{getPrettyJSON(decodeData(response.json()['data']))}")
        return response

session = requests.Session()
session.headers['UserToken'] = USER_TOKEN
session.mount('http://', vocabgoAdapter())
session.mount('https://', vocabgoAdapter())

# 获取全部任务
def getPageTask():
    r = session.post('https://app.vocabgo.com/studentv1/api/Student/ClassTask/PageTask', json={
        "search_type": "1",  # 进行中
        "page_count": 1,
        "page_size": 30,
    }).json()
    return r['data']

# 获取所有词
def getChoseWordList(task_id: int):
    r = session.get('https://app.vocabgo.com/studentv1/api/Student/ClassTask/ChoseWordList', params={
        'task_id': task_id,
        'task_type': 1,
    }).json()
    return r['data']

# 选择全部词
def submitChoseWord_All(task_id: int):
    word_list = getChoseWordList(task_id)['word_list']
    r = session.post('https://app.vocabgo.com/studentv1/api/Student/ClassTask/SubmitChoseWord', json={
        "task_id": task_id,
        "word_map": {
            f"{word_list[0]['course_id']}:{word_list[0]['list_id']}": [w['word'] for w in word_list]
        },
        "chose_err_item": 1,
        "reset_chose_words": 1,  # 重新选词（放弃现有进度，重新练习）
    }).json()
    return r['data']

# 进入练习
def startAnswer(task_id: int, release_id: int):
    r = session.get('https://app.vocabgo.com/studentv1/api/Student/ClassTask/StartAnswer', params={
        'task_id': task_id,
        'task_type': 1,
        'release_id': release_id,
    }).json()
    return decodeData(r['data'])

# 验证答案
def verifyAnswer(topic_code: str, answer):
    r = session.post('https://app.vocabgo.com/studentv1/api/Student/ClassTask/VerifyAnswer', json={
        "answer": answer,
        "topic_code": topic_code,
    }).json()
    return decodeData(r['data'])

# 提交答案
def submitAnswerAndSave(topic_code: str):
    r = session.post('https://app.vocabgo.com/studentv1/api/Student/ClassTask/SubmitAnswerAndSave', json={
        "topic_code": topic_code,
        "time_spent": 10000,
    }).json()
    return decodeData(r['data'])

# 自动刷练习
def start(task_id, release_id):
    topic = startAnswer(task_id, release_id)
    while 'topic_mode' in topic:
        if (topic['topic_mode'] == 0):
            topic = submitAnswerAndSave(topic['topic_code'])
            continue

        if (topic['topic_mode'] == 31):
            answer = []
            for i in range(len(topic['options'])):
                verify = verifyAnswer(topic['topic_code'], i)
                if verify['answer_result'] == 1:
                    answer.append(i)
            for i in answer:
                verify = verifyAnswer(verify['topic_code'], i)
        else:
            verify = verifyAnswer(topic['topic_code'], '')
            verify = verifyAnswer(verify['topic_code'], '')
            answer = verify['answer_corrects'][0]
            if (topic['topic_mode'] == 32):
                verify = verifyAnswer(topic['topic_code'], ','.join(answer.replace('...', '').replace('…', '').strip().split()))
            else:
                verify = verifyAnswer(topic['topic_code'], answer)
        if verify['answer_result'] != 1:
            input('获取答案错误, 请按回车跳过该题\n可将上下文发送给开发者，以便修复bug')
        topic = submitAnswerAndSave(verify['topic_code'])

    print(f"积分：+{topic.get('integral')}\n能量包：+{topic.get('energy_pack')}")

if __name__ == '__main__':
    tasks = getPageTask()
    if not tasks:
        print('获取班级任务失败！请检查 UserToken')
        input()
        exit()

    for i in range(len(tasks['records'])):
        task = tasks['records'][i]
        print(f"{i}: {task['task_name']}  进度{task['progress']}%  得分{task['score']}")

    selectedTask = tasks['records'][int(input('选择任务：'))]

    submitChoseWord_All(selectedTask['task_id'])
    start(selectedTask['task_id'], selectedTask['release_id'])

    input()
