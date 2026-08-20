import random
import json
with open("C:/Users/newle/OneDrive/Desktop/CAI-S2-G1-AI/src/python/session-4/chatbot/data.json","r") as file:
    responses = json.load(file)
def get_response(user_input):
    for key in responses:
        if key in user_input:
            return random.choice(responses[key])
    return random.choice(responses["default"])