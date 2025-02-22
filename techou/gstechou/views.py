from django.shortcuts import render, redirect, HttpResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.utils import timezone
from django.http import HttpResponse
from django.conf import settings
from google.auth.transport.requests import Request
from datetime import datetime
from django.utils.timezone import make_aware
from dateutil import parser
from .models import StudyPlan
from .forms import EventForm
from .models import School
from .serializers import RegisterSerializer, UserSerializer
from rest_framework.views import APIView
from django.contrib.auth import get_user_model  # ← インポートを追加
from rest_framework import generics, permissions
from .models import CustomUser
from .serializers import CustomUserSerializer,StudyRecordSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import StudyPlanSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import render, redirect, get_object_or_404
from .forms import StudyPlanForm, ShiboukouEditForm
from .models import StudyPlan
from django.contrib.auth.decorators import login_required
from .models import Subject
from .forms import PastExamForm, ExamScheduleForm,ExamRecordForm, ChildForm, ShiboukouForm, CustomUserCreationForm
from .models import PastExam, Child, ExamSchedule, ExamRecord, StudyRecord, Shiboukou



import json
import urllib.parse
import pprint
import os
import uuid
import logging


logger = logging.getLogger(__name__)



os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def redirect_handler(request):
    state_from_google = request.GET.get('state')
    state_from_session = request.session.get('state')

    # セッションが切れているか、stateが一致しない場合
    if not state_from_session or state_from_google != state_from_session:
        print("Session expired or state mismatch detected. Redirecting to re-authenticate.")
        return HttpResponseRedirect(reverse('google_calendar_init'))

    # 正常にstateが一致した場合
    return HttpResponse("State validated successfully")

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)  # ✅ ここを修正
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()  # ✅ ここも修正
    return render(request, 'register.html', {'form': form})



@login_required
def mypage(request):
    children = request.user.children.all()
    return render(request, "mypage.html", {"children": children})

@login_required
def child_detail(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)
    shiboukous = child.shiboukou_list.all().order_by('rank')

    form = ShiboukouForm()

    return render(request, "child_detail.html", {
        "child": child,
        "shiboukous": shiboukous,
        "form": form  # 🔥 これをテンプレートに渡す
    })


@login_required
def child_edit(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)
    if request.method == "POST":
        form = ChildForm(request.POST, instance=child)
        if form.is_valid():
            form.save()
            return redirect('child_detail', child_id=child.id)
    else:
        form = ChildForm(instance=child)
    return render(request, "edit_child.html", {"form": form, "child": child})

@login_required
def edit_shiboukou(request, shiboukou_id):
    shiboukou = get_object_or_404(Shiboukou, id=shiboukou_id, child__user=request.user)

    if request.method == 'POST':
        form = ShiboukouEditForm(request.POST, instance=shiboukou)
        if form.is_valid():
            edited_shiboukou = form.save(commit=False)
            edited_shiboukou.school = shiboukou.school  # 🔸 元の学校名を再設定
            edited_shiboukou.save()
            return redirect('child_detail', child_id=shiboukou.child.id)
    else:
        form = ShiboukouEditForm(instance=shiboukou)

    return render(request, 'edit_shiboukou.html', {'form': form, 'shiboukou': shiboukou})



@login_required
def delete_shiboukou(request, shiboukou_id):
    shiboukou = get_object_or_404(Shiboukou, id=shiboukou_id, child__user=request.user)
    child_id = shiboukou.child.id
    shiboukou.delete()
    return redirect('child_detail', child_id=child_id)

@login_required
def add_shiboukou(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)
    if request.method == 'POST':
        form = ShiboukouForm(request.POST)
        if form.is_valid():
            new_shiboukou = form.save(commit=False)
            new_shiboukou.child = child
            new_shiboukou.save()
            return redirect('child_detail', child_id=child.id)
    else:
        form = ShiboukouForm(user=request.user)
    return render(request, 'add_shiboukou.html', {'form': form, 'child': child})


