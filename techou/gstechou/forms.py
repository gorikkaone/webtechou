from django import forms
from .models import StudyPlan, Child
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, PastExam, School, Shiboukou, ExamSchedule, ExamRecord
from datetime import datetime, timedelta,date


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(label="メールアドレス", required=True)
    parent_name = forms.CharField(label="保護者名", max_length=100)

    class Meta:
        model = CustomUser
        fields = ['email', 'parent_name', 'password1', 'password2']
        labels = {
            'email': 'メールアドレス',
            'parent_name': '保護者名',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.parent_name = self.cleaned_data["parent_name"]
        if commit:
            user.save()
        return user


class StudyPlanForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['child'].queryset = Child.objects.filter(user=user)

    class Meta:
        model = StudyPlan
        fields = ['child', 'subject', 'study_content', 'quantity', 'estimated_time', 'priority']
        labels = {
            'child': '子ども',
            'subject': '科目',
            'study_content': '内容',
            'quantity': '分量',
            'estimated_time': '予想時間',
            'priority': '優先度',
        }
        widgets = {
            'child': forms.Select(),
            'priority': forms.Select(choices=[
                ('A', '絶対やる'),
                ('B', 'できればやる'),
                ('C', 'やらなくてもよい'),
            ]),
            'estimated_time': forms.TextInput(attrs={'placeholder': '例: 30分'}),
        }

class ChildForm(forms.ModelForm):

    current_year = date.today().year
    YEAR_CHOICES = [(year, f"{year}年") for year in range(current_year, current_year + 6)]

    entrance_year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        label="受験学年（西暦）",
    )

    class Meta:
        model = Child
        fields = ["name", "entrance_year", "google_calendar_id"]
        labels = {
            "name": "子どもの名前",
            "google_calendar_id": "GoogleカレンダーID（任意）",
        }
        widgets = {
            "google_calendar_id": forms.TextInput(attrs={"placeholder": "任意（未入力でもOK）"}),
        }









class EventForm(forms.Form):
    summary = forms.CharField(label='イベントタイトル', max_length=100)
    description = forms.CharField(label='説明', widget=forms.Textarea, required=False)
    location = forms.CharField(label='場所', max_length=200, required=False)
    start_time = forms.DateTimeField(
        label='開始時間',
        initial=datetime.now().strftime('%Y-%m-%d %H:%M'),
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    end_time = forms.DateTimeField(
        label='終了時間',
        initial=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )

from datetime import datetime
from django import forms
from gstechou.models import PastExam, School, Child

class PastExamForm(forms.ModelForm):
    school = forms.ModelChoiceField(
        queryset=School.objects.none(),
        required=True,
        label="学校名"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        child = kwargs.pop('child', None)
        super().__init__(*args, **kwargs)

        if child:
            # 選択した子どもの志望校リストの学校のみ表示
            self.fields['school'].queryset = School.objects.filter(
                shiboukou_entries__child=child
            )

    class Meta:
        model = PastExam
        fields = ['school', 'year', 'attempt', 'exam_type',
                  'math_score', 'japanese_score', 'science_score', 'social_studies_score',
                  'remarks']
        labels = {
            'school': "学校名",
            'year': "年度",
            'attempt': "回数",
            'exam_type': "入試の分類",
            'math_score': "算数",
            'japanese_score': "国語",
            'science_score': "理科",
            'social_studies_score': "社会",
            'remarks': "特記事項",
        }


# 追加用フォーム
class ShiboukouForm(forms.ModelForm):
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=True,
        label="学校（検索・選択）",
        widget=forms.Select(attrs={"class": "school-select"})
    )

    rank = forms.ChoiceField(
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        label="志望ランク",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Shiboukou
        fields = ['school', 'rank']

# 編集用フォーム
# 追加用フォーム
class ShiboukouForm(forms.ModelForm):
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=True,
        label="学校（検索・選択）",
        widget=forms.Select(attrs={"class": "school-select"})
    )

    rank = forms.ChoiceField(
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        label="志望ランク",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Shiboukou
        fields = ['school', 'rank']

# 編集用フォーム
class ShiboukouEditForm(forms.ModelForm):
    rank = forms.ChoiceField(
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        label="志望ランク",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = Shiboukou
        fields = ['rank']  # 🔸 school を削除


class ExamScheduleForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        child = kwargs.pop('child', None)  # 子どもオブジェクトを取得
        super().__init__(*args, **kwargs)

        if child:
            # この子どもの志望校リストに登録された学校のみを選択肢にする
            self.fields['school'].queryset = Shiboukou.objects.filter(child=child).values_list('school', flat=True)

    class Meta:
        model = ExamSchedule
        fields = [
            "exam_date", "session", "start_time", "end_time", "school",
            "exam_name", "subject_count", "probability_level"
        ]
        widgets = {
            "exam_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }




class ExamRecordForm(forms.ModelForm):
    class Meta:
        model = ExamRecord
        fields = [
            "exam_name", "exam_date", "total_deviation",
            "school1", "school2", "school3", "school4", "school5",
            "pass_probability1", "pass_probability2", "pass_probability3",
            "pass_probability4", "pass_probability5"
        ]
        widgets = {
            "exam_date": forms.DateInput(attrs={"type": "date"}),
        }




class PastExamForm(forms.ModelForm):
    school = forms.ModelChoiceField(
        queryset=Shiboukou.objects.none(),
        required=True,
        label="志望校"
    )

    year = forms.ChoiceField(label="年度", choices=[])

    exam_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '例: 第1回, 特別入試, AO入試'})
    )
    math_score = forms.IntegerField(label="算数", required=False, min_value=0, max_value=100)
    japanese_score = forms.IntegerField(label="国語", required=False, min_value=0, max_value=100)
    science_score = forms.IntegerField(label="理科", required=False, min_value=0, max_value=100)
    social_studies_score = forms.IntegerField(label="社会", required=False, min_value=0, max_value=100)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        child = kwargs.pop('child', None)  # ✅ これを追加！
        super().__init__(*args, **kwargs)

        current_year = datetime.now().year
        self.fields['year'].choices = [(y, str(y)) for y in range(current_year - 10, current_year + 1)]

        if child:
            # ✅ 選択した子どもの志望校リストの学校のみ表示
            self.fields['school'].queryset = Shiboukou.objects.filter(child=child
            )

    class Meta:
        model = PastExam
        fields = ['school', 'year', 'attempt', 'exam_type',
                  'math_score', 'japanese_score', 'science_score', 'social_studies_score',
                  'remarks']
        labels = {
            'school': "志望校",
            'year': "年度",
            'attempt': "回数",
            'exam_type': "入試の分類",
            'math_score': "算数",
            'japanese_score': "国語",
            'science_score': "理科",
            'social_studies_score': "社会",
            'remarks': "特記事項",
        }
        widgets = {
            'exam_date': forms.DateInput(attrs={'type': 'date'}),
            'school': forms.Select(),
        }
