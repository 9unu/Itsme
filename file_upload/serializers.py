from rest_framework import  serializers
from .models import UploadFile

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadFile
        fields = ('name', 'room', 'users', 'group', 'reply_list')