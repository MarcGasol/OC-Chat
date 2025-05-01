from OC_prompts import name2prompt, OPENAI_KEY, ALI_API_KEY, forbidden_words
from openai import OpenAI
import json
import base64
from pydantic import BaseModel


def levenshteinDistance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def get_sentence_emotion(text):
    class SentenceEmotionJSON(BaseModel):
        emotion: str

    client = OpenAI(
        api_key = OPENAI_KEY,
        max_retries = 10
    )

    system='''You are an expert in sentiment classification and dog emotions. You'll be offered with a sentence or several sentences. You should analyze how a dog may feel upon hearing this sentence. Please classify the dog's sentiment reacting to this sentence into one of the following four categories: sad, angry, happy, relaxed, excited, nervous.
    You should also organize your output into the following JSON format:
    {
        "sentiment": "<The classified sentiment of the provided texts. Choose one from: sad, angry, happy, relaxed, excited, nervous.>"
    }
    '''
    response = client.beta.chat.completions.parse(
        model='gpt-4o-mini',
        messages = [
            {"role":"system", "content": system},
            {"role":"user", "content":text},
        ],
        response_format=SentenceEmotionJSON
    )
    temp = response.choices[0].message.parsed
    return temp

def get_dog_emotion(photo64_array, summary='', keyInfo=''):
    
    class DogEmotionOutputJSON(BaseModel):
        emotion: str
        analysis: str
        stage1: str
        stage2: str
        stage3: str
        stage1cn: str
        stage2cn: str
        stage3cn: str
        
    client = OpenAI(
        api_key = OPENAI_KEY,
        max_retries=10
    )

    system = '''You are an expert in distinguishing the emotions of dogs. You'll be offered with an image or several images of a dog. Please classify the emotion of the dog into one of the following six categories: happy, sad, angry, surprise, neutral, others. After that, please give analysis to what the dog might want to do or feel based on your emotion classification and other information in the image, your analysis should be in Chinese. 
    You should also roleplay as the dog and say something according to the emotion and the dog's intention in the analysis in different characteristics. The texts of your roleplay should be in English first and then same thing in Chinese. \n'''
    system += f'''For your reference, these are some background information of the dog. You can base your analysis on these information:
    {keyInfo}
    {summary}
    '''
    system +='''Please organize your output into the following JSON format:
    {"emotion": "<the classified emotion of the dog. Choose one from happy, sad, angry, surprise, neutral, others>", 
     "analysis": "<你对狗狗想要做什么或有什么感觉的分析。几句话就可以了。 >",
     "stage1":"<dog's words as if the dog is a cute little baby who can only speak in simple words.>",
     "stage2":"<dog's words as if the dog is an adolescent who is acting somewhat rebellious towards the master.>",
     "stage3":"<dog's words as if the dog is a mature adult who is sympathetic and caring.>",
     "stage1cn":"<same as stage1 but in Chinese>",
     "stage2cn":"<same as stage2 but in Chinese>",
     "stage3cn":"<same as stage3 but in Chinese>"}
    Please give an output no matter what the picture is.
    '''

    images_input = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{photo64}"}
        } for photo64 in photo64_array
    ]
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What's the emotion of this dog?",
                        }
                    ] + images_input,
                }
        ],
        response_format=DogEmotionOutputJSON
    )
    temp = response.choices[0].message.parsed
    return temp

def get_deception_analysis(convLog):
    class deceptionAnalysis(BaseModel):
        lie_probability: float
        confidence: float
        explanation: str
        explanationCN: str

    client = OpenAI(
        api_key = OPENAI_KEY,
        max_retries=10
    )
        
    dialogue_str = "\n".join([line['role'] + ": " + line['content'] for line in convLog])

    prompt = f"""
    You are an expert in analyzing dialogues for signs of deception. 
    Analyze the following conversation between User and Assistant, they are having a conversation

    Conversation:
    {dialogue_str}

    Identify if User A might be lying. Consider linguistic cues, content consistency, and emotional tone. 
    Return a JSON object with:
    - "lie_probability": (a number between 0 and 1, higher means more likely lying)
    - "confidence": (model confidence in the probability score, a number between 0 and 1, higher means more confident)
    - "explanation": (brief explanation of the result)
    - "explanationCN": (用中文对result做出的分析)

    Remember: Be objective and avoid assumptions beyond the provided text.
    """

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format=deceptionAnalysis
    )
    temp = response.choices[0].message.parsed
    return temp


def get_OCresponse_from_gpt(convLog, charName, personalKeyInfo="", summary=""):

    client = OpenAI(
        api_key = OPENAI_KEY,
        max_retries=10
    )

    system = name2prompt[charName] + personalKeyInfo + summary
    messages = convLog
    response = client.chat.completions.create(
                                messages=[{"role": "system","content": system}] + messages,
                                model="gpt-4o-mini"
                            ).choices[0].message.content
    for word in forbidden_words:
        if word in response:
            return "Hmm. I couldn't make sense of what you just said. You mind repeat that for me?"
    return response

def get_OCresponse_from_gpt_o1(convLog, charName, personalKeyInfo="", summary=""):

    client = OpenAI(
        api_key = OPENAI_KEY,
        max_retries=10
    )

    system = name2prompt[charName] + personalKeyInfo + summary
    messages = convLog
    response = client.chat.completions.create(
                                messages=[{"role": "system","content": system}] + messages,
                                model="gpt-4o"
                            ).choices[0].message.content
    for word in forbidden_words:
        if word in response:
            return "Hmm. 我有点没听懂欸，可以再重复一遍吗？"
    return response

def get_OCresponse_from_gpt_json(convLog, charName, personalKeyInfo="", summary=""):
    client = OpenAI(
        api_key = OPENAI_KEY,
        max_retries=10
    )

    system = name2prompt[charName] + personalKeyInfo + summary
    messages = convLog
    response = client.chat.completions.create(
                                messages=[{"role": "system","content": system}] + messages,
                                response_format={"type": "json_object"},
                                model="gpt-4o-mini"
                            ).choices[0].message.content
    for word in forbidden_words:
        if word in response:
            return "Hmm. I couldn't make sense of what you just said. You mind repeat that for me?"
    d = json.loads(response)
    if "ResponseChinese" not in d:
        return "哈哈哈，你讲话好有意思，可是我听不懂欸~"
    return d['ResponseChinese']

def get_OCresponse_from_qwen_turbo(convLog, charName, personalKeyInfo="", summary=""):
    client = OpenAI(
        # If environment variables are not configured, replace the following line with: api_key="sk-xxx",
        api_key=ALI_API_KEY,
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    system = name2prompt[charName] + personalKeyInfo + summary
    messages = convLog
    response = client.chat.completions.create(
                                messages=[{"role": "system","content": system}] + messages,
                                model="qwen-turbo"
                            ).choices[0].message.content
    for word in forbidden_words:
        if word in response:
            return "哈哈哈，你讲话好有意思，可是我听不懂欸~"
    return response