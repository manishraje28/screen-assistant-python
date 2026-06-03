import threading
import time
import requests
import psutil
import json
import speech_recognition as sr
import gtts
import pygame
import tiktoken
import os
from tempfile import NamedTemporaryFile
import queue
import sys
import uuid
import platform
from groq import Groq
# Platform-specific imports
if platform.system() == "Windows":
    import win32gui

# Constants
USER_ID = 'RUToMGZVt7PZBA8QLz8XSnTCaP84wzZaox9Uk4XEphx'
API_URL = 'https://studycompanion-ai.us01.erebrus.io/9993d6be-0e11-0f0b-b46b-dcccfcd2ab8f/message'
STOP_WORDS = ["stop", "exit", "quit", "bye"]

# Initialize tokenizer
try:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
except Exception as e:
    print(f"❌ Error initializing tokenizer: {e}")
    sys.exit(1)

total_tokens = 0

# Initialize pygame mixer with Ubuntu-compatible settings
try:
    if platform.system() == "Linux":
        # Linux-specific audio initialization
        os.environ['SDL_AUDIODRIVER'] = 'pulse'
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
except Exception as e:
    print(f"⚠️ Audio initialization warning: {e}")
    # Try alternative initialization
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
    except Exception as e2:
        print(f"❌ Audio initialization failed: {e2}")
        print("🔧 Please check your audio system configuration")

# Queue for speech messages
speech_queue = queue.Queue()

def speak_worker():
    """Thread worker for handling speech synthesis."""
    while True:
        text = speech_queue.get()
        try:
            if text == "__STOP__":
                break
            print(f"[Speaking]: {text}")
            with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                filename = temp_file.name
                tts = gtts.gTTS(text=text, lang='en')
                tts.save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            pygame.mixer.music.unload()
            os.remove(filename)
        except Exception as e:
            print(f"⚠️ Speech error: {e}")
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except OSError:
                pass
        finally:
            speech_queue.task_done()

# Start speech thread
threading.Thread(target=speak_worker, daemon=True).start()

def speak(text):
    """Queue text for speech synthesis."""
    print(f"[Agent]: {text}")
    speech_queue.put(text)

def get_application_context(title, process_name):
    """Generate context description based on application type."""
    title_lower = title.lower()
    process_lower = process_name.lower()
    
    # Code editors and IDEs
    if any(name in process_lower for name in ['code', 'visual', 'pycharm', 'intellij', 'sublime', 'atom', 'notepad++']):
        return f"User is coding/developing in {process_name}. Current file or project: {title}. I can help with programming, debugging, or development tasks."
    
    # Web browsers
    elif any(name in process_lower for name in ['chrome', 'firefox', 'edge', 'safari', 'opera']):
        return f"User is browsing the web in {process_name}. Current page: {title}. I can help with web-related questions or research."
    
    # Office applications
    elif any(name in process_lower for name in ['word', 'excel', 'powerpoint', 'outlook', 'onenote']):
        return f"User is working on a document in {process_name}. Document: {title}. I can help with document editing, formatting, or content creation."
    
    # Media applications
    elif any(name in process_lower for name in ['spotify', 'itunes', 'vlc', 'media', 'music']):
        return f"User is using media application {process_name}. Currently: {title}. I can help with media-related questions."
    
    # Terminal/Command line
    elif any(name in process_lower for name in ['cmd', 'powershell', 'terminal', 'bash']):
        return f"User is working in command line/terminal. I can help with command line operations, scripting, or system administration."
    
    # Default case
    else:
        return f"User is working with {process_name}. Current context: {title}. I'm ready to assist with any questions or tasks."

