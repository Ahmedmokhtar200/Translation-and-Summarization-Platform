from django.urls import path
from . import views

urlpatterns = [
    path('summarize', views.summarized_text), # post method
    path('status/<int:text_id>', views.get_status), # get method
    path('home', views.home),
]
