from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .models import CustomUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.backends import ModelBackend
from .models import StudyPlan, StudyRecord

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email instead of username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=Email)  # 🔹 `username` を `email` として取得
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
# ユーザー情報のシリアライザ
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "parent_name", "entrance_year")

# ユーザー登録のシリアライザ
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "parent_name", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            full_name=validated_data["parent_name"],
            password=validated_data["password"],
        )
        return user

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email','password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return CustomUser.objects.create_user(
        email=validated_data['email'],
        parent_name=validated_data['parent_name'],
        password=validated_data['password']
    )
'''
    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user


    def create(self, validated_data):
        user = CustomUser(
            email=validated_data['email'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()

'''

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # `email` でログインできるように修正
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(username=email, password=password)

            if user is None:
                raise serializers.ValidationError("ログインに失敗しました。")

            attrs["username"] = user.email  # Django の認証は `username` を使うため設定する

        return super().validate(attrs)

class StudyPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyPlan
        fields = ['id',  'subject', 'study_content', 'quantity', 'estimated_time', 'priority', 'created_at', 'is_completed']
        extra_kwargs = {'user': {'read_only': True}}  # ユーザーを自動設定




class StudyRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyRecord
        fields = '__all__'  # すべてのフィールドをシリアライズ
