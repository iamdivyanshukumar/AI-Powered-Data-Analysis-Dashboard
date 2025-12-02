# AI-Powered-Data-Analysis-Dashboard

**AI-Powered-Data-Analysis-Dashboard** is a Flask-based web application that helps users quickly explore datasets. By uploading a CSV file, the app automatically generates meaningful visualizations and provides AI-powered insights using OpenAI’s GPT models.  

The goal of **AI-Powered-Data-Analysis-Dashboard** is to simplify the process of data analysis for students, analysts, and professionals by combining automated visualization with natural language explanations.  

---

## Features

- **User Authentication**: Secure login and registration system  
- **CSV Upload & Processing**: Upload CSV files with validation and basic cleaning  
- **Automated Visualization**: Essential plots and AI-suggested visualizations  
- **AI-Powered Insights**: Descriptive insights generated using GPT models  
- **Session Management**: Track previous analysis sessions and history  
- **Responsive Design**: Clean and modern interface built with Bootstrap  

---

## Project Structure

```
ai-powered-data-analysis-dashboard/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py          # User model for authentication
│   │   └── routes.py          # Authentication routes (login, signup, logout)
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── models.py          # Analysis session and visualization models
│   │   └── routes.py          # Dashboard and analysis routes
│   ├── templates/
│   │   ├── auth/              # Login and registration templates
│   │   └── dashboard/         # Dashboard and analysis templates
│   │   └── base.html
│   ├── static/
│   │   ├── css/               # Custom stylesheets
│   │   └── js/                # JavaScript functionality
│   ├── uploads/               # Directory for uploaded CSV files
│   ├── utils/
│   │   ├── data_utils.py      # CSV validation and data processing
│   │   ├── viz_utils.py       # Visualization generation
│   │   └── genai_utils.py     # OpenAI integration for insights
│   ├── __init__.py            # Application factory
│   ├── config.py              # Configuration settings
│   └── extensions.py          # Flask extensions initialization
├── instance/                  # Database instance
├── requirements.txt           # Python dependencies
└── run.py                     # Application entry point
```

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/iamdivyanshukumar/AI-Powered-Data-Analysis-Dashboard.git
   cd ai-powered-data-analysis-dashboard
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv myenv
   source myenv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your actual values:
   ```
   SECRET_KEY=your-secret-key
   DATABASE_URL=sqlite:///ai-powered-data-analysis-dashboard.db
   OPENAI_API_KEY=your-openai-api-key
   ```

5. Initialize the database:
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

---

## Usage

1. Start the development server:
   ```bash
   python run.py
   ```

2. Open your browser and go to:  
   [http://localhost:5000](http://localhost:5000)

3. Register a new account or log in with existing credentials  

4. Upload a CSV file through the dashboard  

5. View the generated visualizations and request AI insights  

---


## Configuration

The application uses environment variables for configuration:

- `SECRET_KEY`: Flask secret key for session security  
- `DATABASE_URL`: Database connection string  
- `OPENAI_API_KEY`: OpenAI API key for AI insights  
- `UPLOAD_FOLDER`: Path for uploaded files (default: `app/uploads`)  

---

## Contributing

1. Fork the repository  
2. Create a feature branch (`git checkout -b feature/your-feature`)  
3. Commit your changes (`git commit -m "Add new feature"`)  
4. Push to the branch (`git push origin feature/your-feature`)  
5. Open a Pull Request  

---


## Acknowledgments

- OpenAI for GPT-powered insights    
- The Flask community for excellent documentation and support  
