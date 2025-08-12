# VidhiPath.ai

A Flask-based legal assistant for Indian law. Features document upload, AI-powered legal Q&A, user authentication, and more.


## Setup

1. Install Python 3.8+.
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the environment:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - Mac/Linux:
     ```
     source venv/bin/activate
     ```
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Add your Gemini API key to a `.env` file:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

## MySQL Database Setup

1. Install MySQL Server and create a database (e.g., `mera_vidhi`).
2. Create a user and grant privileges:
   ```sql
   CREATE USER 'youruser'@'localhost' IDENTIFIED BY 'yourpassword';
   GRANT ALL PRIVILEGES ON mera_vidhi.* TO 'youruser'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. Update your database connection settings in `database.py` or your `.env` file:
   ```
   DB_HOST=localhost
   DB_USER=youruser
   DB_PASSWORD=yourpassword
   DB_NAME=mera_vidhi
   ```

## Supabase Setup

1. Go to [supabase.com](https://supabase.com/) and create a project.
2. Get your Supabase URL and API key from the project settings.
3. Add them to your `.env` file:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_api_key
   ```
4. Run migrations if needed:
   - Place your migration SQL files in `supabase/migrations/`.
   - Use Supabase CLI or dashboard to apply migrations.

## Running the App

```
python app.py
```

## Features

- AI-powered legal Q&A (Gemini API)
- Document upload and processing
- User authentication (login, registration, password reset)
- Email OTP for password reset

## Configuration

Set your environment variables for email and Gemini API keys in `.env` or directly in your code.

## License

MIT
