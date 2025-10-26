# 🌍 AI Language Learning Assistant

An interactive web application that helps you learn languages through video content using Reka's Vision AI API. Watch videos, ask questions about specific scenes, and get instant explanations with translations powered by advanced AI.

![Language Learning](https://img.shields.io/badge/AI-Language%20Learning-blue)
![Python](https://img.shields.io/badge/Python-3.12+-green)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey)
![Reka AI](https://img.shields.io/badge/Powered%20by-Reka%20AI-purple)

## ✨ Features

### 🎥 **Video-Based Learning**
- Watch videos directly in the interface with native HTML5 player
- **Automatic timestamp capture** - Questions include the current video timestamp for context-aware responses
- Jump to specific timestamps from AI responses with clickable time markers
- Responsive video player (75% width, expands to 60% when insights panel opens)
- Full playback controls with progress tracking

### 💬 **AI-Powered Chat Interface**
- Ask questions about video content in natural language
- **Context-aware responses** - AI knows exactly which scene you're asking about
- **Smart suggestion chips** - Quick-access questions that adapt to video timestamp
- Get explanations of phrases, idioms, and expressions
- Receive automatic English translations for non-English content
- Conversation history maintained throughout session
- Beautiful gradient UI with smooth animations

### 🎨 **Modern UI/UX**
- **Collapsible insights panel** - Toggle with floating 💡 button
- **Suggestion chips** with hover effects and animations
- Responsive design that works on desktop and mobile
- Purple gradient theme with smooth transitions
- Clean, distraction-free learning environment
- Video resizes smoothly when panels open/close

### 🧠 **Intelligent Response Formatting**
- Automatically parses structured JSON responses with sections
- Formats video clip timestamps as **⏱️ [start-end]**: description
- Converts markdown to HTML for rich text display
- Handles both plain text and structured responses gracefully

### 🌐 **Multi-Language Support**
- Automatic language detection from video content
- English translations provided for all foreign phrases
- Grammar and pronunciation insights
- Cultural context explanations

## 🏗️ Project Structure

```
roast_my_life/
├── src/
│   ├── api/                      # External API integrations
│   │   ├── reka_vision.py       # Reka Vision API client
│   │   └── reka_research.py     # Reka Research API client
│   ├── routes/                   # Flask route blueprints
│   │   ├── main.py              # Home page routes
│   │   ├── video.py             # Video listing API
│   │   ├── language.py          # Language analysis API
│   │   └── chat.py              # Chat interface & API
│   ├── services/                 # Business logic layer
│   │   ├── video_service.py     # Video fetching & caching
│   │   ├── analysis_service.py  # Response parsing & formatting
│   │   └── markdown_service.py  # Markdown to HTML conversion
│   ├── models/                   # Data models
│   │   └── video_analysis.py    # Pydantic models for video analysis
│   ├── templates/                # Jinja2 HTML templates
│   │   ├── index.html           # Home page
│   │   ├── form.html            # Video selection page
│   │   └── chat.html            # Chat interface (main app)
│   ├── static/                   # Static assets
│   │   ├── css/
│   │   │   └── style.css        # Stylesheets
│   │   └── images/              # Image assets
│   ├── config.py                 # Application configuration
│   └── app.py                    # Flask app initialization
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── .env-sample                   # Environment variables template
└── README.md                     # This file
```

### Architecture Highlights

- **Blueprint-based routing** - Modular route organization for scalability
- **Service layer pattern** - Business logic separated from routes
- **Pydantic models** - Type-safe data validation
- **Response parsing** - Handles both structured JSON and plain text responses
- **Caching** - Video list cached for 60 seconds to reduce API calls
- **Environment-based config** - Easy deployment across environments

## Prerequisites

- Python 3.12 or higher
- pip (Python package manager)

or

- Docker/ Podman

## Installation & Setup

### Option 1: Run Locally

1. **Clone the repository**
   ```bash
   git clone https://github.com/reka-ai/api-examples-python.git
   cd roast_my_life
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   API_KEY=your_reka_api_key_here
   BASE_URL=https://vision-agent.api.reka.ai
   PORT=8111
   DEBUG=false
   ```

5. **Run the application**
   ```bash
   python run.py
   ```
   Or directly:
   ```bash
   python src/app.py
   ```

6. **Open your browser**
   Navigate to: `http://localhost:8111`

### Option 2: Run with Docker

1. **Build the Docker image**
   ```bash
   docker build -t roast-my-life .
   ```

2. **Create a .env file (or reuse the provided `.env-sample`)**
   Place it in this folder (`roast_my_life/.env`). Example:
   ```env
   API_KEY=your_actual_api_key_here
   BASE_URL=https://vision-agent.api.reka.ai
   ```

3. **Run the container passing your env file (recommended)**
   ```bash
   docker run --env-file .env -p 8111:8111 roast-my-life
   ```

   Alternatively, you can pass variables individually:
   ```bash
   docker run -e API_KEY=xxxx -e BASE_URL=https://vision-agent.api.reka.ai -p 8111:8111 roast-my-life
   ```

   For CI-only scenarios, you may inject values during build (not for secrets):
   ```bash
   docker build --build-arg API_KEY=placeholder --build-arg BASE_URL=https://vision-agent.api.reka.ai -t roast-my-life .
   ```
   Note: build args become part of the image metadata layers; avoid using them for real secrets.

4. **Open your browser**
   Navigate to: `http://localhost:8111`

## ⚙️ Environment Variables

Create a `.env` file in the root directory (use `.env-sample` as template):

```env
# Required: Reka API Key
API_KEY=your_reka_api_key_here

# Required: Base URL for Reka Vision API
BASE_URL=https://vision-agent.api.reka.ai

# Optional: Server configuration
PORT=8111                    # Default: 8111
HOST=0.0.0.0                 # Default: 0.0.0.0
DEBUG=false                  # Default: false

# Optional: Custom endpoints (usually not needed)
REKA_VIDEO_QA_ENDPOINT=https://vision-agent.api.reka.ai/qa/chat
```

### Configuration Details

- **API_KEY**: Your Reka AI API key (get one free at https://link.reka.ai/free)
- **BASE_URL**: The base URL for Reka's Vision API endpoints
- **PORT**: The port the Flask server will run on
- **DEBUG**: Enable Flask debug mode (set to `true` for development)
- **REKA_VIDEO_QA_ENDPOINT**: Custom endpoint for video Q&A (auto-generated from BASE_URL if not set)

Runtime precedence: values passed via `docker run -e/--env-file` override any build-time defaults. The app loads `.env` automatically via `python-dotenv`.

## 🚀 Usage

### Getting Started

1. **Launch the application**
   - Start the server using `python run.py`
   - Open your browser to `http://localhost:8111`

2. **Browse available videos**
   - The home page displays a grid of available videos from the Reka Vision API
   - Each video shows a thumbnail and title
   - Click on any video to start learning

3. **Interactive chat interface**
   - The video player takes up 75% of the screen
   - Use the suggestion chips below the video for quick questions:
     - "What language is this?"
     - "Translate this scene"
     - "Cultural context"
     - "Grammar help"
   - Or type your own questions in the input box

4. **Context-aware learning**
   - **Play the video** and pause at any interesting scene
   - **Ask a question** - the app automatically captures the current timestamp
   - The AI will analyze that specific scene and provide context-aware answers
   - Questions show timestamps like: "What does this mean? (at 1:23)"

5. **Explore insights (optional)**
   - Click the floating 💡 button in the top-right corner
   - View automatically extracted phrases and learning opportunities
   - The video resizes to 60% to make room for the insights panel
   - Click 💡 again or the X button to close

### Tips for Best Results

- **Pause at key moments** - Stop the video when you hear something interesting
- **Ask specific questions** - The more specific your question, the better the AI can help
- **Use timestamps** - The automatic timestamp capture helps the AI understand context
- **Try suggestion chips** - They're designed to work well with video content
- **Explore different languages** - The app works with any language in your videos

### Troubleshooting

- **No videos appear**: Verify your `API_KEY` and `BASE_URL` in `.env`
- **Chat not working**: Check that the Reka API endpoint is accessible
- **Video won't play**: Ensure the video URL is valid and accessible
- **Timestamp shows null**: Make sure the video has started playing (currentTime > 0)


## 🛠️ Technical Details

### Key Technologies

- **Flask** - Lightweight Python web framework
- **Reka Vision API** - Advanced video understanding and Q&A
- **Pydantic** - Data validation and type safety
- **Python-Markdown** - Markdown to HTML conversion
- **python-dotenv** - Environment variable management

### API Integration

The app integrates with two Reka AI endpoints:

1. **Video QA API** (`/qa/chat`)
   - Handles video-based question answering
   - Receives conversation history and video context
   - Returns structured responses with sections and timestamps

2. **Research API** (`/v1/chat`)
   - Optional web research capabilities
   - Can fact-check claims and provide additional context

### Response Handling

The app intelligently handles different response formats:

- **Structured JSON with sections**: Automatically parsed and formatted
- **Video clip timestamps**: Displayed as clickable time markers
- **Plain text/markdown**: Rendered directly as HTML
- **Fallback handling**: Gracefully handles parsing errors

## 🤝 Contributing

Contributions are welcome! This is an educational sample project showcasing Reka's Vision API capabilities.

### Areas for Improvement

- Additional language learning features
- More sophisticated UI animations
- Offline video support
- User authentication and progress tracking
- Export conversation history
- Custom vocabulary lists

### Guidelines

- Follow existing code structure and patterns
- Add comments for complex logic
- Test with multiple video types and languages
- Keep the learning experience positive and educational

## 📝 License

Educational / sample use. Adapt freely for your own projects.

## 🔗 Resources

- **Reka Vision API Docs**: https://docs.reka.ai/vision
- **Get a FREE API Key**: https://link.reka.ai/free
- **Reka AI Website**: https://www.reka.ai

---

**Built with ❤️ using Reka AI** - Part of Reka's code samples to help you learn while having fun!