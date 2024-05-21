import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "itsme.settings")
django.setup()
from django.shortcuts import render, redirect, reverse
from .forms import UploadFileForm
from .models import UploadFile
from . import text_preprocessing as txt
import multiprocessing as mp
import time
from .user_speech_modeling import user_modeling
from .hug import hugging, make_pipeline
import pandas as pd


# 정중체, 상냥체 모델로 학습데이터 생성
def process_1(queue1, df, hug_obj):
    formal_pipeline = make_pipeline(model=hug_obj.formal_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)
    gentle_pipeline = make_pipeline(model=hug_obj.gentle_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)
    
    def formal_data():
        for row in df['user']:
            yield str("상냥체 말투로 변환:" + row).strip()
    def gentle_data():
        for row in df['user']:
            yield str("정중체 말투로 변환:" + row).strip()
    formal_outputs=[]
    gentle_outputs=[]
    for out in formal_pipeline(formal_data()):
        formal_outputs.append([x['generated_text'] for x in out][0])

    for out in gentle_pipeline(gentle_data()):
        gentle_outputs.append([x['generated_text'] for x in out][0])
    
    df['formal']=formal_outputs
    df['gentle']=gentle_outputs
    queue1.put(df)
    
# 사용자 말투 학습 + 답장 리스트 생성
def process_2(queue2, df, hug_obj):
    user_model = user_modeling(df, hug_obj)
    test_texts = ["곧 전화드리겠습니다", "나중에 전화하겠습니다", "문자 메세지를 보내주세요", "알바중입니다. 나중에 전화하겠습니다", "회의중입니다. 나중에 전화하겠습니다", "운전중입니다. 나중에 전화하겠습니다", "밥먹고 있습니다. 나중에 전화하겠습니다.", "무슨일 있으신가요?"]
    result = []
    user_pipeline = make_pipeline(model=user_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)
    def user_data():
        for txt in test_texts:
            yield f"사용자 말투로 변환:" + txt
    for out in user_pipeline(user_data()):
        result.append([x['generated_text'] for x in out][0])

    queue2.put(str(result))

def upload(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            total_time=0
            hug_obj = hugging()
            mp.set_start_method('spawn')
            instance = form.save(commit=False)
            print("<<<카톡 데이터 csv로 변환 중>>>")
            start_time = time.time()
            room_name, df, group, users = txt.txt_to_csv(instance.file, instance.name)
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"<<<변환 완료>>>{elapsed_time} 초")
            total_time+=elapsed_time
            instance.room = room_name
            instance.group = group
            instance.users = users
            df.columns = ['user']
            df['formal'] = None
            df['gentle'] = None
            print("총 데이터 수:", len(df))
            limit = min(1000, len(df))
            df = df.sample(n=limit)
            print("학습용 데이터 수 (최대 1500 제한):", len(df))
            print("<<<학습 데이터 생성 파이프라인 동작 중>>>")
            start_time = time.time()
            queue1=mp.Queue()
            p1 = mp.Process(target=process_1, args=(queue1, df, hug_obj))
            p1.start()
            df=queue1.get()
            p1.join()
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"<<<학습 데이터 생성 완료>>> {elapsed_time // 60} 분")
            # df.to_csv("학습 데이터 확인용.csv", encoding='utf-8')
            total_time+=elapsed_time
            # process_1이 완료되었으므로 그 결과를 process_2에 넘겨줌
            print("<<<모델 학습 코드 동작 중>>>")
            queue2=mp.Queue()
            p2 = mp.Process(target=process_2, args=(queue2, df, hug_obj))
            p2.start()
            result=queue2.get()
            p2.join()
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"<<<모델 학습 및 답장 변환 완료>>> {elapsed_time // 60} 분")
            total_time+=elapsed_time

            instance.reply_list = result
            instance.save()
            print("총 소요 시간: ", total_time//60 ,"분")
            return redirect(reverse('file_upload:index'))
    else:
        form = UploadFileForm()

    return render(request, 'file_upload/upload_form.html', {'form': form})


def file_list(request):
    list = UploadFile.objects.all().order_by('-pk')# '-pk' ->역정렬 (최신이 위로 가게)
    return render(
        request,
        'file_upload/file_list.html',
        {'list':list}
    )

def index(request):
    return render(request, 'file_upload/index.html')


import os
from django.conf import settings
def delete_file(request, id):
    file=UploadFile.objects.get(pk=id)
    media_root=settings.MEDIA_ROOT
    remove_file = media_root + '/' + str(file.file)
    print("삭제할 파일:", remove_file)

    if os.path.isfile(remove_file):
        os.remove(remove_file) # 실제 파일 삭제

    file.delete() # db값 삭제 (media값삭제 아님)

    return redirect(reverse('file_upload:list'))


from rest_framework import viewsets
from .serializers import PostSerializer
from .models import UploadFile

class ResponseViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer

    def get_queryset(self):
        user_id = self.request.headers.get('user-id')
        print(type(user_id))
        queryset = UploadFile.objects.filter(id=int(user_id))

        return queryset