def get_google_credentials(request):
    if 'credentials' not in request.session:
        return None

    credentials = Credentials(
        token=request.session['credentials']['token'],
        refresh_token=request.session['credentials']['refresh_token'],
        token_uri=request.session['credentials']['token_uri'],
        client_id=request.session['credentials']['client_id'],
        client_secret=request.session['credentials']['client_secret'],
        scopes=request.session['credentials']['scopes']
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        request.session['credentials'] = credentials_to_dict(credentials)

    return credentials

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def add_study_plan(request):
    if request.method == 'POST':
        form = StudyPlanForm(request.POST, user=request.user)
        if form.is_valid():
            study_plan = form.save(commit=False)
            study_plan.save()

            if study_plan.priority == 'A':
                sync_to_google_calendar(request, study_plan)

            return redirect('study_plan_list', child_id=study_plan.child.id)
    else:
        form = StudyPlanForm(user=request.user)

    return render(request, 'add_study_plan.html', {'form': form})

@login_required
def register_child(request):
    if request.method == "POST":
        form = ChildForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.user = request.user
            child.save()  # 子どもを保存
            form.save()
            return redirect("child_list")
    else:
        form = ChildForm()
    return render(request, "register_child.html", {"child_form": form})





@login_required
def child_list(request):
    children = Child.objects.filter(user=request.user)
    return render(request, "child_list.html", {"children": children})



def sync_to_google_calendar(request, study_plan):
    if 'credentials' not in request.session:
        return HttpResponse('Google認証が必要です。')

    credentials = Credentials(
        token=request.session['credentials']['token'],
        refresh_token=request.session['credentials']['refresh_token'],
        token_uri=request.session['credentials']['token_uri'],
        client_id=request.session['credentials']['client_id'],
        client_secret=request.session['credentials']['client_secret'],
        scopes=request.session['credentials']['scopes']
    )

    service = build('calendar', 'v3', credentials=credentials)
    start_time = timezone.now()
    event = {
        'summary': f'{study_plan.subject.name}: {study_plan.study_content}',
        'description': f'分量: {study_plan.quantity}',
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Tokyo'},
        'end': {'dateTime': (start_time + study_plan.estimated_time).isoformat(), 'timeZone': 'Asia/Tokyo'},
    }

    service.events().insert(calendarId='primary', body=event).execute()

def list_events(request):
    credentials = get_google_credentials(request)

    if not credentials:
        return HttpResponse("認証情報がありません。再認証してください。")

    try:
        # Google Calendar APIのサービスを作成
        service = build('calendar', 'v3', credentials=credentials)

        # 現在時刻からイベントを取得
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        # イベントデータの変換処理
        formatted_events = []
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            end_time = event['end'].get('dateTime', event['end'].get('date'))

            # ISOフォーマットの文字列を datetime に変換（Python 3.6対応）
            start_dt = datetime.strptime(start_time[:-6], '%Y-%m-%dT%H:%M:%S')
            end_dt = datetime.strptime(end_time[:-6], '%Y-%m-%dT%H:%M:%S')

            # 日時をフォーマット
            formatted_events.append({
                'summary': event.get('summary', '（タイトルなし）'),
                'start': start_dt.strftime('%Y-%m-%d %H:%M'),
                'end': end_dt.strftime('%Y-%m-%d %H:%M'),
                'htmlLink': event.get('htmlLink')
            })

        return render(request, 'events.html', {'events': formatted_events})

    except Exception as e:
        return HttpResponse(f'エラーが発生しました: {e}')



def google_calendar_init(request):
        # Google認証フローの初期化
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRETS_FILE,
            scopes=settings.GOOGLE_API_SCOPES,
            redirect_uri=settings.REDIRECT_URI
        )
        # 認証URLの生成
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        # セッションに保存
        request.session['state'] = state
        print("初期セッションID:", request.session.session_key)
        print("セッションに保存した state:", state)

        return redirect(authorization_url)


