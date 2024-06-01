from transformers import (
    T5TokenizerFast,
    T5ForConditionalGeneration,
    pipeline
    )
import torch

class hugging():
    # 허깅페이스 레포 주소
    def __init__(self):
        cache_dir = "./hugging_face"
        origin_model_path="paust/pko-t5-base"
        formal_model_path='9unu/formal_speech_translation'
        gentle_model_path='9unu/gentle_speech_translation'
    
        self.origin_model = T5ForConditionalGeneration.from_pretrained(origin_model_path, cache_dir=cache_dir)
        self.tokenizer = T5TokenizerFast.from_pretrained(formal_model_path, cache_dir=cache_dir)
        self.formal_model = T5ForConditionalGeneration.from_pretrained(formal_model_path, cache_dir=cache_dir)
        self.gentle_model = T5ForConditionalGeneration.from_pretrained(gentle_model_path, cache_dir=cache_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
# 파이프라인 실행 -> 변환 문장 return
def make_pipeline(model, tokenizer, device):
    nlg_pipeline = pipeline('text2text-generation', model=model, tokenizer=tokenizer, device=device, max_length=60) # "auto" -> 자동으로 분산
    return nlg_pipeline
    
# def generate_text(pipe, text, target_style, num_return_sequences=1, max_length=60):
#     style_map = {
#                 'user' : '사용자',
#                 'formal': '상냥체',
#                 'gentle' : '정중체',
#                 'random' : '이상한'
#                 }
#     target_style_name = style_map[target_style]
#     text = f"{target_style_name} 말투로 변환:{text}"
#     out = pipe(text, num_return_sequences=num_return_sequences, max_length=max_length)
#     return [x['generated_text'] for x in out]
