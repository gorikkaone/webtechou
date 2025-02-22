from django.urls import path,include
from .views import create_event as create_sample_event  # サンプルイベント用に別名でインポート
from . import views
from .views import RegisterView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import UserProfileView
from .views import study_plan_form, mypage
from .views import StudyPlanViewSet, study_plan_form, study_plan_edit, study_plan_delete, study_plan_copy, study_plan_list
from .views import past_exam_list, past_exam_create, past_exam_form, past_exam_edit, past_exam_delete, past_exam_copy
from .views import StudyRecordViewSet
from django.contrib.auth import views as auth_views

 # viewsモジュール全体もインポート
router = DefaultRouter()
router.register(r'study-plans-api', StudyPlanViewSet, basename='studyplan')
router.register(r'study-records', StudyRecordViewSet)


urlpatterns = [
    path('init/', views.google_calendar_init, name='google_calendar_init'),
    path('redirect/', views.google_calendar_redirect, name='google_calendar_redirect'),
    path('events/', views.list_events, name='list_events'),
    path('create/', views.create_event, name='create_event'),# フォーム経由のイベント作成
    path('create-sample-event/', create_sample_event, name='create_sample_event'),# サンプルイベント作成
    path('add-study-plan/', views.add_study_plan, name='add_study_plan'),
    path('api/register/', RegisterView.as_view(), name='register'), # JWTのログインAPI
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # トークンの更新
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # ログインユーザー情報取得
    path('user/', UserProfileView.as_view(), name='user_profile'),
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('', include(router.urls)),
    path("study-plan-form/", study_plan_form, name="study_plan_form"),
    path("api/", include(router.urls)),
    path('study-plan-edit/<int:pk>/', study_plan_edit, name='study_plan_edit'),
    path('study-plan-delete/<int:pk>/', study_plan_delete, name='study_plan_delete'),
    path('study-plan-copy/<int:pk>/', study_plan_copy, name='study_plan_copy'),
    path('past-exams/', past_exam_list, name='past_exam_list'),
    path('past-exams/create/', past_exam_create, name='past_exam_create'),
    path('past-exams/form/', past_exam_form, name='past_exam_form'),  # 🔹 フォーム用のURLを追加
    #path('study-plans/<int:child_id>/', StudyPlanViewSet.as_view({'get':'list'}),name='study-plans'),
    #path('study-plans-by-child/<int:child_id>/', study_plan_list, name='study_plan_list'),
    #path('study-plans/<int:child_id>/', study_plan_list, name='study_plan_list'),
    path('past-exams/<int:child_id>/', past_exam_list, name='past_exam_list'),
    path('study-plans/<int:child_id>/', study_plan_list, name='study_plan_list'),
    path('past-exams/<int:exam_id>/edit/', past_exam_edit, name='past_exam_edit'),
    path('past-exams/<int:exam_id>/delete/', past_exam_delete, name='past_exam_delete'),
    path('past-exams/<int:exam_id>/copy/', past_exam_copy, name='past_exam_copy'),
    path('past-exams/<int:child_id>/add/', views.past_exam_form, name='past_exam_add'),
    path("register-child/", views.register_child, name="register_child"),
    path('mypage/', mypage, name='mypage'),
    path(
    "login/",
    auth_views.LoginView.as_view(template_name="login.html", next_page="mypage"),
    name="login"
),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("children/", views.child_list, name="child_list"),
    path("children/<int:child_id>/edit/", views.edit_child, name="edit_child"),  # 編集用
    path("children/<int:child_id>/delete/", views.delete_child, name="delete_child"),
    path('child/<int:child_id>/', views.child_detail, name='child_detail'),
    path('exam-records/<int:child_id>/', views.exam_record_list, name='exam_record_list'),
    path('child/<int:child_id>/edit/', views.child_edit, name='child_edit'),
    path('shiboukou/<int:shiboukou_id>/edit/', views.edit_shiboukou, name='edit_shiboukou'),
    path('shiboukou/<int:shiboukou_id>/delete/', views.delete_shiboukou, name='delete_shiboukou'),
    path('child/<int:child_id>/shiboukou/add/', views.add_shiboukou, name='add_shiboukou'),
    path('register/', views.register, name='register'),



 # 削除用
]
