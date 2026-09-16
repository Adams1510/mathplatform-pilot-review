from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("topics/", views.topics, name="topics"),
    path("learn/m1/integers/", views.integer_topic_entry, name="integer-topic"),
    path(
        "learn/m1/integers/check/",
        views.controlled_activity,
        {"activity": "check"},
        name="integer-check",
    ),
    path(
        "learn/m1/integers/lessons/1/",
        views.controlled_activity,
        {"activity": "lesson-1"},
        name="integer-lesson-1",
    ),
    path("help/accessibility/", views.accessibility_help, name="accessibility-help"),
]
