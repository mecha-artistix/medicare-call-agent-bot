import os
from flask import Flask, render_template_string, request, jsonify
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
systemFile = os.path.join(os.path.dirname(__file__), 'promptEngr')

with open(systemFile, 'r') as file:
    systemMessage = file.read()


app = Flask(__name__)


html_template = '''
<!DOCTYPE html>
<html>
    <head>
        <title>Medicare Qualifier Bot</title>
        <style>
            body { font-family: Arial, sans-serif; }
            #chatbox { width: 80%; margin: 20px auto; }
            #messages { border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: scroll; }
            #user-input { width: 100%; padding: 10px; }
            #send-button { padding: 10px 20px; }
            .message { margin: 10px 0; }
            .user { color: blue; }
            .bot { color: green; }
        </style>
    </head>
    <body>
        <div id="chatbox">
            <h1>Medicare Qualifier Bot</h1>
            <div id="messages"></div>
            <input type="text" id="user-input" placeholder="Type your message here" autocomplete="off"/>
            <button id="send-button">Send</button>
        </div>

        <script>
            const messagesDiv = document.getElementById('messages');
            const userInput = document.getElementById('user-input');
            const sendButton = document.getElementById('send-button');
            window.onload = function() {
                userInput.focus();
                };
            let conversation = [];
            sendButton.addEventListener('click', () => {
                const userText = userInput.value;
                // if (userText.trim() === '') return;

                // Display user's message
                const userMessageDiv = document.createElement('div');
                userMessageDiv.className = 'message user';
                userMessageDiv.textContent = 'You: ' + userText;
                messagesDiv.appendChild(userMessageDiv);

                // Scroll to the bottom
                messagesDiv.scrollTop = messagesDiv.scrollHeight;

                // Clear input
                userInput.value = '';

                // Add user's message to conversation
                conversation.push({"role": "user", "content": userText});

                // Send message to server
                fetch('/get_response', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({'conversation': conversation})
                })
                .then(response => response.json())
                .then(data => {
                    console.log(data)
                    const botMessage = data.response;
                  
                    // Display bot's message
                    const botMessageDiv = document.createElement('div');
                    botMessageDiv.className = 'message bot';
                    botMessageDiv.textContent = botMessage;
                    messagesDiv.appendChild(botMessageDiv);
                    // Display detected intent
                    const userIntent = data.intent;
                    const intentDiv = document.createElement('div');
                    intentDiv.className = 'message intent';
                    intentDiv.textContent = 'Intent -'+userIntent;
                    messagesDiv.appendChild(intentDiv);
                    // Scroll to the bottom
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;

                    // Add bot's message to conversation
                    conversation.push({"role": "assistant", "content": botMessage});
                    console.log(conversation)
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            });

            // Allow pressing Enter to send message
            userInput.addEventListener('keyup', (event) => {
                if (event.key === 'Enter') {
                    sendButton.click();
                }
            });
        </script>
    </body>
</html>
'''


def get_greeting():
    current_hour = datetime.now().hour
    if current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"




@app.route('/', methods=['GET'])
def index():
    return render_template_string(html_template)



@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.get_json()
    conversation = data['conversation']

    # Add greeting and outbound call intro without asking open-ended questions
    if len(conversation) == 1:
        greeting = get_greeting()
    
    system_message = {
        "role": "system",
        "content": systemMessage
        }
    
    conversation.insert(0, system_message)

    # Call the OpenAI API gpt-4o-mini-2024-07-18
    try:
        bot_response = client.chat.completions.create(
            model="gpt-4o",
            messages=conversation,
            max_tokens=1000,
            temperature=0.8
        )
       
        bot_response = bot_response.choices[0].message.content
        print(bot_response)
        response_part, intent = extract_response_and_intent(bot_response)

        if not response_part:
            response_part = bot_response        
        

        return jsonify({'response': response_part, 'intent': intent})
        # return jsonify({'response': bot_message})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': 'Sorry, there was an error processing your request.'})




def extract_response_and_intent(bot_message):
    # Regex patterns for response and intent
    
    response_pattern = re.compile(r'(?i)response:\s*(.*?)(?=\n*\s*intent:|$)', re.DOTALL)
    intent_pattern = re.compile(r'(?i)intent:\s*(.*)', re.DOTALL)

    # Extract response and intent
    response_match = response_pattern.search(bot_message)
    intent_match = intent_pattern.search(bot_message)

    # Get the matched strings or return "Not found" if not detected
    response = response_match.group(1).strip() if response_match else None
    intent = intent_match.group(1).strip() if intent_match else None
    
    return response, intent


if __name__ == '__main__':
    app.run(debug=True)