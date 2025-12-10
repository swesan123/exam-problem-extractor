# Usage Guide

Complete guide on how to set up and use the Exam Problem Extractor application.

## Prerequisites

- Python 3.10 or higher
- Node.js 16+ and npm (for frontend)
- OpenAI API key

## Backend Setup

### 1. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
VECTOR_DB_PATH=./vector_store/chroma_index
VECTOR_DB_TYPE=chroma
LOG_LEVEL=INFO
```

### 3. Run Backend Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

The backend API will be available at `http://localhost:8000`

API documentation (Swagger UI) is available at `http://localhost:8000/docs`

## Frontend Setup

### 1. Install Node Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `frontend/.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Run Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Using the Application

### 1. Access the Application

Open your browser and navigate to `http://localhost:3000`

### 2. Create a Class

1. Click on **"Classes"** in the navigation bar
2. Click **"Create Class"** button
3. Fill in the form:
   - **Name** (required): e.g., "Math 101"
   - **Subject** (optional): e.g., "Mathematics"
   - **Description** (optional): e.g., "Introduction to Calculus"
4. Click **"Create"**

### 3. Generate Questions

1. Click on **"Generate"** in the navigation bar
2. **Option A - Upload Image:**
   - Click "Upload Image" and select an image file (PNG, JPG, JPEG)
   - The system will automatically extract text using OCR
   
   **Option B - Paste Text:**
   - Paste extracted text directly into the "Or Enter OCR Text" field

3. **Select Class (Optional):**
   - Choose a class from the dropdown to automatically save the generated question

4. **Options:**
   - Check "Include solution" if you want the solution included in the generated question

5. Click **"Generate Question"**

6. The generated question will appear in the right panel
   - If you selected a class, you'll see a success message confirming the question was saved

### 4. View Questions in a Class

1. Go to **"Classes"** page
2. Click **"View Questions"** on any class card
3. You'll see all questions for that class
4. Use the search box to filter questions

### 5. Export Questions

1. Navigate to a class's questions page (see step 4 above)
2. Select an export format from the dropdown:
   - **TXT**: Plain text file
   - **PDF**: PDF document
   - **DOCX**: Microsoft Word document
   - **JSON**: JSON data file
3. The file will automatically download

### 6. Manage Classes

- **Edit Class**: Click the edit icon (pencil) on any class card
- **Delete Class**: Click the delete icon (trash) on any class card
  - ⚠️ Warning: This will also delete all questions in the class

## API Endpoints (Direct Usage)

If you prefer to use the API directly:

### Health Check
```bash
curl http://localhost:8000/health
```

### Create Class
```bash
curl -X POST http://localhost:8000/api/classes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Math 101",
    "subject": "Mathematics",
    "description": "Introduction to Calculus"
  }'
```

### List Classes
```bash
curl http://localhost:8000/api/classes
```

### Generate Question
```bash
curl -X POST http://localhost:8000/generate \
  -F "image_file=@screenshot.png" \
  -F "class_id=class_123" \
  -F "include_solution=true"
```

### List Questions in Class
```bash
curl http://localhost:8000/api/questions/classes/class_123/questions
```

### Export Questions
```bash
curl http://localhost:8000/api/classes/class_123/export?format=pdf \
  --output questions.pdf
```

## Workflow Example

1. **Create Classes** for different subjects/courses
   - Example: "Math 101", "Physics 201", "Chemistry Lab"

2. **Generate Questions** from screenshots or text
   - Upload exam screenshots
   - Select the appropriate class
   - Generate questions with or without solutions

3. **Review Questions** in the class questions page
   - Search for specific questions
   - Review generated content

4. **Export Questions** when ready
   - Choose your preferred format
   - Download and use in your exams

## Tips

- **Image Quality**: Better quality images produce better OCR results
- **Class Organization**: Create separate classes for different subjects or exam types
- **Solutions**: Use the "Include solution" option when generating practice questions
- **Export Formats**: 
  - Use TXT for simple text files
  - Use PDF for formatted documents
  - Use DOCX for editable Word documents
  - Use JSON for programmatic access

## Troubleshooting

### Backend Issues

**Port already in use:**
```bash
# Change port
uvicorn app.main:app --reload --port 8001
```

**OpenAI API errors:**
- Verify your API key is correct in `.env`
- Check your OpenAI account has sufficient credits
- Ensure you're using a valid model (gpt-4o)

**Database errors:**
- Ensure the `data/` directory exists and is writable
- Check database file permissions

### Frontend Issues

**API connection errors:**
- Verify backend is running on port 8000
- Check `VITE_API_BASE_URL` in `frontend/.env`
- Ensure CORS is configured correctly

**Build errors:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Docker Usage (Alternative)

### Run with Docker Compose

```bash
# Set environment variables in .env file
cp .env.example .env
# Edit .env with your OpenAI API key

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Backend: `http://localhost:8000`  
Frontend: Build and serve separately or use nginx reverse proxy

## Next Steps

- Explore the API documentation at `http://localhost:8000/docs`
- Check the [Deployment Guide](DEPLOYMENT.md) for production setup
- Review the [Design Document](../DESIGN.md) for architecture details

