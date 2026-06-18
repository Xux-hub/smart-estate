from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


def crawler_index(request):
    return render(request, 'crawler/disabled.html')


@csrf_exempt
@require_POST
def crawler_start(request):
    return JsonResponse(
        {
            'error': '爬虫功能已停用。项目现在直接读取 MySQL 数据库中的 house_info 表。',
        },
        status=410,
    )


def crawler_status(request, task_id):
    return JsonResponse({'error': '爬虫功能已停用，暂无任务状态。'}, status=410)


def crawler_list(request):
    return JsonResponse({'tasks': [], 'message': '爬虫功能已停用。'})
