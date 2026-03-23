from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from clubs.models import Club

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    club_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    username = serializers.CharField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        club = Club.objects.create(
            name=validated_data["club_name"]
        )

        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            club=club,
            role="owner"
        )

        return user


class ClubUserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "role", "is_active", "date_joined"]
        read_only_fields = fields


class ClubUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["email", "username", "password", "role"]

    def validate_role(self, value):
        requesting_user = self.context["request"].user
        if requesting_user.role == "manager" and value == "owner":
            raise serializers.ValidationError("Managers cannot create users with the Owner role.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            role=validated_data["role"],
            club=self.context["request"].user.club,
        )


class ClubUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role", "is_active"]

    def validate_role(self, value):
        requesting_user = self.context["request"].user
        if requesting_user.role == "manager" and value == "owner":
            raise serializers.ValidationError("Managers cannot assign the Owner role.")
        return value

    def validate(self, attrs):
        # Prevent a user from deactivating or changing their own role
        if self.instance == self.context["request"].user:
            raise serializers.ValidationError("You cannot modify your own account.")
        return attrs
