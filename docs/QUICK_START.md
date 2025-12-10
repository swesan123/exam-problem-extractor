# Quick Start Guide

## Application is Running! 🎉

Your application is now running at **http://localhost:8000**

## Next Steps

### 1. Explore the Interactive API Documentation

Open your browser and visit:

- **Swagger UI (Interactive Docs)**: http://localhost:8000/docs
  - Try out all endpoints directly from your browser
  - See request/response schemas
  - Test with real data

- **ReDoc (Alternative Docs)**: http://localhost:8000/redoc
  - Clean, readable documentation format

### 2. Test the Health Check

```bash
curl http://localhost:8000/health
```

Or visit: http://localhost:8000/health

### 3. Test the Root Endpoint

```bash
curl http://localhost:8000/
```

Or visit: http://localhost:8000/

### 4. Test the OCR Endpoint

Extract text from an image:

```bash
curl -X POST "http://localhost:8000/ocr" \
  -F "file=@/path/to/your/image.png"
```

**Requirements:**
- Image file (PNG, JPG, or JPEG)
- Max size: 10MB
- You need a valid OpenAI API key in your `.env` file

### 5. Test the Embed Endpoint

Store exam questions in the vector database:

```bash
curl -X POST "http://localhost:8000/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Find the derivative of f(x) = x^2 + 3x",
    "metadata": {
      "source": "exam_2023",
      "page": 1,
      "chunk_id": "chunk_001"
    }
  }'
```

### 6. Test the Retrieve Endpoint

Search for similar exam questions:

```bash
curl -X POST "http://localhost:8000/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "derivative problems",
    "top_k": 5
  }'
```

### 7. Test the Generate Endpoint (Full Pipeline)

Generate an exam question from an image:

```bash
curl -X POST "http://localhost:8000/generate" \
  -F "image_file=@/path/to/your/problem_image.png" \
  -F "include_solution=false"
```

Or with pre-extracted text:

```bash
curl -X POST "http://localhost:8000/generate" \
  -F "ocr_text=Find the derivative of x^2" \
  -F "include_solution=false"
```

## Using the Interactive Docs (Recommended)

1. **Open http://localhost:8000/docs in your browser**

2. **Click on any endpoint** (e.g., `POST /ocr`)

3. **Click "Try it out"**

4. **Fill in the parameters:**
   - For `/ocr`: Upload an image file
   - For `/embed`: Enter text and metadata
   - For `/retrieve`: Enter a query
   - For `/generate`: Upload image or enter text

5. **Click "Execute"**

6. **See the response** with status code and data

## Example Workflow

### Step 1: Populate the Vector Database

First, add some exam questions to the database:

```bash
# Add multiple exam questions
curl -X POST "http://localhost:8000/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Question: Find the derivative of f(x) = x^2. Answer: 2x",
    "metadata": {"source": "calc_exam_1", "chunk_id": "q1"}
  }'

curl -X POST "http://localhost:8000/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Question: Solve for x: 2x + 5 = 15. Answer: x = 5",
    "metadata": {"source": "algebra_exam_1", "chunk_id": "q2"}
  }'
```

### Step 2: Upload an Image and Generate a Question

```bash
curl -X POST "http://localhost:8000/generate" \
  -F "image_file=@problem_screenshot.png" \
  -F "include_solution=false"
```

The system will:
1. Extract text from the image (OCR)
2. Find similar questions in the database
3. Generate a formatted exam question

## Troubleshooting

### "Invalid API key" Error

Make sure your `.env` file has a valid OpenAI API key:

```bash
# Check your .env file
cat .env | grep OPENAI_API_KEY
```

### "No similar content found"

You need to populate the vector database first using the `/embed` endpoint.

### "File too large"

Images must be under 10MB. Compress or resize your image.

### "Invalid file type"

Only PNG, JPG, and JPEG images are supported.

## Next Steps

1. ✅ **Explore the API docs** at http://localhost:8000/docs
2. ✅ **Test the endpoints** using the interactive docs
3. ✅ **Populate the vector database** with exam questions
4. ✅ **Try the full pipeline** with an image upload
5. 📚 **Read the full documentation** in `docs/ONBOARDING.md`

## Need Help?

- Check the logs in your terminal for detailed error messages
- Review the API documentation at `/docs`
- See `docs/CODE_EXPLANATION.md` for architecture details
- Check `docs/SECURITY_AUDIT.md` for security considerations

Happy coding! 🚀

