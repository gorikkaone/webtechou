from django.contrib import admin
import datetime
from django import forms
from .models import CustomUser, School, Subject, StudyPlan, PastExam, Child, Shiboukou, ExamRecord, ExamSchedule, StudyRecord

class ShiboukouInline(admin.TabularInline):
    autocomplete_fields = ['school']  # 志望校検索を有効化
    model = Shiboukou
    extra = 1  # 追加フォームの数

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'entrance_year')
    inlines = [ShiboukouInline]  # 志望校をインラインで表示

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('parent_name', 'email', 'is_staff')
    search_fields = ('parent_name', 'email')

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    search_fields = ['name']  # 学校名で検索可能に
    list_display = ('name', 'prefecture', 'school_type')
    list_filter = ('prefecture', 'school_type')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('child', 'subject', 'study_content', 'priority', 'created_at')
    list_filter = ('priority',)

@admin.register(PastExam)
class PastExamAdmin(admin.ModelAdmin):

    '''

    def changelist_view(self, request, extra_context=None):
                import matplotlib

matplotlib.use("Agg")
        import matplotlib.pyplot as plt
                import io

from io import BytesIO



        import base64
        from django.db.models import Avg

        # グラフのデータ取得
        exams = PastExam.objects.all()

        # グラフ1: 同じ学校・同じ年度の試験回数ごとの比較
        school_year_attempts = {}
        for exam in exams:
            key = (exam.school, exam.year)
            if key not in school_year_attempts:
                school_year_attempts[key] = {}
            school_year_attempts[key][exam.attempt] = exam.total_score

        fig1, ax1 = plt.subplots()
        for (school, year), attempts in school_year_attempts.items():
            ax1.plot(attempts.keys(), attempts.values(), label=f"{school.name} {year}")
        ax1.set_xlabel("試験回数")
        ax1.set_ylabel("合計スコア")
        ax1.set_title("同じ学校・同じ年度の試験回数ごとの比較")
        ax1.legend()

        buf1 = BytesIO()
        fig1.savefig(buf1, format="png")
        buf1.seek(0)
        encoded_graph1 = base64.b64encode(buf1.read()).decode("utf-8")
        buf1.close()

        # グラフ2: 同じ学校で1回目の試験の記録（新しい順）
        first_attempts = exams.filter(attempt=1).order_by("-year")
        school_names = [exam.school.name for exam in first_attempts]
        scores = [exam.total_score for exam in first_attempts]

        fig2, ax2 = plt.subplots()
        ax2.barh(school_names, scores, color="blue")
        ax2.set_xlabel("合計スコア")
        ax2.set_ylabel("学校")
        ax2.set_title("同じ学校で1回目の試験の記録（新しい順）")

        buf2 = BytesIO()
        fig2.savefig(buf2, format="png")
        buf2.seek(0)
        encoded_graph2 = base64.b64encode(buf2.read()).decode("utf-8")
        buf2.close()

        extra_context = extra_context or {}
        extra_context["graph1"] = encoded_graph1
        extra_context["graph2"] = encoded_graph2

        return super().changelist_view(request, extra_context=extra_context)
        '''


    list_filter = ('year', 'school')  # 過去問一覧にフィルタを追加
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "total_score":
            return None  # 合計スコアの入力フィールドを非表示にする
        if db_field.name == "year":
            current_year = datetime.datetime.now().year
            kwargs["widget"] = forms.Select(choices=[(y, str(y)) for y in range(current_year - 20, current_year + 1)])
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    def save_model(self, request, obj, form, change):
        # Noneの場合は0に変換して計算
        obj.total_score = (obj.math_score or 0) + (obj.japanese_score or 0) + (obj.science_score or 0) + (obj.social_studies_score or 0)
        super().save_model(request, obj, form, change)
    list_display = ('child', 'school', 'year', 'attempt', 'math_score', 'japanese_score', 'science_score', 'social_studies_score', 'total_score')



@admin.register(ExamRecord)
class ExamRecordAdmin(admin.ModelAdmin):
    list_display = ('child', 'exam_name', 'exam_date', 'total_score', 'total_deviation',
                    'school1', 'school2', 'school3', 'school4', 'school5',
                    'pass_probability1', 'pass_probability2', 'pass_probability3', 'pass_probability4', 'pass_probability5')

    list_filter = ('exam_name', 'exam_date', 'pass_probability1', 'pass_probability2', 'pass_probability3', 'pass_probability4', 'pass_probability5')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ['school1', 'school2', 'school3', 'school4', 'school5']:
            obj = self.get_object(request)
            if obj and obj.child:
                kwargs["queryset"] = Shiboukou.objects.filter(child=obj.child)
            else:
                kwargs["queryset"] = Shiboukou.objects.all()  # デフォルトで全志望校を表示
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_object(self, request):
        """ 編集画面で現在のオブジェクトを取得 """
        obj_id = request.resolver_match.kwargs.get("object_id")
        if obj_id:
            return self.model.objects.filter(pk=obj_id).first()
        return None


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ("child", "exam_date", "session", "school", "exam_name", "subject_count", "probability_level")
    list_filter = ("exam_date", "session", "school", "subject_count", "probability_level")


@admin.register(StudyRecord)
class StudyRecordAdmin(admin.ModelAdmin):
    list_display = ('child', 'date', 'content', 'result')
    list_filter = ('child', 'date')
    search_fields = ('content', 'result', 'comment')

    # モデルのラベルを変更
    def get_model_perms(self, request):
        return {'add': True, 'change': True, 'delete': True, 'view': True}
