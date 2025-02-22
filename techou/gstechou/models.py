from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from rest_framework import generics, permissions
from rest_framework.response import Response
from django.conf import settings

# カスタムユーザーのマネージャー
class CustomUserManager(BaseUserManager):
    def create_user(self, email, parent_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, parent_name=parent_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, parent_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, parent_name, password, **extra_fields)

# カスタムユーザーモデル
class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    parent_name = models.CharField(max_length=100, verbose_name="保護者氏名", null=False, blank=False, default="未設定")
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["parent_name"]

    def __str__(self):
        return self.parent_name


class Child(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="children")
    name = models.CharField(max_length=100, verbose_name="子どもの名前")
    entrance_year = models.PositiveIntegerField(verbose_name="受験学年（西暦）", null=True, blank=True)  # 受験学年をChildに追加
    google_calendar_id = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name}（{self.user.parent_name}）"

# 学校モデル
class School(models.Model):

    PREFECTURE_CHOICES = [
        ("北海道", "北海道"), ("青森県", "青森県"), ("岩手県", "岩手県"), ("宮城県", "宮城県"), ("秋田県", "秋田県"),
        ("山形県", "山形県"), ("福島県", "福島県"), ("茨城県", "茨城県"), ("栃木県", "栃木県"), ("群馬県", "群馬県"),
        ("埼玉県", "埼玉県"), ("千葉県", "千葉県"), ("東京都", "東京都"), ("神奈川県", "神奈川県"), ("新潟県", "新潟県"),
        ("富山県", "富山県"), ("石川県", "石川県"), ("福井県", "福井県"), ("山梨県", "山梨県"), ("長野県", "長野県"),
        ("岐阜県", "岐阜県"), ("静岡県", "静岡県"), ("愛知県", "愛知県"), ("三重県", "三重県"), ("滋賀県", "滋賀県"),
        ("京都府", "京都府"), ("大阪府", "大阪府"), ("兵庫県", "兵庫県"), ("奈良県", "奈良県"), ("和歌山県", "和歌山県"),
        ("鳥取県", "鳥取県"), ("島根県", "島根県"), ("岡山県", "岡山県"), ("広島県", "広島県"), ("山口県", "山口県"),
        ("徳島県", "徳島県"), ("香川県", "香川県"), ("愛媛県", "愛媛県"), ("高知県", "高知県"), ("福岡県", "福岡県"),
        ("佐賀県", "佐賀県"), ("長崎県", "長崎県"), ("熊本県", "熊本県"), ("大分県", "大分県"), ("宮崎県", "宮崎県"),
        ("鹿児島県", "鹿児島県"), ("沖縄県", "沖縄県"),
    ]

    name = models.CharField(max_length=100, verbose_name='学校名')
    address = models.CharField(max_length=200, null=True, blank=True, verbose_name='住所')
    school_type = models.CharField(
        max_length=10,
        choices=[('私立', '私立'), ('国立', '国立')],
        verbose_name='学校種別'
    )
    prefecture = models.CharField(
        max_length=10,
        choices=PREFECTURE_CHOICES,
        verbose_name='都道府県',
        default='不明'
    )

    def __str__(self):
        return self.name


# 教科モデル
class Subject(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='教科名')  # 🔹 直接日本語を保存

    def __str__(self):
        return self.name  # 🔹 そのまま日本語で表示


# 学習計画モデル
class StudyPlan(models.Model):
    PRIORITY_CHOICES = [
        ('A', '絶対やる'),
        ('B', 'できればやる'),
        ('C', 'やらなくてもよい'),
    ]

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="study_plans", null=True, blank=True)  # 🔹 ユーザーではなく子どもに紐付け
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    study_content = models.TextField()  # 学習内容の説明
    quantity = models.CharField(max_length=50)  # 問題数、ページ数など
    estimated_time = models.CharField(max_length=20, verbose_name="予想時間")
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    is_completed = models.BooleanField(default=False)  # 学習計画が達成済みか

    def __str__(self):
        return f"{self.child.name} - {self.subject.name}: {self.study_content} ({self.priority}, {'済' if self.is_completed else '未'})"

class Shiboukou(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="shiboukou_list")
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="shiboukou_entries")
    rank = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        verbose_name="志望ランク"
    )

    class Meta:
        verbose_name = "志望校"
        verbose_name_plural = "志望校一覧"
        unique_together = ('child', 'school')  # 重複登録を防ぐ

    def __str__(self):
        return f"{self.child.name} - {self.school.name} ({self.rank})"



class PastExam(models.Model):

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="past_exams", blank=True, null=True)
    school = models.ForeignKey(Shiboukou, on_delete=models.SET_NULL, null=True, verbose_name="志望校")  # ✅ 志望校リストに紐付ける
    year = models.IntegerField(verbose_name="年度")
    attempt = models.IntegerField(verbose_name="回数")
    exam_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="入試の分類")
    math_score = models.IntegerField(verbose_name="算数")
    japanese_score = models.IntegerField(verbose_name="国語")
    science_score = models.IntegerField(verbose_name="理科")
    social_studies_score = models.IntegerField(verbose_name="社会")
    total_score = models.IntegerField(verbose_name="合計", blank=True, null=True)
    remarks = models.TextField(blank=True, verbose_name="特記事項")

    class Meta:
        verbose_name = "過去問記録"
        verbose_name_plural = "過去問記録一覧"

    def save(self, *args, **kwargs):
        self.total_score = self.math_score + self.japanese_score + self.science_score + self.social_studies_score
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.child.name} - {self.school.school.name if self.school else '不明'} ({self.year} - {self.exam_type or '不明'})"

