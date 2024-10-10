from datetime import datetime
from flask import render_template, request, Flask, jsonify, Response
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
import qianfan
import json
import os

@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)


# 设置环境变量
os.environ["QIANFAN_ACCESS_KEY"] = "901c37dc426b4c6fbd4d60c22ef939f1"
os.environ["QIANFAN_SECRET_KEY"] = "bc5650a148c94378a52eee38491f7556"

chat_comp = qianfan.ChatCompletion()

@app.route('/api/generate-article', methods=['POST'])
def generate_article():
    data = request.json
    theme = data.get('theme', '')
    requirement = data.get('requirement', '')

    print(f"Received request - Theme: {theme}, Requirement: {requirement}")

    if not theme:
        return jsonify({"success": False, "message": "主题不能为空"}), 400

    prompt = f"主题：{theme}\n要求：{requirement}\n请根据以上主题和要求生成一篇文章。"

    def generate():
        try:
            resp = chat_comp.do(model="ERNIE-Speed-8K", messages=[{
                "role": "user",
                "content": prompt
            }], stream=True)

            full_article = ""
            for chunk in resp:
                print(f"Received chunk: {chunk}")
                if 'result' in chunk:
                    content = chunk['result']
                    full_article += content
                    yield f"data: {json.dumps({'content': content})}\n"
                
                if chunk.get('is_end', False):
                    if full_article.strip():
                        print(f"Full generated article: {full_article}")
                        yield f"data: {json.dumps({'end': True, 'full_article': full_article})}\n"
                    else:
                        print("Warning: Generated article is empty")
                        yield f"data: {json.dumps({'error': '生成的文章为空'})}\n"

        except Exception as e:
            print(f"Error: {str(e)}")
            yield f"data: {json.dumps({'error': f'生成文章失败: {str(e)}'})}\n"

    return Response(generate(), content_type='text/event-stream')