'''
    # セッション保存後すぐに確認
    if request.session.get('state') != state:
        print("セッション保存に失敗しました。")
        return HttpResponse("セッション保存エラー")

        print("保存した state:", state)

    return redirect(f"{authorization_url}&custom_state={state}")
'''

def google_calendar_redirect(request):

    # Googleから返ってきた state を取得
    #print("リダイレクト後のセッションID:", request.session.session_key)
    received_state = request.GET.get('state')
    session_state = request.session.get('state')

    print("リクエストで受け取った state:", received_state)
    print("セッションから取得した state:", session_state)

    if session_state is None:
      print("セッションが切れています。再認証を開始します。")
      return redirect('google_calendar_init')

    if received_state != session_state:
      return redirect('google_calendar_init')
      HttpResponse("Stateが一致しません。再認証を行ってください。")


    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=settings.GOOGLE_API_SCOPES,
        redirect_uri=settings.REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    request.session['credentials'] = credentials_to_dict(credentials)
    return redirect('list_events')
    #return HttpResponse('うまくいったでしょう？')



    #request.session['credentials'] = credentials_to_dict(credentials)
    #return redirect('list_events')


def create_event(request):
    if 'credentials' not in request.session:
        #return redirect('google_calendar_init')
        redirect_url = f'/google-calendar/init/?next={request.path}'
        print("リダイレクトするURL:", redirect_url)

        return redirect(redirect_url)

    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            credentials = get_google_credentials(request)
            if not credentials:
                    return HttpResponse("認証情報が見つかりません。再認証してください。")

            service = build('calendar', 'v3', credentials=credentials)

            event = {
                'summary': form.cleaned_data['summary'],
                'location': form.cleaned_data['location'],
                'description': form.cleaned_data['description'],
                'start': {
                    'dateTime': form.cleaned_data['start_time'].isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': form.cleaned_data['end_time'].isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
            }

             # Googleカレンダーへのイベント作成
            event_result = service.events().insert(calendarId='primary', body=event).execute()
            print("Googleカレンダーにイベントが作成されました:", event_result)

            return HttpResponse(f"イベントが作成されました: {event_result.get('htmlLink')}")

        """
          except Exception as e:
             print("Googleカレンダーへのイベント作成中にエラーが発生:", e)
            return HttpResponse(f"エラーが発生しました: {e}")
        """
    else:
        form = EventForm()

    return render(request, 'create_event.html', {'form': form})

def sync_calendar(user):
    credentials = Credentials(...)  # 認証情報の設定
    service = build('calendar', 'v3', credentials=credentials)

    plans = StudyPlan.objects.filter(user=user, priority='A')
    for plan in plans:
        event = {
            'summary': f'{plan.subject.name}: {plan.study_content}',
            'description': f'分量: {plan.quantity}, 予想時間: {plan.estimated_time}',
            'start': {'dateTime': '2025-02-10T10:00:00+09:00'},  # 適宜設定
            'end': {'dateTime': '2025-02-10T11:00:00+09:00'},
        }
        service.events().insert(calendarId='primary', body=event).execute()

    return redirect('dashboard')

def save_and_display_graph(request):
    # グラフ生成
    plt.figure(figsize=(5, 4))
    x = [1, 2, 3, 4, 5]
    y = [3, 1, 4, 1, 5]
    plt.plot(x, y, marker='o', linestyle='--', color='b')
    plt.title('保存されたグラフ')
    plt.xlabel('X')
    plt.ylabel('Y')

    # グラフを static ディレクトリに保存
    graph_path = os.path.join(settings.BASE_DIR, 'static', 'graph.png')
    plt.savefig(graph_path)
    plt.close()

    # テンプレートに表示
    return render(request, 'static_graph.html')

def create_sample_event(request):
    if 'credentials' not in request.session:
        return redirect('google_calendar_init')

    try:
        credentials = get_google_credentials(request)
        service = build('calendar', 'v3', credentials=credentials)

        event = {
            'summary': 'サンプルイベント',
            'location': 'オンライン',
            'description': 'Googleカレンダーへのイベント作成テスト',
            'start': {
                'dateTime': timezone.now().isoformat(),
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': (timezone.now() + timezone.timedelta(hours=1)).isoformat(),
                'timeZone': 'Asia/Tokyo',
            },
        }

        service.events().insert(calendarId='primary', body=event).execute()
        return HttpResponse("サンプルイベントが作成されました")  # リダイレクトを一時的に停止

    except Exception as e:
        return HttpResponse(f'エラーが発生しました: {e}')

def schools_by_prefecture(request, prefecture):
    schools = School.objects.filter(prefecture=prefecture)
    return render(request, "school_list.html", {"schools": schools})

User = get_user_model()

# ユーザー登録API
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]  # 誰でも登録可能

