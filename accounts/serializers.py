from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from clubs.models import Club

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    club_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    username = serializers.CharField()

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
