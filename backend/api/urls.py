from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health),
    path("posts/", views.posts),
    path("youtube/status/", views.youtube_status),
    path("youtube/sync/", views.youtube_sync),
    path("instagram/status/", views.instagram_status),
    path("instagram/sync/", views.instagram_sync),
    path("analytics/", views.analytics),
    path("comments/<int:pk>/report/", views.report_comment),
    path("posts/<int:pk>/comments/", views.post_comment),
    path("moderate/", views.moderate),
    path("moderate-batch/", views.moderate_batch),
    path("history/", views.history),
    path("stats/", views.stats),
    path("incidents/", views.incidents),
    path("incidents/<int:pk>/review/", views.review_incident),
    path("incidents/<int:pk>/report/", views.incident_report),
]
