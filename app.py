from flask import Flask, request, jsonify, redirect, url_for, Request
from gptResponse import get_OCresponse_from_gpt, get_OCresponse_from_gpt_json, get_OCresponse_from_gpt_o1, get_dog_emotion, get_sentence_emotion, levenshteinDistance, get_deception_analysis, get_OCresponse_from_qwen_turbo
# from flask_cors import CORS
from OC_prompts import name2id
import os
import random
import base64
import boto3

import datetime

app = Flask(__name__)
# CORS(app)


@app.route('/')
def index():
    return "Hello World the local server time is {}\n only for adult response".format(datetime.datetime.now())

@app.route("/botResponseFromOC/<string:charName>", methods=['POST'])
def botResponseFromOC(charName):
    if charName not in name2id.keys():
        return jsonify({"error":"character not found"})
    json_ = request.json
    convLog = json_['convLog']
    if len(convLog)%2 == 0:
        return jsonify({"error":"number of messages must be odd"})
    for i in range(0, len(convLog), 2):
        role = convLog[i]['role']
        if role != 'user':
            return jsonify({"error":"role of odd-numbered message must be user, find "+str(i)+"th to be "+role+"(index starts with 1)"})
    for i in range(1, len(convLog), 2):
        role = convLog[i]['role']
        if role != 'assistant':
            return jsonify({"error":"role of even-numbered message must be assistant, find "+str(i)+"th to be "+role+"(index starts with 1)"})
    print("successfully get convLog")

    total_length = len(convLog[-1]['content'])
    shortenedConvLog = [convLog[-1]]
    for i in range(len(convLog)-3, -1, -2):
        total_length += (len(convLog[i]['content']) + len(convLog[i+1]['content']))
        if total_length > 4000:
            break
        shortenedConvLog.append(convLog[i+1])
        shortenedConvLog.append(convLog[i])
    
    convLog = shortenedConvLog[::-1]
    print(convLog[-1]['content'])

    personalKeyInfo = json_["user"]["personalKeyInfo"]
    if personalKeyInfo is not None:
        personalKeyInfo = "\nHere is some key information of the user: \n" + personalKeyInfo
    else:
        personalKeyInfo = ""

    summary = "" if json_["summary"] is None else "\nSummary of your previous conversation with the user: \n"+json_["summary"]

    response = ""
    if charName == "AmandaAdultCN":
        response = get_OCresponse_from_gpt_json(convLog, charName, personalKeyInfo, summary)
    elif charName == "Nicole":
        model = json_.get("model", "")
        if model =='qwen-turbo':
            response = get_OCresponse_from_qwen_turbo(convLog, charName, personalKeyInfo, summary)
        else:
            response = get_OCresponse_from_gpt_o1(convLog, charName, personalKeyInfo, summary)
    else:
        response = get_OCresponse_from_gpt(convLog, charName, personalKeyInfo, summary)

    return jsonify({"botResponse": response})

@app.route("/botResponseFromOC", methods=['POST'])
def redirectBotResponseFromOC():
    json_ = request.json
    charName = json_.get("character")
    
    if not charName:
        return jsonify({"error": "character field is required in the request body"})

    # Validate charName early if needed
    if charName not in name2id:
        return jsonify({"error": "character not found"})

    # Directly call the original function with charName, simulating internal reroute
    return botResponseFromOC(charName)

@app.route("/dogEmotion", methods=['POST'])
def dogEmotion():
    json_ = request.json
    photo64_array = json_["photo"]
    summary = json_["summary"] 
    keyInfo = json_["keyInfo"]

    temp = get_dog_emotion(photo64_array)
    if temp.emotion != "error":
        return jsonify({
            "emotion":temp.emotion,
            "analysis":temp.analysis,
            "stage1":temp.stage1,
            "stage2":temp.stage2,
            "stage3":temp.stage3,
            "stage1cn":temp.stage1cn,
            "stage2cn":temp.stage2cn,
            "stage3cn":temp.stage3cn,
        })
    else:
        return jsonify({
            "error":"You uploaded an unsupported image. Please make sure your image has of one the following formats: ['png', 'jpeg', 'gif', 'webp'], and convert it to base64",
        })

@app.route("/humanTextToDogVoice", methods=['POST'])
def humanTextToDogVoice():
    json_ = request.json
    text = json_["text"]
    numberOfAudios = min((len(text) +9) // 10, 10)

    sentiment = get_sentence_emotion(text)
    allEmotions = ["happy", "sad", "relaxed", "angry", "excited", "nervous"]
    
    closest_distance = 1e9
    closest_emotion = None
    for emotion in allEmotions:
        tempDistance = levenshteinDistance(sentiment.emotion, emotion)
        if tempDistance < closest_distance:
            closest_distance = tempDistance
            closest_emotion = emotion



    
    s3 = boto3.resource('s3',
        aws_access_key_id="",
        aws_secret_access_key= "")
    myBucket = s3.Bucket('dog-audios')


    object_summaries = list(myBucket.objects.filter(Prefix="dogTest/"+closest_emotion+"/"))
    
    file_names = [obj.key for obj in object_summaries]
    audios_choosed = random.choices(file_names, k=numberOfAudios)

    return jsonify({
        "s3-address": "https://dog-audios.s3.us-west-1.amazonaws.com/",
        "audios":audios_choosed
        })

@app.route("/deceptionAnalysis", methods=['POST'])
def deceptionAnalysis():
    json_ = request.json
    convLog = json_['convLog']
    print("successfully get convLog")
    total_length = len(convLog[-1]['content'])
    shortenedConvLog = [convLog[-1]]
    for i in range(len(convLog)-3, -1, -2):
        total_length += (len(convLog[i]['content']) + len(convLog[i+1]['content']))
        if total_length > 4000:
            break
        shortenedConvLog.append(convLog[i+1])
        shortenedConvLog.append(convLog[i])
    
    response = get_deception_analysis(shortenedConvLog)
    return jsonify({
        "lie_probability": response.lie_probability,
        "confidence": response.confidence,
        "explanation": response.explanation,
        "explanationCN": response.explanationCN
    })


if __name__ == '__main__':
    app.run()