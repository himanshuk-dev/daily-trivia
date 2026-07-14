from django.urls import path

from .views import (
    leaderboard_view,
    master_cycle_generate_trivia,
    master_cycle_list_create,
    trivia_session_answers,
    trivia_session_evaluate,
    trivia_session_publish,
    trivia_session_retrieve,
    user_delete,
    user_list_create,
)


urlpatterns = [
    path('users/', user_list_create, name='user-list-create'),
    path('users/<int:pk>/', user_delete, name='user-delete'),
    path('leaderboard/', leaderboard_view, name='leaderboard'),
    path('master-cycles/', master_cycle_list_create, name='master-cycle-list-create'),
    path('master-cycles/<int:pk>/generate-trivia/', master_cycle_generate_trivia, name='master-cycle-generate-trivia'),
    path('trivia-sessions/<int:pk>/', trivia_session_retrieve, name='trivia-session-retrieve'),
    path('trivia-sessions/<int:pk>/publish/', trivia_session_publish, name='trivia-session-publish'),
    path('trivia-sessions/<int:pk>/evaluate/', trivia_session_evaluate, name='trivia-session-evaluate'),
    path('trivia-sessions/<int:pk>/answers/', trivia_session_answers, name='trivia-session-answers'),
]
