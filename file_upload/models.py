from django.db import models
import os
# import re
# from uuid import uuid4
# Create your models here.


# txt파일 저장 경로를 각 사용자 이름 폴더로 바꿔주기
def file_path_change(instance, filename):			
    upload_to = instance.user_name		
    # ext = filename.split('.')[-1]
    # uuid = uuid4().hex
    # filename = '{}.{}'.format(uuid, ext)                                           
    return os.path.join(upload_to, filename)

class UploadFile(models.Model):
    user_id=models.CharField(max_length=300,null=False, blank=False)
    user_name=models.CharField(max_length=300,null=False, blank=False)
    
    file = models.FileField(blank=False, upload_to=file_path_change, null=True)
    
    room = models.CharField(max_length=50, null=True, blank=True)
    # users =models.CharField(max_length=300, null=True, blank=True)
    # group = models.BooleanField(null=True, blank=True)
    
    reply_list=models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"사용자 : {self.user_name} + [{self.user_id}], 파일 경로:{self.file}"