def get_linux_application_context(process_name, cmdline):
    """Generate context description for Linux applications."""
    process_lower = process_name.lower()
    cmdline_str = ' '.join(cmdline) if cmdline else ''
    
    # Python development
    if 'python' in process_lower:
        if 'agent_w.py' in cmdline_str:
            return "User is running the voice assistant application. I can help with voice assistant features, AI interactions, or Python development."
        else:
            return f"User is running Python application. Command: {cmdline_str}. I can help with Python programming, debugging, or development tasks."
    
    # Code editors
    elif any(name in process_lower for name in ['code', 'vim', 'nano', 'emacs']):
        return f"User is editing code/text in {process_name}. I can help with programming, text editing, or development tasks."
    
    # Shell/Terminal
    elif any(name in process_lower for name in ['bash', 'zsh', 'fish', 'sh']):
        return f"User is working in {process_name} shell/terminal. I can help with command line operations, scripting, or system administration."
    
    # Docker
    elif 'docker' in cmdline_str:
        return "User is working with Docker containers. I can help with containerization, deployment, or Docker-related tasks."
    
    # Default case
    else:
        return f"User is working in Linux environment with {process_name}. I'm ready to assist with any Linux-related questions or tasks."

def get_detailed_screen_context(title, process_name, platform, cmdline=None):
    """Generate comprehensive screen context for intelligent responses."""
    title_lower = title.lower() if title else ""
    process_lower = process_name.lower() if process_name else ""
    cmdline_str = ' '.join(cmdline) if cmdline else ""
    
    detailed_info = f"CURRENT SCREEN CONTEXT:\n"
    detailed_info += f"Platform: {platform}\n"
    detailed_info += f"Active Window: {title}\n"
    detailed_info += f"Process: {process_name}\n"
    
    if cmdline:
        detailed_info += f"Command Line: {cmdline_str}\n"
    
    detailed_info += f"\nWHAT THE USER IS CURRENTLY DOING:\n"
    
    # Code editors and IDEs
    if any(name in process_lower for name in ['code', 'visual', 'pycharm', 'intellij', 'sublime', 'atom', 'notepad++']):
        file_type = "unknown file type"
        if any(ext in title_lower for ext in ['.py', 'python']):
            file_type = "Python file"
        elif any(ext in title_lower for ext in ['.js', 'javascript']):
            file_type = "JavaScript file"
        elif any(ext in title_lower for ext in ['.html', '.css']):
            file_type = "web development file"
        elif any(ext in title_lower for ext in ['.cpp', '.c', '.h']):
            file_type = "C/C++ file"
        
        detailed_info += f"The user is actively coding/developing in {process_name}.\n"
        detailed_info += f"Current file/project: {title} ({file_type})\n"
        detailed_info += f"I should help with: programming concepts, debugging, code optimization, syntax help, best practices for this specific file type.\n"
        detailed_info += f"I can see their current work context and should provide specific programming assistance."
    
    # Web browsers
    elif any(name in process_lower for name in ['chrome', 'firefox', 'edge', 'safari', 'opera']):
        detailed_info += f"The user is browsing the web using {process_name}.\n"
        detailed_info += f"Current page/tab: {title}\n"
        
        if any(term in title_lower for term in ['youtube', 'video']):
            detailed_info += f"They appear to be watching videos. I can help with video-related questions, learning from videos, or finding similar content.\n"
        elif any(term in title_lower for term in ['github', 'stackoverflow', 'programming']):
            detailed_info += f"They're looking at programming/development resources. I can help explain code, debug issues, or suggest related topics.\n"
        elif any(term in title_lower for term in ['tutorial', 'learn', 'course']):
            detailed_info += f"They're in learning mode. I can help explain concepts, answer questions about the material, or provide additional examples.\n"
        else:
            detailed_info += f"I can help with web research, explaining content they're reading, or finding related information.\n"
    
    # Office applications
    elif any(name in process_lower for name in ['word', 'excel', 'powerpoint', 'outlook', 'onenote']):
        detailed_info += f"The user is working on a document in {process_name}.\n"
        detailed_info += f"Document: {title}\n"
        detailed_info += f"I can help with: document editing, formatting, content creation, structure, writing assistance, data analysis (if Excel).\n"
        detailed_info += f"I should focus on helping them improve their current document work."
    
    # Python/Programming (Linux specific)
    elif 'python' in process_lower:
        if 'agent_w.py' in cmdline_str:
            detailed_info += f"The user is running their voice assistant application.\n"
            detailed_info += f"Command: {cmdline_str}\n"
            detailed_info += f"I can help with: voice assistant features, AI integrations, Python development, debugging their current application.\n"
        else:
            detailed_info += f"The user is running a Python application.\n"
            detailed_info += f"Command: {cmdline_str}\n"
            detailed_info += f"I can help with: Python programming, debugging, optimization, explaining errors, suggesting improvements.\n"
    
    # Terminal/Command line
    elif any(name in process_lower for name in ['cmd', 'powershell', 'terminal', 'bash', 'zsh', 'fish', 'sh']):
        detailed_info += f"The user is working in command line/terminal ({process_name}).\n"
        if cmdline_str:
            detailed_info += f"Recent command context: {cmdline_str}\n"
        detailed_info += f"I can help with: command line operations, scripting, system administration, file operations, troubleshooting commands.\n"
        detailed_info += f"I should provide specific command examples and explain terminal operations."
    
    # Default case
    else:
        detailed_info += f"The user is working with {process_name}.\n"
        detailed_info += f"Current context: {title}\n"
        detailed_info += f"I should provide assistance relevant to their current application and task.\n"
    
    detailed_info += f"\nIMPORTANT: I should always respond based on what the user is currently doing on their screen. "
    detailed_info += f"My answers should be contextual and directly helpful for their current task."
    
    return detailed_info

