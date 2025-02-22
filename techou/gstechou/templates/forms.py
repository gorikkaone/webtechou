from django import forms
from .models import StudyPlan, Child
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, PastExam, School, Shiboukou, ExamSchedule, ExamRecord
from datetime import datetime, timedelta,date


class StudyPlanForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['child'].queryset = Child.objects.filter(parent=user)

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

    shiboukou_schools = forms.ModelMultipleChoiceField(
        queryset=School.objects.all(),
        widget=forms.SelectMultiple(attrs={"class": "school-select"}),
        required=False,
        label="志望校"
    )

    class Meta:
        model = Child
        fields = ["name", "entrance_year", "google_calendar_id", "shiboukou_schools"]
        labels = {
            "name": "子どもの名前",
            "google_calendar_id": "GoogleカレンダーID（任意）",
        }
        widgets = {
            "google_calendar_id": forms.TextInput(attrs={"placeholder": "任意（未入力でもOK）"}),
        }

    # 🔥 ここが最重要！これを必ず定義！
    def save(self, commit=True):
        child = super().save(commit=False)
        if commit:
            child.save()
            child.shiboukou_list.all().delete()  # 既存の志望校を削除
            selected_schools = self.cleaned_data['shiboukou_schools']
            for school in selected_schools:
                Shiboukou.objects.create(child=child, school=school, rank="B")
        return child




class CustomUserCreationForm(UserCreationForm):
     class Meta:
        model = CustomUser
        fields = ['email', 'parent_name']
        labels = {
            'email': 'メールアドレス',
            'parent_name': '保護者名',
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
        queryset=Shiboukou.objects.none(),  # 初期値は空（後でユーザーの子どもに紐付ける）
        required=True,
        label="志望校（志望校リストから選択）"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ✅ ユーザーの子どもの志望校リストを取得
        if user:
            self.fields['child'].queryset = Child.objects.filter(user=user)

        # ✅ 選択した子どもの志望校リストのみ表示
        if self.instance and self.instance.pk:
            self.fields['school'].queryset = Shiboukou.objects.filter(child=self.instance.child)

    class Meta:
        model = PastExam
        fields = ['child', 'school', 'year', 'attempt', 'exam_type',
                  'math_score', 'japanese_score', 'science_score', 'social_studies_score',
                  'remarks']
        labels = {
            'child': '子ども',
            'school': "志望校（志望校リストから選択）",
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
        }


class ShiboukouForm(forms.ModelForm):
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=True,
        label="学校（検索・選択）",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    rank = forms.ChoiceField(
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        label="志望ランク",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ✅ ユーザーの子どものみ選択肢にする
        if user:
            self.fields['child'].queryset = Child.objects.filter(user=user)

    class Meta:
        model = Shiboukou
        fields = ['child', 'school', 'rank']
        labels = {
            'child': '子ども',
            'school': '学校（検索・選択）',
            'rank': '志望ランク'
        }



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




#@login_required
class PastExamForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ✅ ユーザーの子どものみ選択肢にする
        if user:
            self.fields['child'].queryset = Child.objects.filter(user=user)

        # ✅ 編集時は、現在の child を選択肢に含める
        if self.instance and self.instance.pk:
            self.fields['child'].queryset |= Child.objects.filter(pk=self.instance.child.pk)
# ✅ 年度の選択肢をセット（現在の年度から過去10年分）
        current_year = datetime.now().year
        self.fields['year'].choices = [(y, str(y)) for y in range(current_year - 10, current_year + 1)]

    # ✅ `choices=[]` ではなく、`__init__` で動的にセット
    year = forms.ChoiceField(label="年度", choices=[])
    exam_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '例: 第1回, 特別入試, AO入試'})
    )
    math_score = forms.IntegerField(label="算数", required=False, min_value=0, max_value=100)
    japanese_score = forms.IntegerField(label="国語", required=False, min_value=0, max_value=100)
    science_score = forms.IntegerField(label="理科", required=False, min_value=0, max_value=100)
    social_studies_score = forms.IntegerField(label="社会", required=False, min_value=0, max_value=100)

    class Meta:
        model = PastExam
        fields = ['child', 'school_name', 'year', 'attempt', 'exam_type',
                  'math_score', 'japanese_score', 'science_score', 'social_studies_score',
                  'remarks']
        labels = {
            'child': '子ども',
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
