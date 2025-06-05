# Google Vertex AI

To use Vertex AI, we need to:
1. Set up your Google Vertex AI credentials. 
2. Setup Environment Variables

### Web UI

1. [Create a service account](https://console.cloud.google.com/iam-admin/serviceaccounts/create) with `Vertex AI User` role
2. Download the credentials

Next, set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path of the JSON key file

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
export MODEL="vertex_ai/gemini-2.5-flash-preview-05-20"
```

### Command Line

From the command line, you can simply use `gcloud init` to set up your credentials.

```bash
gcloud init
```

And then set your model:

```bash
export MODEL="vertex_ai/gemini-2.5-flash-preview-05-20"
```
