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
from django.conf import settings
import pandas as pd

home_url="http://54.79.101.135:8080"

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

from django.contrib.auth.decorators import login_required
@login_required # 로그인 상태일때만 가능
def upload(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            total_time=0
            print("모델 초기화 시작")
            try:
                hug_obj = hugging()
                print("모델 초기화 완료")
            except Exception as e:
                print("모델 초기화 도중 오류 발생:", e)
            # mp.set_start_method('spawn')
            instance = form.save(commit=False)
            instance.user_name=request.session['user_name']
            instance.user_id=request.session['user_id']
            print("<<<카톡 데이터 csv로 변환 중>>>")
            start_time = time.time()
            room_name, df, group, users = txt.txt_to_csv(instance.file, instance.user_name)
            instance.room = room_name
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"<<<변환 완료>>>{elapsed_time} 초")
            ExistingInstance = UploadFile.objects.filter(user_id=instance.user_id, room=instance.room)
            if ExistingInstance.exists():
                for file in ExistingInstance:
                    media_root = str(settings.MEDIA_ROOT)  # Path 객체를 문자열로 변환
                    remove_file = os.path.join(media_root, str(file.file))
                    # 파일이 존재하면 삭제
                    if os.path.isfile(remove_file):
                        os.remove(remove_file)  # 실제 파일 삭제                    
                    file.delete()           
            total_time+=elapsed_time
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
            media_root = str(settings.MEDIA_ROOT)  # Path 객체를 문자열로 변환
            remove_file = os.path.join(media_root, str(file.file))
            os.remove(remove_file)
            
            print("총 소요 시간: ", total_time//60 ,"분")
            return redirect(reverse('file_upload:index'))
    else:
        form = UploadFileForm()

    return render(request, 'file_upload/upload_form.html', {'form': form})


from django.views import View
import requests
"""카카오 서버에 인증 요청"""
class kakaoView(View):
    def get(self, request):
        kakao_api = "https://kauth.kakao.com/oauth/authorize?response_type=code"
        redirect_uri = f"{home_url}/file/kakao/callback"
        client_id = settings.API_KEY
        print("서버에 인증 요청은감")
        return redirect(f"{kakao_api}&client_id={client_id}&redirect_uri={redirect_uri}")
    
"""인증 요청 후 받은 엑세스토큰으로 사용자 정보 get request -> nickname, id 수집"""
class kakaoCallBackView(View):
    def get(self, request):
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.API_KEY,
            "redirect_uri": f"{home_url}/file/kakao/callback",  # 변경: redirection_uri -> redirect_uri
            "code": request.GET["code"]
        }
        kakao_token_api = "https://kauth.kakao.com/oauth/token"
        response = requests.post(kakao_token_api, data=data)
        response_data = response.json()
        access_token = response_data.get("access_token")

        if access_token:
            kakao_user_api = "https://kapi.kakao.com/v2/user/me"
            headers = {"Authorization": f"Bearer {access_token}"}  # 변경: ${access_token} -> {access_token}
            user_response = requests.get(kakao_user_api, headers=headers)
            user_information = user_response.json()

            kakao_id = user_information.get("id")
            kakao_nickname = user_information.get("properties", {}).get("nickname")

            if kakao_id and kakao_nickname:
                request.session['user_id'] = kakao_id
                request.session['user_name'] = kakao_nickname
                print("받아옴")
                return render(request, 'file_upload/index.html')
            else:
                print("오류")

        

"""로그인 화면"""
def user_login(request):
    return render(request, 'file_upload/user_login.html')

"""초기 화면"""
def index(request):
    return render(request, 'file_upload/index.html')


"""업로드한 파일 보여주는 화면"""
def file_list(request):
    list = UploadFile.objects.filter(user_id=request.session['user_id']).order_by('-pk')# '-pk' ->역정렬 (최신이 위로 가게)
    return render(
        request,
        'file_upload/file_list.html',
        {'list':list}
    )

"""업로드한 파일 중 삭제하고 싶은 파일 선택시 제거"""
import os
from django.conf import settings
def delete_file(request, id):
    try:
        # user_id와 pk로 파일을 가져옴
        file = UploadFile.objects.filter(user_id=request.session['user_id']).get(pk=id)
        
        # 파일 경로를 생성
        media_root = str(settings.MEDIA_ROOT)  # Path 객체를 문자열로 변환
        remove_file = os.path.join(media_root, str(file.file))
        print("삭제할 파일:", remove_file)
        
        # 파일이 존재하면 삭제
        if os.path.isfile(remove_file):
            os.remove(remove_file)  # 실제 파일 삭제
        
        # 데이터베이스에서 파일 레코드 삭제
        file.delete()  # db값 삭제 (media값 삭제 아님)
        
    except UploadFile.DoesNotExist:
        print("파일이 존재하지 않습니다.")
    
    # 파일 목록 페이지로 리다이렉트
    return redirect(reverse('file_upload:list'))

"""로그 아웃 시 세션에 묶여있던 사용자 id, 닉네임 메모리 제거"""
def del_session(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'user_name' in request.session:
        del request.session['user_name']
    
    return render(request, 'file_upload/user_login.html')
    

"""모바일 앱에서 request왔을 때 header 내용 (user-id)에 맞춰서 필터링 후 사용자의 답장 리스트 response"""
from rest_framework import viewsets
from .serializers import PostSerializer
from .models import UploadFile

class ResponseViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer

    def get_queryset(self):
        user_id = self.request.headers.get('user-id')
        print(user_id)
        queryset = UploadFile.objects.filter(user_id=user_id)
        print(queryset)
        return queryset
    


"""여러개 gpu활용가능할때 병렬처리용"""
# def formal_change(queue1, df, hug_obj):
#     formal_pipeline = make_pipeline(model=hug_obj.formal_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)    
#     formal_outputs=[]
#     def data_load():
#         for row in df['user']:
#             yield str("상냥체 말투로 변환:" + row).strip()

#     for out in formal_pipeline(data_load()):
#         formal_outputs.append([x['generated_text'] for x in out])
#     queue1.put(formal_outputs)

# def gentle_change(queue2, df, hug_obj):
#     gentle_pipeline = make_pipeline(model=hug_obj.gentle_model, tokenizer=hug_obj.tokenizer, device=hug_obj.device)
#     gentle_outputs=[]
#     def data_load():
#         for row in df['user']:
#             yield str("정중체 말투로 변환:" + row).strip()
#     for out in gentle_pipeline(data_load()):
#         gentle_outputs.append([x['generated_text'] for x in out])
#     queue2.put(gentle_outputs)

# def process_1(origin_queue,df, hug_obj):
#     # 최종 반환할 데이터 프레임
#     result_df = pd.DataFrame(columns=['user', 'formal', 'gentle'])
#     result_df['user'] = df['user']
#     # KeyDataset을 활용하기 위한 변환
#     queue1=mp.Queue()
#     p1 = mp.Process(target=formal_change, args=(queue1, df, hug_obj))
#     queue2=mp.Queue()
#     p2 = mp.Process(target=gentle_change, args=(queue2, df, hug_obj))
#     p1.start()
#     p2.start()
#     formal_outputs=queue1.get()
#     gentle_outputs=queue2.get()
#     p1.join()
#     p2.join()
#     result_df['gentle'] = formal_outputs
#     result_df['formal'] = gentle_outputs
    
#     origin_queue.put(result_df)