def get_active_window_info():
    """Get comprehensive screen context information for intelligent responses."""
    if platform.system() == "Windows":
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return {
                    "title": "Desktop", 
                    "process": "Explorer", 
                    "context": "User is on Windows desktop. No specific application is active.",
                    "detailed_context": "The user is currently on the Windows desktop. They may be looking at desktop icons, wallpaper, or switching between applications. I can help with general Windows tasks, file management, or launching applications."
                }
            
            title = win32gui.GetWindowText(hwnd)
            
            # Get comprehensive process information
            try:
                import win32process
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(process_id)
                process_name = process.name()
                
                # Get enhanced context with more details
                context = get_application_context(title, process_name)
                detailed_context = get_detailed_screen_context(title, process_name, "Windows")
                
                return {
                    "title": title.strip() or "Untitled Window", 
                    "process": process_name,
                    "context": context,
                    "detailed_context": detailed_context,
                    "platform": "Windows"
                }
            except Exception as e:
                return {
                    "title": title.strip() or "Untitled Window", 
                    "process": "Unknown Windows App", 
                    "context": "Generic Windows application",
                    "detailed_context": f"User is working with a Windows application titled '{title}'. I can provide general Windows application support.",
                    "platform": "Windows"
                }
                
        except Exception as e:
            print(f"⚠️ Window detection error: {e}")
            return {
                "title": "Unknown", 
                "process": "Unknown", 
                "context": "Unable to detect current application",
                "detailed_context": "I cannot currently detect what application or window you're using. Please tell me what you're working on so I can provide better assistance.",
                "platform": "Windows"
            }
    else:
        # Enhanced Linux/Ubuntu context detection
        try:
            # Get comprehensive process information
            current_processes = []
            all_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    proc_info = proc.info
                    all_processes.append(proc_info)
                    
                    # Prioritize certain processes for context
                    if proc_info['name'] in ['python3', 'python', 'code', 'vim', 'nano', 'bash', 'zsh', 'fish', 'sh', 'docker']:
                        current_processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if current_processes:
                # Sort by most recent or most relevant
                main_proc = current_processes[0]
                context = get_linux_application_context(main_proc['name'], main_proc.get('cmdline', []))
                detailed_context = get_detailed_screen_context(
                    f"Linux Terminal - {main_proc['name']}", 
                    main_proc['name'], 
                    "Linux",
                    main_proc.get('cmdline', [])
                )
                
                return {
                    "title": f"Linux Terminal - {main_proc['name']}", 
                    "process": main_proc['name'],
                    "context": context,
                    "detailed_context": detailed_context,
                    "platform": "Linux",
                    "cmdline": main_proc.get('cmdline', [])
                }
            else:
                return {
                    "title": "Linux Console", 
                    "process": "shell", 
                    "context": "Linux terminal or console environment",
                    "detailed_context": "User is working in a Linux terminal/console environment. I can help with Linux commands, system administration, file operations, or any Linux-related tasks.",
                    "platform": "Linux"
                }
        except Exception as e:
            print(f"⚠️ Linux process detection error: {e}")
            return {
                "title": "Linux Console", 
                "process": "unknown", 
                "context": "Linux environment - unable to detect specific application",
                "detailed_context": "I'm running in a Linux environment but cannot detect the specific application you're using. Please describe what you're working on so I can provide targeted assistance.",
                "platform": "Linux"
            }

