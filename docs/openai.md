# OpenAI API Documentation

## Overview
OpenAI provides AI models for natural language processing, image generation, and computer vision.

## Models Used in This Project

### 1. GPT-4o-mini (Chat Completions)
Fast and affordable multimodal model for text and vision tasks.

### 2. DALL-E 3 (Image Generation)
State-of-the-art text-to-image generation model.

## API Setup

```python
from openai import OpenAI
import os

# Initialize client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

## Chat Completions API (GPT-4o-mini)

### Basic Usage
```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=1000
)

result = response.choices[0].message.content
```

### Parameters

#### model
- `"gpt-4o-mini"` - Fast, affordable multimodal model
- `"gpt-4o"` - More capable but slower
- `"gpt-4-turbo"` - Previous generation

#### messages
Array of message objects with `role` and `content`:
- `role`: "system", "user", or "assistant"
- `content`: String or array (for vision)

#### temperature
- Range: 0.0 to 2.0
- Lower = more deterministic (0.0-0.3)
- Higher = more creative (0.7-1.5)
- Default: 1.0

#### max_tokens
Maximum number of tokens to generate (1 token ≈ 4 characters)

### Vision API (Image Analysis)

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    max_tokens=500
)
```

### System Prompts

Best practices:
- Clear instructions
- Specific output format
- Context and constraints
- Examples (few-shot learning)

```python
system_prompt = """You are an expert in window treatments.
Analyze product images and identify:
1. Product type (blinds, shutters, curtains)
2. Material and color
3. Installation location
4. Style and features

Always respond in Lithuanian."""
```

## Image Generation API (DALL-E 3)

### Basic Usage
```python
response = client.images.generate(
    model="dall-e-3",
    prompt="A beautiful spring landscape with flowers",
    size="1024x1024",
    quality="standard",
    n=1
)

image_url = response.data[0].url
```

### Parameters

#### model
- `"dall-e-3"` - Latest, highest quality
- `"dall-e-2"` - Previous generation

#### prompt
Text description of desired image (max 4000 characters)

Best practices:
- Be specific and descriptive
- Include style, mood, lighting
- Mention objects, colors, composition
- Avoid vague terms

#### size
- DALL-E 3: "1024x1024", "1024x1792", "1792x1024"
- DALL-E 2: "256x256", "512x512", "1024x1024"

#### quality
- `"standard"` - Faster, cheaper
- `"hd"` - Higher detail (DALL-E 3 only)

#### n
Number of images (1-10 for DALL-E 2, only 1 for DALL-E 3)

### Prompt Engineering for DALL-E

Good prompt structure:
```
[Subject] + [Style] + [Composition] + [Lighting] + [Mood] + [Details]
```

Example:
```python
prompt = """Professional product photography of modern window blinds
in a bright living room, minimalist Scandinavian style,
natural daylight, warm cozy atmosphere, high resolution,
depth of field, blurred background"""
```

## Error Handling

```python
try:
    response = client.chat.completions.create(...)
except openai.RateLimitError:
    print("Rate limit exceeded")
except openai.APIConnectionError:
    print("Connection error")
except openai.AuthenticationError:
    print("Invalid API key")
except Exception as e:
    print(f"Error: {e}")
```

## Cost Optimization

### GPT-4o-mini
- Input: $0.150 / 1M tokens
- Output: $0.600 / 1M tokens
- ~4 characters = 1 token

Tips:
- Use clear, concise prompts
- Set appropriate max_tokens
- Use temperature 0.5-0.7 for focused tasks
- Cache system prompts when possible

### DALL-E 3
- Standard 1024x1024: $0.040/image
- Standard 1024x1792: $0.080/image
- HD quality: 2x price

Tips:
- Use "standard" quality unless needed
- Generate one image at a time
- Refine prompts before generating

## Best Practices

1. **API Key Security**
   - Use environment variables
   - Never commit keys to git
   - Use Streamlit secrets for deployment

2. **Rate Limiting**
   - Implement retry logic
   - Add delays between requests
   - Monitor usage

3. **Prompt Design**
   - Test and iterate
   - Use specific instructions
   - Include examples
   - Set appropriate temperature

4. **Cost Management**
   - Monitor token usage
   - Set max_tokens limits
   - Use cheaper models when possible
   - Cache responses

## Documentation Links
- https://platform.openai.com/docs
- https://platform.openai.com/docs/guides/vision
- https://platform.openai.com/docs/guides/images