class UserProfileView(generics.RetrieveUpdateAPIView):

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class StudyPlanViewSet(viewsets.ModelViewSet):
    queryset = StudyPlan.objects.all()
    serializer_class = StudyPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        child_id = self.kwargs.get("child_id")
        print(f"📌 Debug: child_id = {child_id}")
        queryset = StudyPlan.objects.filter(child_id=child_id)
        priority = self.request.query_params.get('priority', None)
        is_completed = self.request.query_params.get('completed', None)  # 🔹 追加

        if priority in ['A', 'B', 'C']:
            queryset = queryset.filter(priority=priority)

        if is_completed is not None:  # 🔹 Noneチェックを追加
            if is_completed.lower() == 'true':  # 文字列の `true` を処理
                queryset = queryset.filter(is_completed=True)
            elif is_completed.lower() == 'false':  # 文字列の `false` を処理
                queryset = queryset.filter(is_completed=False)

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='mark-as-completed')
    def mark_as_completed(self, request, pk=None):
        study_plan = self.get_object()
        study_plan.is_completed = True
        study_plan.save()
        return Response({'message': '学習計画を達成済みにしました。'})

    def perform_create(self, serializer):
        # 🔹 ユーザーを自動で紐付ける
        serializer.save(user=self.request.user)

@login_required
def study_plan_form(request):
    child_id = request.GET.get("child") or request.POST.get("child")
    selected_child = None

    if child_id:
        selected_child = get_object_or_404(Child, id=child_id, user=request.user)

    if request.method == 'POST':
        form = StudyPlanForm(request.POST, user=request.user)
        if form.is_valid():
            study_plan = form.save(commit=False)
            study_plan.child = selected_child
            study_plan.save()
            return redirect('study_plan_list', child_id=selected_child.id)
    else:
        form = StudyPlanForm(user=request.user, initial={'child': selected_child})

    return render(request, "study_plan_form.html", {
        "form": form,
        "selected_child": selected_child
    })



@login_required
def study_plan_edit(request, pk):
    study_plan = get_object_or_404(StudyPlan, id=pk, child__user=request.user)  # 🔹 該当の学習計画を取得
    if request.method == "POST":
        form = StudyPlanForm(request.POST, instance=study_plan)  # 🔹 既存データをフォームにセット
        if form.is_valid():
            form.save()
            return redirect('study_plan_list', child_id=study_plan.child.id)

            #return redirect(f"/study-plan-form/?subject={study_plan.subject.name}")  # 🔹 編集後は元のページへ
    else:
        form = StudyPlanForm(instance=study_plan)  # 🔹 初期表示

    return render(request, "study_plan_edit.html", {
        "form": form,
        "study_plan": study_plan
    })

