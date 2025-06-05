# Google Gemini

We will:
1. Create a Gemini API Key
2. Setup Environment Variables

### Web UI

1. Go to [Gemini API Key](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Select your GCP Project from the dropdown
4. Press "Create your API Key..."

This key will be the `GEMINI_API_KEY` you use in your environment variables.

### Command Line

Use the gcloud cli.  `gcloud alpha services api-keys create --display-name 'my-fast-mcp-gemini-key' --api-target=service=generativelanguage.googleapis.com`

The value in the keyString field will be the `GEMINI_API_KEY` you use in your environment variables.

### Setup Environment Variables

```bash
export GEMINI_API_KEY=your-gemini-api-key
export MODEL="gemini/gemini-2.5-flash-preview-05-20"
```