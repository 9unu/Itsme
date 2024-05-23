from rest_framework import  serializers
from .models import UploadFile

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadFile
        fields = ('user_id', 'user_name', 'room', 'reply_list')