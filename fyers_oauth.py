import os
import json
import logging
import hashlib
import secrets
import uuid
from typing import Optional
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("fyers_oauth.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fyers_oauth")

# Create directories for storing data
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
tokens_dir = data_dir / "tokens"
tokens_dir.mkdir(exist_ok=True)

# Retrieve Fyers app configuration from environment
APP_ID = os.getenv("APP_ID", os.getenv("BROKER_API_KEY"))
SECRET_KEY = os.getenv("SECRET_KEY", os.getenv("BROKER_API_SECRET"))
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Validate config
if not APP_ID or not SECRET_KEY or not REDIRECT_URI:
    logger.error(
        "Missing required environment variables: APP_ID/BROKER_API_KEY, SECRET_KEY/BROKER_API_SECRET, or REDIRECT_URI")
    raise Exception("Missing required environment variables")

# Session states storage - in production, use a proper database
states = {}

app = FastAPI(
    title="Fyers OAuth Integration",
    description="A secure interface for authenticating with Fyers API",
    version="1.0.0"
)

# Create a directory for static files
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
css_dir = static_dir / "css"
css_dir.mkdir(exist_ok=True)
js_dir = static_dir / "js"
js_dir.mkdir(exist_ok=True)

# Create CSS file if it doesn't exist
css_file = css_dir / "styles.css"
if not css_file.exists():
    with open(css_file, "w") as f:
        f.write("""
:root {
    --primary-color: #2563eb;
    --primary-dark: #1e40af;
    --secondary-color: #f59e0b;
    --text-color: #1f2937;
    --light-bg: #f3f4f6;
    --white: #ffffff;
    --error: #ef4444;
    --success: #10b981;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--light-bg);
    padding: 0;
    margin: 0;
}

.container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 20px;
}

header {
    background-color: var(--primary-color);
    color: var(--white);
    padding: 1rem 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

header .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo {
    font-size: 1.5rem;
    font-weight: bold;
}

main {
    padding: 2rem 0;
    min-height: calc(100vh - 150px);
}

.card {
    background: var(--white);
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    padding: 2rem;
    margin: 1rem 0;
}

.card-title {
    color: var(--primary-color);
    margin-bottom: 1rem;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.5rem;
}

.btn {
    display: inline-block;
    padding: 0.6rem 1.2rem;
    background: var(--primary-color);
    color: var(--white);
    border: none;
    border-radius: 4px;
    text-decoration: none;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.3s;
}

.btn:hover {
    background: var(--primary-dark);
}

.btn-secondary {
    background: var(--secondary-color);
}

.btn-secondary:hover {
    background: #d97706;
}

footer {
    text-align: center;
    padding: 1rem 0;
    background: var(--primary-color);
    color: var(--white);
}

.alert {
    padding: 1rem;
    border-radius: 4px;
    margin: 1rem 0;
}

.alert-error {
    background-color: #fecaca;
    border: 1px solid var(--error);
    color: #7f1d1d;
}

.alert-success {
    background-color: #d1fae5;
    border: 1px solid var(--success);
    color: #064e3b;
}

.loader {
    border: 4px solid #f3f3f3;
    border-top: 4px solid var(--primary-color);
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin: 1rem auto;
    display: none;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

pre {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    margin: 1rem 0;
}

.token-info {
    margin: 1rem 0;
}

.copy-btn {
    margin-top: 0.5rem;
}

.hidden {
    display: none;
}

@media (max-width: 768px) {
    .card {
        padding: 1rem;
    }
}
        """)

# Create JS file if it doesn't exist
js_file = js_dir / "scripts.js"
if not js_file.exists():
    with open(js_file, "w") as f:
        f.write("""
document.addEventListener('DOMContentLoaded', function() {
    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const textToCopy = document.getElementById(targetId).textContent;

            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = this.textContent;
                this.textContent = 'Copied!';
                this.classList.add('btn-secondary');

                setTimeout(() => {
                    this.textContent = originalText;
                    this.classList.remove('btn-secondary');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
                this.textContent = 'Failed to copy';
                setTimeout(() => {
                    this.textContent = originalText;
                }, 2000);
            });
        });
    });

    // Show/hide token details
    const toggleButtons = document.querySelectorAll('.toggle-btn');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);

            if (targetElement.classList.contains('hidden')) {
                targetElement.classList.remove('hidden');
                this.textContent = 'Hide Details';
            } else {
                targetElement.classList.add('hidden');
                this.textContent = 'Show Details';
            }
        });
    });
});
        """)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Function to generate a secure random state
