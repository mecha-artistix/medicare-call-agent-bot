import os
from flask import Flask, render_template_string, request, jsonify
from openai import OpenAI
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

# HTML template for the web page
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

        let conversation = [];

        sendButton.addEventListener('click', () => {
            const userText = userInput.value;
            if (userText.trim() === '') return;

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
                const botMessage = data.response;

                // Display bot's message
                const botMessageDiv = document.createElement('div');
                botMessageDiv.className = 'message bot';
                botMessageDiv.textContent = 'Bot: ' + botMessage;
                messagesDiv.appendChild(botMessageDiv);

                // Scroll to the bottom
                messagesDiv.scrollTop = messagesDiv.scrollHeight;

                // Add bot's message to conversation
                conversation.push({"role": "assistant", "content": botMessage});
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

# Helper function to determine greeting based on server time
def get_greeting():
    current_hour = datetime.now().hour
    if current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"

# Keep track of the current step
conversation_step = 0

# Define the route for the homepage
@app.route('/')
def index():
    return render_template_string(html_template)

# Endpoint to get response from GPT-4o Mini
@app.route('/get_response', methods=['POST'])
def get_response():
    global conversation_step
    data = request.get_json()
    conversation = data['conversation']
    
    # Define different system prompts for each step
    system_prompts = [
        {
            "role": "system",
            "content": "You are an outbound caller. First, greet the user and ask how they are doing. Wait for their response before proceeding."
        },
        {
            "role": "system",
            "content": "Now ask if the user has Medicare Part A or Part B."
        },
        {
            "role": "system",
            "content": "If the user does not have Medicare, ask if their age is between 65 and 85."
        },
        {
            "role": "system",
            "content": "If the user is unsure, ask if they have a red, white, and blue Medicare card."
        },
        {
            "role": "system",
            "content": "If their age is less than 65, ask if they qualify due to a disability."
        }
    ]

    # Insert the system prompt for the current step
    if conversation_step < len(system_prompts):
        conversation.insert(0, system_prompts[conversation_step])

    # Call the OpenAI API gpt-4o-mini-2024-07-18
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=conversation,
            max_tokens=1000,
            temperature=0.7
        )

        bot_message = response.choices[0].message.content

        # Increment conversation step to move to the next question
        conversation_step += 1

        return jsonify({'response': bot_message})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': 'Sorry, there was an error processing your request.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=82, debug=True)

