 
from django.contrib import admin
from .models import (
    Category,
    ServiceRequest,
    RequestComment,
    RequestHistory,
)

admin.site.register(Category)
admin.site.register(ServiceRequest)
admin.site.register(RequestComment)
admin.site.register(RequestHistory)