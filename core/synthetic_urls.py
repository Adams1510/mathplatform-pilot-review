from django.urls import path

from . import synthetic_views

app_name = "synthetic"
urlpatterns = [
    path("state/", synthetic_views.synthetic_state, name="state"),
    path("state/save/", synthetic_views.save_state, name="save-state"),
    path("math-accessibility/", synthetic_views.synthetic_math_accessibility, name="math-probe"),
]
