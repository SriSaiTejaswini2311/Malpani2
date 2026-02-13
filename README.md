# Dr. Malpani's AI Assistant (IVF Consultation Engine)

A conversational AI engine designed to simulate an initial IVF consultation, gathering patient history, validating test reports, and reasoning about the case.

## Features

- **Conversational Intake**: Collects detailed patient history (Age, Duration, Previous Pregnancies, Treatments).
- **Document Verification**: Validates uploaded medical reports (e.g., Semen Analysis, AMH) against date criteria.
- **Phase 1 & 2 Workflow**: 
  - **Phase 1**: History taking and test identification.
  - **Phase 2**: Document upload, date extraction, and validity checking.

## Prerequisites

- **Python 3.10+**
- **Node.js 16+** (and `npm`)
- **Google Gemini API Key** (for embeddings/extraction features)

## Setup Instructions

### 1. Backend Setup (Python/FastAPI)

Navigate to the `backend` directory:
```bash
cd backend
```

Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Set up Environment Variables:
1.  Copy `.env.example` to a new file named `.env`:
    ```bash
    cp .env.example .env
    # Or manually create .env and copy the contents
    ```
2.  Open `.env` and replace `YOUR_API_KEY_HERE` with your actual Google Gemini API Key.

Run the Backend Server:
```bash
uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

### 2. Frontend Setup (React)

Open a new terminal and navigate to the `frontend` directory:
```bash
cd frontend
```

Install dependencies:
```bash
npm install
```

Start the React Development Server:
```bash
npm start
```
The application will open at `http://localhost:3000`.

## Usage

1.  Start both backend and frontend servers.
2.  Open the frontend in your browser.
3.  Chat with the AI to provide your history.
4.  When prompted, upload your test reports (PDF/Images). The system will check their validity (e.g., Semen Analysis valid for 90 days, AMH for 1 year).

## Troubleshooting

-   **Session Reset**: The current implementation uses in-memory session storage. **Restarting the backend server will reset the conversation.** You must refresh the browser page if you restart the backend.
-   **API Errors**: Ensure your `GOOGLE_API_KEY` is valid in the `.env` file.