def generate_state():
    """Generate a secure random state for OAuth flow."""
    state_id = str(uuid.uuid4())
    state_value = secrets.token_urlsafe(32)
    states[state_id] = {
        "value": state_value,
        "created_at": datetime.now()
    }
    return state_id, state_value


# Base HTML template
def get_base_html(title, content, error=None, success=None):
    """Generate HTML with the base template."""
    error_html = f"""
    <div class="alert alert-error">
        <p>{error}</p>
    </div>
    """ if error else ""

    success_html = f"""
    <div class="alert alert-success">
        <p>{success}</p>
    </div>
    """ if success else ""

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Fyers OAuth</title>
        <link rel="stylesheet" href="/static/css/styles.css">
    </head>
    <body>
        <header>
            <div class="container">
                <div class="logo">Fyers OAuth Integration</div>
            </div>
        </header>

        <main>
            <div class="container">
                {error_html}
                {success_html}
                {content}
            </div>
        </main>

        <footer>
            <div class="container">
                <p>&copy; {datetime.now().year} Fyers OAuth Integration</p>
            </div>
        </footer>

        <script src="/static/js/scripts.js"></script>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
async def index():
    """Homepage with a login button and application information."""
    content = """
    <div class="card">
        <h2 class="card-title">Welcome to Fyers OAuth Integration</h2>
        <p>This application helps you securely authenticate with the Fyers API and retrieve an access token.</p>

        <div style="margin: 2rem 0;">
            <a href="/login" class="btn">Login with Fyers</a>
        </div>

        <div>
            <h3>How it works:</h3>
            <ol style="margin-left: 1.5rem;">
                <li>Click the login button above</li>
                <li>You'll be redirected to Fyers' login page</li>
                <li>After successful authentication, you'll be redirected back here</li>
                <li>Your access token will be displayed and saved for future use</li>
            </ol>
        </div>
    </div>
    """
    return get_base_html("Home", content)


@app.get("/login")
async def login():
    """
    Redirect the user to Fyers' OAuth login page.
    Using v3 API as per the provided sample code
    """
    try:
        # Generate a secure state for this session
        state_id, state_value = generate_state()

        # Store state_id in a cookie or session (here we'll just use a query param for demo)

        # For v3 API, use the direct URL construction
        base_url = "https://api-t1.fyers.in/api/v3/generate-authcode"

        params = {
            "client_id": APP_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "state": f"{state_id}:{state_value}"
        }

        # Construct the authorization URL
        auth_url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

        logger.info("Generated Fyers auth URL for state_id: %s", state_id)
        return RedirectResponse(auth_url)
    except Exception as e:
        logger.exception("Error generating auth URL: %s", e)
        error_content = f"""
        <div class="card">
            <h2 class="card-title">Error</h2>
            <p>An error occurred while redirecting to Fyers login:</p>
            <pre>{str(e)}</pre>
            <a href="/" class="btn">Back to Home</a>
        </div>
        """
        return get_base_html("Error", error_content, error="Failed to generate login URL")