@login_required
def study_plan_delete(request, pk):
    study_plan = get_object_or_404(StudyPlan, id=pk, child__user=request.user)  # 🔹 該当の学習計画を取得

    if request.method == "POST":
        study_plan.delete()  # 🔹 削除
        return redirect('study_plan_list', child_id=study_plan.child.id)

    # 🔹 GETのときは確認画面を表示
    return render(request, "study_plan_delete.html", {
        "study_plan": study_plan
    })



@login_required
def study_plan_copy(request, pk):
    original_plan = get_object_or_404(StudyPlan, id=pk, child__user=request.user)

    # 🔹 コピーを作成
    new_plan = StudyPlan.objects.create(
        child=original_plan.child,  # 🔸 ここを修正
        subject=original_plan.subject,
        study_content=original_plan.study_content,
        quantity=original_plan.quantity,
        estimated_time=original_plan.estimated_time,
        priority=original_plan.priority
    )

    # 🔸 一覧画面に戻る
    return redirect('study_plan_list', child_id=new_plan.child.id)





@login_required
def past_exam_list(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)
    past_exams = PastExam.objects.filter(child=child).order_by('-year', '-attempt')

    return render(request, 'past_exam_list.html', {
        'child': child,
        'past_exams': past_exams
    })

@login_required
def past_exam_form(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)

    print(f"Debug: child={child}")

    if request.method == 'POST':
        form = PastExamForm(request.POST, user=request.user, child=child)
        if form.is_valid():
            past_exam = form.save(commit=False)
            past_exam.child = child
            past_exam.save()
            return redirect('past_exam_list', child_id=child.id)
    else:
        form = PastExamForm(user=request.user, child=child)

    return render(request, 'past_exam_form.html', {'form': form, 'child': child})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import PastExam, Child
from .forms import PastExamForm



@login_required
def past_exam_form(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)

    if request.method == 'POST':
        form = PastExamForm(request.POST, user=request.user, child=child)
        if form.is_valid():
            past_exam = form.save(commit=False)
            past_exam.child = child
            past_exam.save()
            return redirect('past_exam_list', child_id=child.id)
    else:
        form = PastExamForm(user=request.user, child=child)

    return render(request, 'past_exam_form.html', {'form': form, 'child': child})

@login_required
def past_exam_create(request):
    if request.method == "POST":
        form = PastExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.user = request.user  # 🔹 ユーザーを紐付ける
            exam.save()
            return redirect("past_exam_list")
    else:
        form = PastExamForm()

    return render(request, "past_exam_form.html", {"form": form})

@login_required
def study_plan_list(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)  # ✅ `user` は `Child` の取得にのみ使う
    study_plans = StudyPlan.objects.filter(child=child).order_by('-created_at')  # ✅ `user` ではなく `child` で取得

    return render(request, 'study_plan_list.html', {
        'child': child,
        'study_plans': study_plans
    })


def study_plan_list(request, child_id=None):
    #print(f"🔥 study_plan_list() が呼ばれました！ URL: {request.path}")  # ✅ URL をログ出力
    #print(f"📌 Debug: Received child_id (before) = {child_id}")

    # `child_id` を `request.resolver_match.kwargs` から取得してみる
    child_id_from_url = request.resolver_match.kwargs.get("child_id", None)
    #print(f"📌 Debug: Received child_id (from request.resolver_match) = {child_id_from_url}")

    if child_id is None and child_id_from_url is not None:
        child_id = child_id_from_url  # ✅ もし `child_id=None` なら `request.resolver_match.kwargs` からセット

    #print(f"📌 Debug: Received child_id (after fix) = {child_id}")

    if child_id is None:
        #print("❌ `child_id` が None です！ URL の設定を確認してください！")
        return render(request, 'study_plan_list.html', {'error': 'child_id が取得できません'})

    child = get_object_or_404(Child, id=child_id)
    #print(f"📌 Debug: Found child = {child}")

    study_plans = StudyPlan.objects.filter(child=child).order_by('-created_at')
    #print(f"📌 Debug: StudyPlan count = {study_plans.count()}")

    return render(request, 'study_plan_list.html', {
        'child': child,
        'study_plans': study_plans
    })

