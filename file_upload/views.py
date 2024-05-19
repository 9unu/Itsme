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
from .hug import hugging, make_pipeline, generate_text
import pandas as pd
from transformers.pipelines.pt_utils import KeyDataset

def formal_change(queue1, df, hug_obj):
    formal_pipeline = make_pipeline(model=hug_obj.formal_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)    
    formal_outputs=[]
    def data_load():
        for row in df['user']:
            yield str("상냥체 말투로 변환:" + row).strip()

    for out in formal_pipeline(data_load()):
        formal_outputs.append([x['generated_text'] for x in out])
    queue1.put(formal_outputs)

def gentle_change(queue2, df, hug_obj):
    gentle_pipeline = make_pipeline(model=hug_obj.gentle_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)
    gentle_outputs=[]
    def data_load():
        for row in df['user']:
            yield str("정중체 말투로 변환:" + row).strip()
    for out in gentle_pipeline(data_load()):
        gentle_outputs.append([x['generated_text'] for x in out])
    queue2.put(gentle_outputs)

def process_1(origin_queue,df, hug_obj):
    # 최종 반환할 데이터 프레임
    result_df = pd.DataFrame(columns=['user', 'formal', 'gentle'])
    result_df['user'] = df['user']
    # KeyDataset을 활용하기 위한 변환
    queue1=mp.Queue()
    p1 = mp.Process(target=formal_change, args=(queue1, df, hug_obj))
    queue2=mp.Queue()
    p2 = mp.Process(target=gentle_change, args=(queue2, df, hug_obj))
    p1.start()
    p2.start()
    formal_outputs=queue1.get()
    gentle_outputs=queue2.get()
    p1.join()
    p2.join()
    result_df['gentle'] = formal_outputs
    result_df['formal'] = gentle_outputs
    
    origin_queue.put(result_df)

# 사용자 말투 학습 + 답장 리스트 생성
def process_2(queue2, df, hug_obj):
    user_model = user_modeling(df, hug_obj)
    test_texts = ["곧 전화드리겠습니다", "나중에 전화하겠습니다", "문자 메세지를 보내주세요", "알바중입니다. 나중에 전화하겠습니다", "회의중입니다. 나중에 전화하겠습니다", "운전중입니다. 나중에 전화하겠습니다", "밥먹고 있습니다. 나중에 전화하겠습니다.", "무슨일 있으신가요?"]
    result = []
    user_pipeline = make_pipeline(model=user_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)
    for text in test_texts:
        user_output = generate_text(user_pipeline, text=text, target_style='user', num_return_sequences=1, max_length=100)[0]
        result.append(user_output)
    queue2.put(str(result))

def upload(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            hug_obj = hugging()
            mp.set_start_method('spawn')
            instance = form.save(commit=False)
            print("<<<카톡 데이터 csv로 변환 중>>>")
            start_time = time.time()
            room_name, df, group, users = txt.txt_to_csv(instance.file, instance.name)
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"<<<변환 완료>>>{elapsed_time} 초")
            instance.room = room_name
            instance.group = group
            instance.users = users
            df.columns = ['user']
            df['formal'] = None
            df['gentle'] = None
            print("총 데이터 수:", len(df))
            
            limit = min(1500, len(df))
            df = df.sample(n=limit)
            print("학습용 데이터 수 (최대 1500 제한):", len(df))
            print("<<<학습 데이터 생성 파이프라인 동작 중>>>")
            start_time = time.time()
            origin_queue=mp.Queue()
            proc_1=mp.Process(target=process_1, args=(origin_queue, df, hug_obj))
            proc_1.start()
            df=origin_queue.get()
            proc_1.join()
            elapsed_time = end_time - start_time
            print(f"<<<학습 데이터 생성 완료>>> {elapsed_time // 60} 분")
            # process_1이 완료되었으므로 그 결과를 process_2에 넘겨줌
            print("<<<모델 학습 코드 동작 중>>>")
            queue2=mp.Queue()
            proc_2 = mp.Process(target=process_2, args=(queue2, df, hug_obj))
            proc_2.start()
            result=queue2.get()
            proc_2.join()
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"<<<모델 학습 및 답장 변환 완료>>> {elapsed_time // 60} 분")

            instance.reply_list = result
            instance.save()
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