"""
爬虫管理视图 - 提供前端界面触发和管理爬虫任务
"""
import json
import subprocess
import sys
import os
import threading
from datetime import datetime

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# 爬虫任务状态存储（简易内存版，生产环境应使用 Redis/数据库）
crawler_tasks = {}


def crawler_index(request):
    """爬虫管理页面"""
    return render(request, 'crawler/index.html')


@csrf_exempt
@require_POST
def crawler_start(request):
    """启动爬虫任务"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的请求数据'}, status=400)

    city = data.get('city', '北京')
    pages = data.get('pages', 3)

    # 检查是否有正在运行的任务
    for task_id, task in crawler_tasks.items():
        if task['status'] == 'running' and task['city'] == city:
            return JsonResponse({'error': f'{city}的爬虫任务正在运行中', 'task_id': task_id}, status=409)

    # 创建任务
    task_id = f"{city}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    crawler_tasks[task_id] = {
        'task_id': task_id,
        'city': city,
        'pages': pages,
        'status': 'running',
        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'finished_at': None,
        'output': '',
        'error': '',
    }

    # 在后台线程中运行爬虫
    thread = threading.Thread(target=_run_crawler, args=(task_id, city, pages))
    thread.daemon = True
    thread.start()

    return JsonResponse({'task_id': task_id, 'message': f'爬虫任务已启动: {city}, {pages}页'})


def _run_crawler(task_id, city, pages):
    """后台运行爬虫进程"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    crawler_dir = os.path.join(project_root, 'crawler')

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'scrapy', 'crawl', 'lianjia',
             '-a', f'city={city}', '-a', f'pages={pages}'],
            cwd=crawler_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        crawler_tasks[task_id]['output'] = result.stdout[-2000:] if result.stdout else ''
        crawler_tasks[task_id]['error'] = result.stderr[-2000:] if result.stderr else ''
        crawler_tasks[task_id]['status'] = 'completed' if result.returncode == 0 else 'failed'
    except subprocess.TimeoutExpired:
        crawler_tasks[task_id]['status'] = 'timeout'
        crawler_tasks[task_id]['error'] = '爬虫运行超时（5分钟）'
    except Exception as e:
        crawler_tasks[task_id]['status'] = 'failed'
        crawler_tasks[task_id]['error'] = str(e)
    finally:
        crawler_tasks[task_id]['finished_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def crawler_status(request, task_id):
    """查询爬虫任务状态"""
    task = crawler_tasks.get(task_id)
    if not task:
        return JsonResponse({'error': '任务不存在'}, status=404)
    return JsonResponse(task)


def crawler_list(request):
    """获取所有爬虫任务列表"""
    tasks = sorted(crawler_tasks.values(), key=lambda x: x['started_at'], reverse=True)
    return JsonResponse({'tasks': tasks[:20]})
