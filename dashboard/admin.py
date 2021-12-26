from django.contrib import admin
from .models import  Course,Order,SearchRecord

admin.site.register(Course)
admin.site.register(Order)
admin.site.register(SearchRecord)