def query_agent(context, include_screen_context=True):
    """Send context to API with comprehensive screen awareness for intelligent responses."""
    try:
        # Always include comprehensive screen context for better responses
        enhanced_context = context
        screen_context_info = ""
        
        if include_screen_context:
            try:
                screen_info = get_active_window_info()
                
                # Add comprehensive screen context to every query
                screen_context_info = f"""

=== CURRENT USER SCREEN CONTEXT ===
{screen_info['detailed_context']}

USER'S CURRENT ENVIRONMENT:
- Platform: {screen_info.get('platform', 'Unknown')}
- Active Application: {screen_info['process']}
- Window Title: {screen_info['title']}
- Context: {screen_info['context']}

INSTRUCTION: Based on the above screen context, please provide a response that is specifically relevant to what the user is currently doing. If they ask about something unrelated to their current screen, acknowledge their current context but still answer their question. Always be helpful and contextual.

USER'S QUESTION/REQUEST:
{context}

RESPONSE GUIDELINES:
- Consider what they're currently working on
- Provide specific help related to their current application/task
- If it's a general question, relate it to their current context when possible
- Be direct and actionable
"""
                
                enhanced_context = screen_context_info
                
            except Exception as e:
                print(f"⚠️ Context enhancement error: {e}")
                enhanced_context = f"User Question: {context}\n\nNote: Unable to detect current screen context, providing general assistance."
        
        print(f"🔍 Sending enhanced query with screen context...")
        
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "text": enhanced_context,
                "userId": USER_ID,
                "voice_mode": "false"
            },
            timeout=20  # Increased timeout for complex context queries
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0 and "text" in data[0]:
            return data[0]["text"]
        elif isinstance(data, dict) and "text" in data:
            return data["text"]
        return "No response text."
    except Exception as e:
        return f"⚠️ Error: {e}"

def count_tokens(text):
    """Count tokens in text using tiktoken."""
    try:
        return len(tokenizer.encode(text))
    except Exception:
        return 0

def listen_and_respond(recognizer):
    """Listen for audio input and respond with speech."""
    global total_tokens
    with sr.Microphone() as source:
        print("\n🎤 Speak... (say 'stop' or press Ctrl+C to exit)")
        recognizer.adjust_for_ambient_noise(source, duration=0.2)
        try:
            audio = recognizer.listen(source, phrase_time_limit=6, timeout=5)
        except sr.WaitTimeoutError:
            print("❗ No speech detected within timeout.")
            speak("Please speak to continue.")
            return True

        try:
            user_input = recognizer.recognize_google(audio)
            input_tokens = count_tokens(user_input)
            print(f"🗣️ You said: {user_input} (🔢 {input_tokens} tokens)")

            if user_input.lower().strip() in STOP_WORDS:
                print("🛑 Exit word detected.")
                speak("Okay, stopping.")
                return False

            response = query_agent(user_input)
            output_tokens = count_tokens(response)
            print(f"🤖 AI: {response} (🔢 {output_tokens} tokens)")
            speak(response)
            total_tokens += input_tokens + output_tokens
            print(f"📊 Total tokens used this session: {total_tokens}")
            return True
        except sr.UnknownValueError:
            print("❗ Couldn't understand.")
            speak("Sorry, I didn't catch that.")
            return True
        except sr.RequestError as e:
            print(f"🔌 STT Error: {e}")
            speak("Microphone or speech service error.")
            return True

