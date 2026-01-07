# AI Software Scanner

### The Problem:

* Team X reviews software for security issues
* They need to identify which approved software contains embedded AI (which may have compliance/security implications like unauthorized cloud data streaming)
* Currently it's a manual process with a spreadsheet of approved software
* AI is being added to software constantly, so this needs to run periodically (weekly)

### The Solution:
A simple Python tool that:

* Reads a spreadsheet/CSV of software names
* Uses AI to research each software and determine if it contains AI features
* Flags any software that has AI components for human review
* Outputs results (flagged vs. not flagged)

## Environment Variables

```sh
export AZURE_OPENAI_ENDPOINT="https://your-org.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
# OR
export OPENAI_API_KEY="your-key"
```
