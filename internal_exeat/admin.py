from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import InternalExeat

@admin.register(InternalExeat)
class Internal(ModelAdmin):
    pass
# Register your models here.
