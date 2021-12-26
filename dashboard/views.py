from django.shortcuts import render
from django.http import JsonResponse
from .models import Order,Course,SearchRecord
import json
import pytz
from django.core.paginator import Paginator
from datetime import datetime
from django_pandas.io import read_frame
from  django.core.cache import cache
import pandas as pd
import uuid
from django_q.tasks import async_task


from . import data_analysis
data_analysis_function_map = {
'platform_pie': data_analysis.get_platform_pie,
'product_line_income_bar': data_analysis.get_product_line_income_bar,
'daily_income_line': data_analysis.get_daily_income_line,
'total_income': data_analysis.get_total_income,
'provinces_sales_map': data_analysis.get_provinces_sales_map,
}

PAYMENT_PENDING = 'PE'
PAYMENT_SUCCESS = 'SU'
PAYMENT_CANCELLED = 'CA'
PAYMENT_OVERDUE = 'OV'
PAYMENT_REFUND = 'RE'
STATUS_TYPE_CHOICES = dict([
        (PAYMENT_PENDING, '未支付'),
        (PAYMENT_SUCCESS, '支付成功'),
        (PAYMENT_CANCELLED, '取消'),
        (PAYMENT_OVERDUE, '过期'),
        (PAYMENT_REFUND, '退款')
        ])

op_to_lookup = {
    'equal': 'exact',
    'not_equal': 'exact',
    'like': 'contains',
    'not_like': 'contains',
    'starts_with': 'startswith',
    'ends_with': 'endswith',
    'less': 'lt',
    'less_or_equal': 'lte',
    'greater': 'gt',
    'greater_or_equal': 'gte',
    'between': 'range',
    'not_between': 'range',
    'select_equals': 'exact',
    'select_not_equals': 'exact',
    'select_any_in': 'in',
    'select_not_any_in': 'in',
    }



def analyse_order_conditions(conditions):
    final_query = None
    for child in conditions['children']:
        if 'children' in child:
            child_query = analyse_order_conditions(child)
        else:
            model, field = child['left']['field'].split('.')
            lookup = op_to_lookup[child['op']]
            right = child['right']
            if field.endswith('time'):
                if isinstance(right, list):
                    start_dt, end_dt = right
                    start_dt = datetime.strptime(start_dt, '%Y-%m-%dT%H:%M:%S%z')
                    end_dt = datetime.strptime(end_dt, '%Y-%m-%dT%H:%M:%S%z')
                    right = (start_dt, end_dt)
                else:
                    right = datetime.strptime(right, '%Y-%m-%dT%H:%M:%S%z')

            if model == 'order':
                params = {f'{field}__{lookup}': right}
            else:
                params = {f'{model}__{field}__{lookup}': right}
            if 'not_' in child['op']:
                child_query = Order.objects.exclude(**params)
            else:
                child_query = Order.objects.filter(**params)

            if final_query is None:
                final_query = child_query
            elif conditions['conjunction'] == 'and':
                final_query = final_query & child_query
            else:
                final_query = final_query | child_query

    return final_query





def index(request):
    order_fields=[{"name":field.name,"label":field.verbose_name} for field in Order._meta.fields]
    return render(request, 'dashboard/index.html',{'order_fields':order_fields})

def order_filter_api(request):
    data = json.loads(request.body.decode())
    page = data.get('page', 0)
    per_page = data.get('perPage', 10)
    conditions = data.get('conditions', {})
    orders = analyse_order_conditions(conditions) if len(conditions) > 0 else Order.objects.all()
    orders = orders.order_by('id')
    #orders = Order.objects.all().order_by('id')
    paginator = Paginator(orders, per_page)
    page_obj = paginator.get_page(page)
    items = list(page_obj.object_list.values())
    for item in items:
        item['course'] = Course.objects.get(id=item['course_id']).title
        item['create_time'] = item['create_time'].astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
        if item['pay_time'] is not None:
            item['pay_time'] = item['pay_time'].astimezone(pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
        item['status'] = STATUS_TYPE_CHOICES[item['status']]
        
    data = {
        "status": 0,
        "msg": "ok",
        "data": {
            "total": orders.count(),
            "items": items
        }
    }
    if len(conditions) > 0:
        #search_record = SearchRecord.objects.create(conditions=json.dumps(conditions))
        #search_record.objs.add(*orders)
        #data["data"]["sid"] = search_record.id
        sid=str(uuid.uuid4())
        data["data"]["sid"] =sid
        #orders = SearchRecord.objects.get(id=sid).objs.all()
        orders_df = read_frame(orders, coerce_float=True)
        orders_json = orders_df.to_json(orient='table')
        cache.set(sid, orders_json, 600)
    return JsonResponse(data)

def order_data_vis_api(request):
    data_type = request.GET.get('type', '')
    data = {
        "status": 0,
        "msg": "ok",
        "data": {}
    }
    sid = request.GET.get('sid', '')
    if len(sid) == 0:
        return JsonResponse(data)
    cache_data = cache.get(sid)
    orders_df = pd.read_json(cache_data, orient='table')
    #orders = SearchRecord.objects.get(id=sid).objs.all()
    #orders_df = read_frame(orders, coerce_float=True)
    data_analysis_function = data_analysis_function_map[data_type]
    data['data'] = data_analysis_function(orders_df)
    return JsonResponse(data)

def order_send_email_api(request):
    sid = request.GET.get('sid')
    data = json.loads(request.body.decode())
    email = data.get('email')
    email_data = {
        'sid': sid,
        'email': email,
        'subject': '您的订单数据表格已生成'
    }
    async_task('dashboard.tasks.send_email', email_data)
    data = {
    "status": 0,
    "msg": "邮件发送请求已经开始处理",
    "data": {
    }
    }
    return JsonResponse(data)

def spider_ifeng_api(request):
    result = cache.get('ifeng-spider', [])
    data = {
    "status": 0,
    "msg": "ok",
    "data": {
    "total": len(result),
    "items": result
    }
    }
    return JsonResponse(data)