@app.get("/fyers/callback", response_class=HTMLResponse)
async def callback(
        code: str = Query(None),
        auth_code: str = Query(None),
        state: str = Query(None),
        error: str = Query(None),
        error_description: str = Query(None)
):
    """Handle the callback from Fyers after authentication."""
    # Check for errors from Fyers
    if error:
        logger.error("OAuth error: %s - %s", error, error_description)
        error_content = f"""
        <div class="card">
            <h2 class="card-title">Authentication Error</h2>
            <p>Fyers returned an error:</p>
            <pre>{error}: {error_description}</pre>
            <a href="/" class="btn">Try Again</a>
        </div>
        """
        return get_base_html("Authentication Error", error_content, error=f"Fyers error: {error}")

    # Validate state
    if not state:
        logger.error("Missing state parameter in callback")
        return get_base_html("Error",
                             "<div class='card'><h2 class='card-title'>Error</h2><p>Missing state parameter</p><a href='/' class='btn'>Try Again</a></div>",
                             error="Missing state parameter")

    try:
        state_id, state_value = state.split(":", 1)
        if state_id not in states or states[state_id]["value"] != state_value:
            logger.error("Invalid state: %s", state)
            return get_base_html("Error",
                                 "<div class='card'><h2 class='card-title'>Security Error</h2><p>Invalid state parameter. This could be a CSRF attempt.</p><a href='/' class='btn'>Try Again</a></div>",
                                 error="Security validation failed")

        # Clean up used state
        states.pop(state_id, None)
    except Exception as e:
        logger.error("Error validating state: %s", e)
        return get_base_html("Error",
                             "<div class='card'><h2 class='card-title'>Error</h2><p>Invalid state format</p><a href='/' class='btn'>Try Again</a></div>",
                             error="Invalid state format")

    # Use auth_code if provided; otherwise fallback to code.
    actual_code = auth_code if auth_code else code
    if not actual_code:
        logger.error("Missing authorization code in callback")
        return get_base_html("Error",
                             "<div class='card'><h2 class='card-title'>Error</h2><p>Missing authorization code</p><a href='/' class='btn'>Try Again</a></div>",
                             error="Missing authorization code")

    try:
        # Generate appIdHash as per the sample
        checksum_input = f"{APP_ID}:{SECRET_KEY}"
        app_id_hash = hashlib.sha256(checksum_input.encode('utf-8')).hexdigest()

        # The payload for token request
        payload = {
            'grant_type': 'authorization_code',
            'appIdHash': app_id_hash,
            'code': actual_code
        }

        # Token validation endpoint - using v3 as shown in the sample
        url = 'https://api-t1.fyers.in/api/v3/validate-authcode'

        # Headers as per Fyers documentation
        headers = {'Content-Type': 'application/json'}

        # Loading indicator HTML
        loading_html = """
        <div class="card">
            <h2 class="card-title">Processing</h2>
            <p>Retrieving your access token...</p>
            <div class="loader" style="display: block;"></div>
        </div>
        """

        # Make the request using httpx for async support
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

            logger.info(f"Token response status: {response.status_code}")

            # Parse the response
            response_data = response.json()

            # Check if response is successful
            if response.status_code == 200 and response_data.get('s') == 'ok':
                access_token = response_data.get('access_token')

                if not access_token:
                    raise ValueError("Authentication succeeded but no access token was returned")

                # Generate a unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                token_filename = f"token_{timestamp}.json"
                token_path = tokens_dir / token_filename

                # Save the complete token response
                with open(token_path, "w") as f:
                    json.dump(response_data, f, indent=4)
                logger.info("Access token saved to %s", token_path)

                # Return success page
                token_content = f"""
                <div class="card">
                    <h2 class="card-title">Authentication Successful</h2>
                    <p>Your access token has been retrieved and saved successfully!</p>

                    <div class="token-info">
                        <h3>Access Token</h3>
                        <pre id="access-token">{access_token}</pre>
                        <button class="btn copy-btn" data-target="access-token">Copy Token</button>
                    </div>

                    <div class="token-info">
                        <h3>Token Details</h3>
                        <button class="btn toggle-btn" data-target="token-details">Show Details</button>
                        <pre id="token-details" class="hidden">{json.dumps(response_data, indent=4)}</pre>
                        <button class="btn copy-btn hidden" data-target="token-details">Copy Details</button>
                    </div>

                    <div style="margin-top: 2rem;">
                        <p>Token has been saved to: <code>{token_path}</code></p>
                        <a href="/" class="btn">Back to Home</a>
                    </div>
                </div>
                """
                return get_base_html("Authentication Successful", token_content, success="Authentication successful!")
            else:
                # Handle API error
                error_message = response_data.get('message', 'Authentication failed. Please try again.')
                logger.error("API error: %s - %s", response.status_code, error_message)
                error_content = f"""
                <div class="card">
                    <h2 class="card-title">API Error</h2>
                    <p>Failed to retrieve access token:</p>
                    <pre>{error_message}</pre>
                    <div>
                        <h3>Response Details:</h3>
                        <pre>{json.dumps(response_data, indent=4)}</pre>
                    </div>
                    <a href="/" class="btn">Try Again</a>
                </div>
                """
                return get_base_html("API Error", error_content, error=f"API error: {error_message}")

    except Exception as e:
        logger.exception("Error generating access token: %s", e)
        error_content = f"""
        <div class="card">
            <h2 class="card-title">Error</h2>
            <p>An error occurred while processing your authentication:</p>
            <pre>{str(e)}</pre>
            <a href="/" class="btn">Try Again</a>
        </div>
        """
        return get_base_html("Error", error_content, error="Failed to generate access token")