@login_required
def past_exam_edit(request, exam_id):
    exam = get_object_or_404(PastExam, id=exam_id, child__user=request.user)

    if request.method == "POST":
        form = PastExamForm(request.POST, instance=exam, user=request.user, child=exam.child)
        if form.is_valid():
            form.save()
            return redirect('past_exam_list', child_id=exam.child.id)
    else:
        form = PastExamForm(instance=exam, user=request.user, child=exam.child)

    return render(request, 'past_exam_form.html', {'form': form, 'child': exam.child})


@login_required
def past_exam_delete(request, exam_id):
    exam = get_object_or_404(PastExam, id=exam_id, child__user=request.user)

    if request.method == "POST":
        child_id = exam.child.id
        exam.delete()
        return redirect('past_exam_list', child_id=child_id)

    return render(request, 'past_exam_delete.html', {'exam': exam})



@login_required
def past_exam_copy(request, exam_id):
    exam = get_object_or_404(PastExam, id=exam_id, child__user=request.user)

    new_exam = PastExam.objects.create(
        child=exam.child,
        school=exam.school,  # ✅ 修正（school_name → school）
        year=exam.year,
        attempt=exam.attempt,
        exam_type=exam.exam_type,
        math_score=exam.math_score,
        japanese_score=exam.japanese_score,
        science_score=exam.science_score,
        social_studies_score=exam.social_studies_score,
        remarks=exam.remarks
    )

    return redirect('past_exam_list', child_id=exam.child.id)



@login_required
def exam_record_list(request, child_id):

    child = get_object_or_404(Child, id=child_id, user=request.user)
    records = ExamRecord.objects.filter(child=child).order_by("-exam_date")

    return render(request, "exam_record_list.html", {"child": child, "records": records})


@login_required
def exam_record_create(request, child_id):

    child = get_object_or_404(Child, id=child_id, user=request.user)

    if request.method == "POST":
        form = ExamRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.child = child
            record.save()
            return redirect("exam_record_list", child_id=child.id)
    else:
        form = ExamRecordForm()

    return render(request, "exam_record_form.html", {"form": form, "child": child})



@login_required
def exam_schedule_list(request, child_id):

    child = get_object_or_404(Child, id=child_id, user=request.user)
    schedules = ExamSchedule.objects.filter(child=child).order_by("exam_date", "session")

    return render(request, "exam_schedule_list.html", {"child": child, "schedules": schedules})


@login_required
def exam_schedule_create(request, child_id):

    child = get_object_or_404(Child, id=child_id, user=request.user)

    if request.method == "POST":
        form = ExamScheduleForm(request.POST, child=child)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.child = child
            schedule.save()
            return redirect("exam_schedule_list", child_id=child.id)
    else:
        form = ExamScheduleForm(child=child)

    return render(request, "exam_schedule_form.html", {"form": form, "child": child})

class StudyRecordViewSet(viewsets.ModelViewSet):
    queryset = StudyRecord.objects.all()
    serializer_class = StudyRecordSerializer

    def get_queryset(self):
        """
        子どもごとの学習記録を取得できるようにする
        """
        child_id = self.request.query_params.get('child')
        if child_id:
            return self.queryset.filter(child_id=child_id)
        return self.queryset

@login_required
def edit_child(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)
    if request.method == "POST":
        form = ChildForm(request.POST, instance=child)
        if form.is_valid():
            form.save()
            return redirect("child_list")
    else:
        form = ChildForm(instance=child)
    return render(request, "edit_child.html", {"form": form})

@login_required
def delete_child(request, child_id):
    child = get_object_or_404(Child, id=child_id, user=request.user)
    if request.method == "POST":
        child.delete()
        return redirect("child_list")
    return render(request, "delete_child.html", {"child": child})
