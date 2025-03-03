# Fyers OAuth Integration

A secure and user-friendly web application for authenticating with the Fyers trading API and managing access tokens.


## Features

- **Secure OAuth Flow**: Complete OAuth 2.0 implementation for Fyers API v3
- **Modern UI**: Responsive, card-based interface with proper styling
- **Token Management**: View, copy, and manage your authentication tokens
- **Security Features**: CSRF protection with secure state generation
- **Comprehensive Error Handling**: User-friendly error messages and logging
- **Copy-to-Clipboard**: One-click copying of tokens and authentication details
- **Persistent Storage**: Automatic saving of tokens with timestamps
- **Detailed Logging**: Comprehensive logging of all authentication processes

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- Python 3.8+
- Fyers Trading Account and API Credentials

### Step 1: Clone the repository

```bash
git clone https://github.com/yourusername/fyers-oauth.git
cd fyers-oauth
```

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

### Step 3: Activate the virtual environment

**On Windows:**
```bash
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### Step 1: Create a .env file

Create a `.env` file in the project root directory with the following variables or change it "smaple.env" to ".env":

```
APP_ID=your_fyers_app_id
SECRET_KEY=your_fyers_secret_key
REDIRECT_URI=http://127.0.0.1:5000/fyers/callback
```

The `APP_ID` should be in the format `XXXXXX-100` where XXXXXX is your Fyers App ID.

You can also use these alternative variable names if they match your existing configuration:
```
BROKER_API_KEY=your_fyers_app_id
BROKER_API_SECRET=your_fyers_secret_key
```

### Step 2: Configure the redirect URI in Fyers Developer Console

1. Log in to your Fyers Developer Console
2. Navigate to your application settings
3. Set the redirect URI to `http://127.0.0.1:5000/fyers/callback`
4. Save your changes

## Usage

### Starting the application

```bash
python fyers_oauth.py
```

The application will start at `http://127.0.0.1:5000`.

### Authentication Flow

1. Open your browser and navigate to `http://127.0.0.1:5000`
2. Click on the "Login with Fyers" button
3. You will be redirected to the Fyers login page
4. Enter your Fyers credentials and complete any verification steps
5. After successful authentication, you will be redirected back to the application
6. Your access token will be displayed and saved automatically

### Managing Tokens

1. Navigate to `http://127.0.0.1:5000/tokens` to view all saved tokens
2. Click on any token to view its details
3. Use the copy buttons to copy tokens for use in your trading applications

## Project Structure

```
fyers-oauth/
│
├── fyers_oauth.py        # Main application file
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this file)
├── fyers_oauth.log       # Application logs
│
├── data/                 # Data directory (created automatically)
│   └── tokens/           # Stored access tokens
│
├── static/               # Static files (created automatically)
│   ├── css/
│   │   └── styles.css    # CSS styles
│   └── js/
│       └── scripts.js    # JavaScript functions
│
└── README.md             # This documentation
```

## API Endpoints

### `/`
- **Method**: GET
- **Description**: Homepage with login button
- **Response**: HTML

### `/login`
- **Method**: GET
- **Description**: Redirects to Fyers login page
- **Response**: Redirect

### `/fyers/callback`
- **Method**: GET
- **Description**: Callback endpoint for Fyers OAuth
- **Query Parameters**:
  - `code` or `auth_code`: Authorization code from Fyers
  - `state`: State parameter for security validation
  - `error`: Error code (if authentication failed)
  - `error_description`: Error description (if authentication failed)
- **Response**: HTML with token information or error message

### `/tokens`
- **Method**: GET
- **Description**: Lists all saved tokens
- **Response**: HTML with token list

### `/token/{token_id}`
- **Method**: GET
- **Description**: Displays details for a specific token
- **Path Parameters**:
  - `token_id`: The ID of the token to view
- **Response**: HTML with token details

## Security Considerations

### State Parameter

The application uses a secure random state parameter to prevent CSRF attacks. Each authentication request generates a unique state value that is validated when Fyers redirects back to the application.

### Token Storage

Access tokens are stored in JSON files in the `data/tokens/` directory. Each file is named with a timestamp to prevent overwriting and for easy identification.

### Environment Variables

Sensitive information such as your Fyers App ID and Secret Key should be stored in the `.env` file, which should **not** be committed to version control.

## Troubleshooting

### Common Issues

#### "Missing required environment variables"

Ensure you have created a `.env` file with the required variables (APP_ID, SECRET_KEY, REDIRECT_URI).

#### "State mismatch" error

This error occurs if the state parameter from Fyers doesn't match the expected value. This could indicate a CSRF attack or a session timeout. Try logging in again.

#### "API error: Invalid AuthCode"

The authentication code provided by Fyers is invalid or has expired. This typically happens if you try to reuse a code or if there was a delay in processing. Try logging in again.

### Checking Logs

Check the `fyers_oauth.log` file for detailed error information. The application logs all requests, responses, and errors.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is not officially affiliated with Fyers. Use at your own risk. Always ensure you're following Fyers' terms of service when using their API.

---

For any issues or questions, please open an issue on GitHub or contact [info@lunargates.com].