@app.get("/tokens", response_class=HTMLResponse)
async def list_tokens():
    """List all saved tokens."""
    try:
        token_files = list(tokens_dir.glob("*.json"))

        if not token_files:
            token_list_content = """
            <div class="card">
                <h2 class="card-title">Saved Tokens</h2>
                <p>No tokens have been saved yet.</p>
                <a href="/" class="btn">Back to Home</a>
            </div>
            """
            return get_base_html("No Tokens", token_list_content)

        # Generate token list
        token_items = ""
        for token_file in sorted(token_files, reverse=True):
            try:
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                    access_token = token_data.get("access_token", "No token found")
                    created_time = token_file.stem.split("_")[1:]
                    created_time = "_".join(created_time) if created_time else "Unknown"

                token_items += f"""
                <div class="card" style="margin-bottom: 1rem;">
                    <h3>{token_file.name}</h3>
                    <p>Created: {created_time}</p>
                    <pre id="token-{token_file.stem}" style="max-width: 100%; overflow-x: auto;">{access_token[:20]}...</pre>
                    <button class="btn copy-btn" data-target="token-{token_file.stem}">Copy Token</button>
                    <a href="/token/{token_file.stem}" class="btn" style="margin-left: 0.5rem;">View Details</a>
                </div>
                """
            except Exception as e:
                logger.error(f"Error reading token file {token_file}: {e}")
                token_items += f"""
                <div class="card" style="margin-bottom: 1rem;">
                    <h3>{token_file.name}</h3>
                    <p>Error reading token: {str(e)}</p>
                </div>
                """

        token_list_content = f"""
        <div class="card">
            <h2 class="card-title">Saved Tokens</h2>
            <p>The following tokens have been saved:</p>

            <div style="margin: 1rem 0;">
                {token_items}
            </div>

            <a href="/" class="btn">Back to Home</a>
        </div>
        """
        return get_base_html("Saved Tokens", token_list_content)

    except Exception as e:
        logger.exception("Error listing tokens: %s", e)
        error_content = f"""
        <div class="card">
            <h2 class="card-title">Error</h2>
            <p>An error occurred while listing tokens:</p>
            <pre>{str(e)}</pre>
            <a href="/" class="btn">Back to Home</a>
        </div>
        """
        return get_base_html("Error", error_content, error="Failed to list tokens")


@app.get("/token/{token_id}", response_class=HTMLResponse)
async def view_token(token_id: str):
    """View details of a specific token."""
    try:
        token_path = tokens_dir / f"{token_id}.json"

        if not token_path.exists():
            error_content = f"""
            <div class="card">
                <h2 class="card-title">Token Not Found</h2>
                <p>The requested token does not exist.</p>
                <a href="/tokens" class="btn">View All Tokens</a>
            </div>
            """
            return get_base_html("Token Not Found", error_content, error="Token not found")

        with open(token_path, "r") as f:
            token_data = json.load(f)

        token_content = f"""
        <div class="card">
            <h2 class="card-title">Token Details: {token_id}</h2>

            <div class="token-info">
                <h3>Access Token</h3>
                <pre id="access-token-detail">{token_data.get('access_token', 'No token found')}</pre>
                <button class="btn copy-btn" data-target="access-token-detail">Copy Token</button>
            </div>

            <div class="token-info">
                <h3>Complete Token Data</h3>
                <pre id="token-data">{json.dumps(token_data, indent=4)}</pre>
                <button class="btn copy-btn" data-target="token-data">Copy Data</button>
            </div>

            <div style="margin-top: 1rem;">
                <a href="/tokens" class="btn">Back to Token List</a>
            </div>
        </div>
        """
        return get_base_html(f"Token: {token_id}", token_content)

    except Exception as e:
        logger.exception("Error viewing token: %s", e)
        error_content = f"""
        <div class="card">
            <h2 class="card-title">Error</h2>
            <p>An error occurred while viewing token details:</p>
            <pre>{str(e)}</pre>
            <a href="/tokens" class="btn">Back to Token List</a>
        </div>
        """
        return get_base_html("Error", error_content, error="Failed to view token details")


# Custom error handlers
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    error_content = """
    <div class="card">
        <h2 class="card-title">Page Not Found</h2>
        <p>The requested page does not exist.</p>
        <a href="/" class="btn">Back to Home</a>
    </div>
    """
    return HTMLResponse(
        content=get_base_html("Page Not Found", error_content, error="Page not found"),
        status_code=404
    )


@app.exception_handler(500)
async def server_error_exception_handler(request: Request, exc: HTTPException):
    error_content = """
    <div class="card">
        <h2 class="card-title">Server Error</h2>
        <p>An unexpected error occurred on the server.</p>
        <a href="/" class="btn">Back to Home</a>
    </div>
    """
    return HTMLResponse(
        content=get_base_html("Server Error", error_content, error="Server error"),
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Fyers OAuth Integration server")
    logger.info(f"APP_ID: {APP_ID[:5]}{'*' * (len(APP_ID) - 5) if len(APP_ID) > 5 else ''}")
    logger.info(f"REDIRECT_URI: {REDIRECT_URI}")

    # Make sure the module name matches the filename
    uvicorn.run("fyers_oauth:app", host="127.0.0.1", port=5000, reload=True)