class ExamRecord(models.Model):
    child = models.ForeignKey('Child', on_delete=models.CASCADE, related_name='exam_records', verbose_name='受験生')
    exam_name = models.CharField(max_length=255, verbose_name='試験名')
    exam_date = models.DateField(verbose_name='実施日')

    math_score = models.IntegerField(null=True, blank=True, verbose_name='算数 得点')
    math_deviation = models.FloatField(null=True, blank=True, verbose_name='算数 偏差値')

    japanese_score = models.IntegerField(null=True, blank=True, verbose_name='国語 得点')
    japanese_deviation = models.FloatField(null=True, blank=True, verbose_name='国語 偏差値')

    science_score = models.IntegerField(null=True, blank=True, verbose_name='理科 得点')
    science_deviation = models.FloatField(null=True, blank=True, verbose_name='理科 偏差値')

    social_studies_score = models.IntegerField(null=True, blank=True, verbose_name='社会 得点')
    social_studies_deviation = models.FloatField(null=True, blank=True, verbose_name='社会 偏差値')

    total_score = models.IntegerField(editable=False, null=True, blank=True, verbose_name='合計 得点')
    total_deviation = models.FloatField(editable=True, null=True, blank=True, verbose_name='合計 偏差値')

    school1 = models.ForeignKey('Shiboukou', on_delete=models.SET_NULL, null=True, blank=True, related_name='school1', verbose_name='志望校1')
    school2 = models.ForeignKey('Shiboukou', on_delete=models.SET_NULL, null=True, blank=True, related_name='school2', verbose_name='志望校2')
    school3 = models.ForeignKey('Shiboukou', on_delete=models.SET_NULL, null=True, blank=True, related_name='school3', verbose_name='志望校3')
    school4 = models.ForeignKey('Shiboukou', on_delete=models.SET_NULL, null=True, blank=True, related_name='school4', verbose_name='志望校4')
    school5 = models.ForeignKey('Shiboukou', on_delete=models.SET_NULL, null=True, blank=True, related_name='school5', verbose_name='志望校5')
    PASS_PROBABILITY_CHOICES = [
        ('80+', '80%以上'),
        ('80-60', '80〜60%'),
        ('60-40', '60〜40%'),
        ('40-20', '40〜20%'),
        ('20-', '20%未満')
    ]
    pass_probability1 = models.CharField(max_length=10, choices=PASS_PROBABILITY_CHOICES, null=True, blank=True, verbose_name='志望校1の合格可能性')
    pass_probability2 = models.CharField(max_length=10, choices=PASS_PROBABILITY_CHOICES, null=True, blank=True, verbose_name='志望校2の合格可能性')
    pass_probability3 = models.CharField(max_length=10, choices=PASS_PROBABILITY_CHOICES, null=True, blank=True, verbose_name='志望校3の合格可能性')
    pass_probability4 = models.CharField(max_length=10, choices=PASS_PROBABILITY_CHOICES, null=True, blank=True, verbose_name='志望校4の合格可能性')
    pass_probability5 = models.CharField(max_length=10, choices=PASS_PROBABILITY_CHOICES, null=True, blank=True, verbose_name='志望校5の合格可能性')

    result_notes = models.TextField(blank=True, null=True, verbose_name='結果について')

    def save(self, *args, **kwargs):
        scores = [self.math_score, self.japanese_score, self.science_score, self.social_studies_score]
        deviations = [self.math_deviation, self.japanese_deviation, self.science_deviation, self.social_studies_deviation]

        self.total_score = sum(filter(None, scores))
        valid_deviations = list(filter(None, deviations))
        self.total_deviation = sum(valid_deviations) / len(valid_deviations) if valid_deviations else None

        super().save(*args, **kwargs)

class ExamSchedule(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE)  # 子どもと紐付け
    school = models.ForeignKey(School, on_delete=models.CASCADE)  # 志望校リストから
    exam_date = models.DateField()  # 受験日
    session = models.CharField(max_length=10, choices=[("午前", "午前"), ("午後", "午後")])  # 午前・午後
    start_time = models.TimeField(null=True, blank=True)  # 開始時刻
    end_time = models.TimeField(null=True, blank=True)  # 終了時刻
    exam_name = models.CharField(max_length=255)  # 試験名（自由記述）
    subject_count = models.CharField(
        max_length=10,
        choices=[("4教科", "4教科"), ("2教科", "2教科"), ("単科", "単科"), ("その他", "その他")]
    )  # 教科数
    probability_level = models.CharField(
        max_length=10,
        choices=[("挑戦校", "挑戦校"), ("実力相応校", "実力相応校"), ("安全校", "安全校")]
    )  # 可能性レベル

    def __str__(self):
        return f"{self.child.name} - {self.exam_date} - {self.exam_name}"

class StudyRecord(models.Model):
    child = models.ForeignKey(
        'Child', on_delete=models.CASCADE, related_name='study_records',
        verbose_name="子ども"
    )
    date = models.DateField(verbose_name="日付")
    content = models.TextField(verbose_name="学習内容")
    result = models.CharField(max_length=255, verbose_name="成果")
    comment = models.TextField(blank=True, null=True, verbose_name="感想")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        verbose_name = "学習記録"
        verbose_name_plural = "学習記録一覧"

    def __str__(self):
        return f"{self.child.name} - {self.date} - {self.content}"

    child = models.ForeignKey(
        'Child', on_delete=models.CASCADE, related_name='study_records',
        verbose_name="子ども"
    )
    date = models.DateField(verbose_name="日付")
    content = models.TextField(verbose_name="学習内容")
    result = models.CharField(max_length=255, verbose_name="成果")
    comment = models.TextField(blank=True, null=True, verbose_name="感想")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        verbose_name = "学習記録"
        verbose_name_plural = "学習記録一覧"

    def __str__(self):
        return f"{self.child.name} - {self.date} - {self.content}"