class ConsoleAssistant:
    def __init__(self):
        print("🧠 Enhanced Context-Aware Console Assistant Starting...")
        print("🔍 This assistant can see what you're working on and provide contextual help!")
        print("💡 Features:")
        print("   • Screen context awareness (what app you're using)")
        print("   • Intelligent responses based on your current activity")
        print("   • Enhanced help for coding, browsing, documents, and more")
        print("   • Cross-platform support (Windows & Linux)")
        
        self.recognizer = sr.Recognizer()
        self.running = True

        # Start background threads
        threading.Thread(target=self.update_window_loop, daemon=True).start()
        threading.Thread(target=self.listen_loop, daemon=True).start()
        
        # Send initial context with detailed screen awareness
        try:
            initial_context = get_active_window_info()
            welcome_msg = f"Enhanced Voice Assistant activated! I can see you're currently using {initial_context['process']} on {initial_context.get('platform', 'your system')}."
            
            print(f"[Welcome]: {welcome_msg}")
            print(f"[Screen Context]: {initial_context['context']}")
            print(f"[Detailed Analysis]: I have comprehensive awareness of your current screen and activity")
            
            # Give a context-aware greeting
            contextual_greeting = f"Hello! I can see you're working with {initial_context['process']}. I understand your current context and I'm ready to provide specific help based on exactly what you're doing on your screen right now."
            speak(contextual_greeting)
            
        except Exception as e:
            print(f"⚠️ Initial context error: {e}")
            speak("Hello! I'm your enhanced screen-aware voice assistant. I can analyze what you're currently doing and provide contextual help.")

    def update_window_loop(self):
        """Monitor active window and provide comprehensive context awareness."""
        last_context = ""
        context_change_count = 0
        
        while self.running:
            try:
                info = get_active_window_info()
                current_context = f"{info['title']} - {info['process']}"
                
                print(f"🪟 Active Window: '{info['title']}'")
                print(f"🔧 Process: {info['process']} ({info.get('platform', 'Unknown')} platform)")
                print(f"📋 Context: {info['context']}")
                print(f"🔍 Screen Analysis: Ready to provide contextual assistance based on current activity")
                
                # Show detailed context periodically
                if hasattr(info, 'detailed_context'):
                    print(f"💡 Detailed Context Available: I can see exactly what you're working on")
                
                # Only respond to significant context changes
                if (current_context != last_context and 
                    info["title"] not in ["Unknown", "No Active Window", "Linux Console", "Desktop"] and
                    context_change_count < 2):  # Reduced automatic responses
                    
                    last_context = current_context
                    context_change_count += 1
                    
                    # Create a context-aware welcome message
                    context_message = f"""
                    I can see you've switched to working with {info['title']} in {info['process']}.
                    
                    Based on your current screen, I understand you're: {info['context']}
                    
                    Please provide a brief, encouraging message (under 25 words) that shows I understand 
                    what they're currently doing and offer relevant assistance.
                    """
                    
                    print(f"[Context Change]: New application detected - {info['process']}")
                    reply = query_agent(context_message.strip(), include_screen_context=False)
                    
                    # Only speak meaningful context updates
                    if reply and not reply.startswith("⚠️") and len(reply.strip()) > 10:
                        speak(f"I can see you're now working with {info['process']}. {reply}")
                
                time.sleep(10)  # Longer interval for less spam, more meaningful updates
                
            except Exception as e:
                print(f"⚠️ Window monitoring error: {e}")
                time.sleep(10)

    def listen_loop(self):
        """Continuously listen for audio input."""
        while self.running:
            if not listen_and_respond(self.recognizer):
                self.running = False
                break
            time.sleep(0.1)

    def run(self):
        try:
            print("\n🎤 Enhanced Voice Assistant Ready!")
            print("💬 I can now understand what you're working on and provide contextual help.")
            print("🗣️ Just speak naturally - I'll respond based on your current activity!")
            print("⌨️ You can also press Ctrl+C to exit anytime.")
            
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Stopped by user.")
            self.running = False
        finally:
            self.running = False
            speech_queue.put("__STOP__")
            pygame.mixer.quit()

if __name__ == "__main__":
    try:
        app = ConsoleAssistant()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Stopped by user.")
        speak("Goodbye!")
        app.running = False
        speech_queue.put("__STOP__")
        pygame.mixer.quit()